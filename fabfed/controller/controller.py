import logging
from typing import List, Union, Dict

from fabfed.exceptions import ControllerException
from fabfed.model.state import ProviderState
from fabfed.util.config import WorkflowConfig
from .helper import ControllerResourceListener, partition_layer3_config
from fabfed.policy.policy_helper import ProviderPolicy
from .provider_factory import ProviderFactory
from ..util.constants import Constants
from ..util.config_models import ResourceConfig


class Controller:
    def __init__(self, *, config: WorkflowConfig, logger: logging.Logger,
                 policy: Union[Dict[str, ProviderPolicy], None] = None,
                 use_local_policy=True):
        self.config = config
        self.logger = logger
        self.provider_factory = None
        self.resources: List[ResourceConfig] = []
        self.policy = policy
        self.use_local_policy = use_local_policy

    def init(self, *, session: str, provider_factory: ProviderFactory):
        for provider_config in self.config.get_provider_config():
            name = provider_config.attributes.get('name')
            name = f"{session}-{name}" if name else session
            provider_factory.init_provider(type=provider_config.type,
                                           label=provider_config.label,
                                           name=name,
                                           attributes=provider_config.attributes,
                                           logger=self.logger)

        if not self.policy:
            if self.use_local_policy:
                from fabfed.policy.policy_helper import load_policy

                self.policy = load_policy()
                self.logger.info(f"loaded local stitching policy.")
            else:
                from fabfed.policy.policy_helper import load_remote_policy

                self.policy = load_remote_policy()
                self.logger.info(f"loaded remote stitching policy.")

        self.provider_factory = provider_factory
        providers = self.provider_factory.providers
        resource_listener = ControllerResourceListener(providers)

        for provider in providers:
            provider.set_resource_listener(resource_listener)

        self.resources = self.config.get_resource_configs()

        from fabfed.policy.policy_helper import handle_stitch_info, fix_node_site, fix_network_site

        self.resources = handle_stitch_info(self.config, self.policy, self.resources)

        for resource in self.resources:
            if resource.is_node:
                fix_node_site(resource, self.resources)
            elif resource.is_network:
                fix_network_site(resource)

        for resource in self.resources:
            resource_dict = resource.attributes
            resource_dict[Constants.RES_TYPE] = resource.type
            resource_dict[Constants.RES_NAME_PREFIX] = resource.name
            resource_dict[Constants.LABEL] = resource.label
            resource_dict[Constants.EXTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.RESOLVED_EXTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.INTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.RESOLVED_INTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.SAVED_STATES] = list()

            for dependency in resource.dependencies:
                if dependency.is_external:
                    resource_dict[Constants.EXTERNAL_DEPENDENCIES].append(dependency)
                else:
                    resource_dict[Constants.INTERNAL_DEPENDENCIES].append(dependency)

        layer3_to_network_mapping = {}
        networks = [resource for resource in self.resources if resource.is_network]

        for network in networks:
            layer3 = network.attributes.get(Constants.RES_LAYER3)

            if layer3:
                if layer3.label in layer3_to_network_mapping:
                    layer3_to_network_mapping.get(layer3.label).append(network)
                else:
                    layer3_to_network_mapping[layer3.label] = [network]

        for networks_with_same_layer3 in layer3_to_network_mapping.values():
            partition_layer3_config(networks=networks_with_same_layer3)

        peering_to_network_mapping = {}

        for network in networks:
            network.attributes[Constants.RES_PEER_LAYER3] = []
            peering = network.attributes.get(Constants.RES_PEERING)

            if peering:
                if peering.label in peering_to_network_mapping:
                    peering_to_network_mapping.get(peering.label).append(network)
                else:
                    peering_to_network_mapping[peering.label] = [network]

        for peers in peering_to_network_mapping.values():
            for network in peers:
                for other in [peer for peer in peers if peer.label != network.label]:
                    if Constants.RES_LAYER3 in other.attributes:
                        network.attributes[Constants.RES_PEER_LAYER3].append(other.attributes[Constants.RES_LAYER3])

        for network in networks:
            self.logger.info(f"{network}: stitch_info={network.attributes.get(Constants.RES_STITCH_INFO)}")
            self.logger.info(f"{network}: stitch_with={network.attributes.get(Constants.RES_STITCH_INTERFACE)}")

    def plan(self, provider_states: List[ProviderState]):
        resources = self.resources
        resource_state_map = Controller._build_state_map(provider_states)
        self.logger.info(f"Starting PLAN_PHASE: Calling ADD ... for {len(resources)} resource(s)")

        exceptions = []
        for resource in resources:
            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            if resource.label in resource_state_map:
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

            try:
                provider.add_resource(resource=resource.attributes)
            except Exception as e:
                exceptions.append(e)
                self.logger.error(e, exc_info=True)

        if exceptions:
            raise ControllerException(exceptions)

    def create(self, provider_states: List[ProviderState]):
        self.logger.info(f"Starting CREATE_PHASE: Calling CREATE ... for {len(self.resources)} resource(s)")
        resource_state_map = Controller._build_state_map(provider_states)
        exceptions = []

        for resource in filter(lambda r: not r.is_service, self.resources):
            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            if resource.label in resource_state_map:
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

            try:
                provider.create_resource(resource=resource.attributes)
            except Exception as e:
                exceptions.append(e)
                self.logger.error(e, exc_info=True)

        if exceptions:
            raise ControllerException(exceptions)

        from .helper import find_node_clusters
        from fabfed.util.node_tester import SshNodeTester

        clusters = find_node_clusters(resources=self.resources)
        nodes = [n for provider in self.provider_factory.providers for n in provider.nodes]

        for cluster in clusters:
            tester = SshNodeTester(nodes=[n for n in nodes if n.label in [n.label for n in cluster]],
                                   run_ping_test=len(cluster)>1)
            tester.run_tests()

            from fabfed.model.state import get_dumper
            import sys
            import yaml

            rep = yaml.dump(tester.summary, default_flow_style=False, sort_keys=False, Dumper=get_dumper())
            sys.stderr.write(rep)

            if tester.has_failures():
                raise ControllerException([Exception("Node testing over ssh failed see node test summary ...")])

            self.logger.info(f"Node testing over ssh pass for {[n.name for n in nodes]}")

        exceptions = []

        for resource in filter(lambda r: r.is_service, self.resources):
            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            if resource.label in resource_state_map:
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

            try:
                provider.create_resource(resource=resource.attributes)
            except Exception as e:
                exceptions.append(e)
                self.logger.error(e, exc_info=True)

        if exceptions:
            raise ControllerException(exceptions)

    @staticmethod
    def _build_state_map(provider_states):
        resource_state_map = dict()
        for provider_state in provider_states:
            temp_list = provider_state.states()

            for state in temp_list:
                if state.label in resource_state_map:
                    resource_state_map[state.label].append(state)
                else:
                    resource_state_map[state.label] = [state]

        return resource_state_map

    def delete(self, *, provider_states: List[ProviderState]):
        exceptions = []
        resource_state_map = Controller._build_state_map(provider_states)
        provider_resource_map = dict()

        for provider_state in provider_states:
            key = provider_state.label
            provider_resource_map[key] = list()

        temp = self.resources
        temp.reverse()

        for resource in temp:
            if resource.label in resource_state_map:
                key = resource.provider.label
                external_dependencies = resource.attributes.get(Constants.EXTERNAL_DEPENDENCIES, [])
                external_states = [resource_state_map[ed.resource.label] for ed in external_dependencies]
                resource.attributes[Constants.EXTERNAL_DEPENDENCY_STATES] = sum(external_states, [])
                provider_resource_map[key].append(resource)
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

        remaining_resources = list()
        skip_resources = set()

        for resource in temp:
            if resource.label not in resource_state_map:
                continue

            provider_label = resource.provider.label
            provider = self.provider_factory.get_provider(label=provider_label)
            external_states = resource.attributes[Constants.EXTERNAL_DEPENDENCY_STATES]

            if resource.label in skip_resources:
                self.logger.warning(f"Skipping deleting resource: {resource} with {provider_label}")
                remaining_resources.append(resource)
                skip_resources.update([external_state.label for external_state in external_states])
                continue

            fabric_work_around = False
            # TODO: THIS FABRIC SPECIFIC AS WE DON"T SUPPORT SLICE MODIFY API JUST YET
            for remaining_resource in remaining_resources:
                if provider_label == remaining_resource.provider.label \
                        and "@fabric" in remaining_resource.provider.label:
                    fabric_work_around = True
                    break

            if fabric_work_around:
                self.logger.warning(f"Skipping deleting fabric resource: {resource} with {provider_label}")
                remaining_resources.append(resource)
                skip_resources.update([external_state.label for external_state in external_states])
                continue

            try:
                provider.delete_resource(resource=resource.attributes)
            except Exception as e:
                self.logger.warning(f"Exception occurred while deleting resource: {e} using {provider_label}")
                remaining_resources.append(resource)
                skip_resources.update([external_state.label for external_state in external_states])
                exceptions.append(e)

        provider_states_copy = provider_states.copy()
        provider_states.clear()

        for provider_state in provider_states_copy:
            provider_state.node_states.clear()
            provider_state.network_states.clear()
            provider_state.service_states.clear()
            provider = self.provider_factory.get_provider(label=provider_state.label)
            provider_state.failed = provider.failed

            for remaining_resource in remaining_resources:
                resource_state = resource_state_map[remaining_resource.label]

                if remaining_resource.provider.label == provider_state.label:
                    if remaining_resource.is_network:
                        provider_state.network_states.extend(resource_state)
                    elif remaining_resource.is_node:
                        provider_state.node_states.extend(resource_state)
                    elif remaining_resource.is_service:
                        provider_state.service_states.extend(resource_state)

            if provider_state.node_states or provider_state.network_states or provider_state.service_states:
                provider_states.append(provider_state)

        if exceptions:
            raise ControllerException(exceptions)

    def get_states(self) -> List[ProviderState]:
        provider_states = []

        for provider in self.provider_factory.providers:
            provider_state = provider.get_state()

            # TODO if provider_state.network_states or provider_state.node_states:
            provider_states.append(provider_state)

        return provider_states
