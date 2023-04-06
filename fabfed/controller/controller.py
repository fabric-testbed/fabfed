import logging
from typing import List

from fabfed.exceptions import ControllerException
from fabfed.model.state import ProviderState
from fabfed.util.config import WorkflowConfig
from .helper import ControllerResourceListener, partition_layer3_config
from .provider_factory import ProviderFactory
from ..util.constants import Constants


class Controller:
    def __init__(self, *, config: WorkflowConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.provider_factory = None

    def init(self, *, session: str, provider_factory: ProviderFactory):
        for provider_config in self.config.get_provider_config():
            name = provider_config.attributes.get('name')
            name = f"{session}-{name}" if name else session
            provider_factory.init_provider(type=provider_config.type,
                                           label=provider_config.label,
                                           name=name,
                                           attributes=provider_config.attributes,
                                           logger=self.logger)

        self.provider_factory = provider_factory
        providers = self.provider_factory.providers
        resource_listener = ControllerResourceListener(providers)

        for provider in providers:
            provider.set_resource_listener(resource_listener)

        resources = self.config.get_resource_configs()

        for resource in resources:
            resource_dict = resource.attributes
            resource_dict[Constants.RES_TYPE] = resource.type
            resource_dict[Constants.RES_NAME_PREFIX] = resource.name
            resource_dict[Constants.LABEL] = resource.label
            resource_dict[Constants.EXTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.RESOLVED_EXTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.INTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.RESOLVED_INTERNAL_DEPENDENCIES] = list()

            for dependency in resource.dependencies:
                if dependency.is_external:
                    resource_dict[Constants.EXTERNAL_DEPENDENCIES].append(dependency)
                else:
                    resource_dict[Constants.INTERNAL_DEPENDENCIES].append(dependency)

            if resource.is_network and not resource.attributes.get(Constants.RES_NET_STITCH_PROVS):
                resource.attributes[Constants.RES_NET_STITCH_PROVS] = list()

        for network in [resource for resource in resources if resource.is_network]:
            for dependency in network.dependencies:
                if dependency.resource.is_network:
                    stitch_provider = network.provider.type

                    if stitch_provider not in dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS]:
                        if stitch_provider not in dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS]:
                            dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS].append(stitch_provider)

        layer3_to_network_mapping = {}
        networks = [resource for resource in resources if resource.is_network]

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
                    network.attributes[Constants.RES_PEER_LAYER3].append(other.attributes[Constants.RES_LAYER3])

    def _build_state_map(self, provider_states):
        resource_state_map = dict()
        for provider_state in provider_states:
            temp_list = provider_state.network_states + provider_state.node_states + provider_state.service_states

            for state in temp_list:
                if state.label in resource_state_map:
                    resource_state_map[state.label].append(state)
                else:
                    resource_state_map[state.label] = [state]
        return resource_state_map

    def plan(self, *, provider_states: List[ProviderState]):
        resources = self.config.get_resource_configs()
        resource_state_map = self._build_state_map(provider_states)

        self.logger.info(f"Starting PLAN_PHASE: Calling ADD ... for {len(resources)} resource(s)")

        exceptions = []
        for resource in resources:
            resource.attributes[Constants.SAVED_STATES] = list()
            if resource.label in resource_state_map:
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.add_resource(resource=resource.attributes)
            except Exception as e:
                exceptions.append(e)
                self.logger.error(e, exc_info=True)

        if exceptions:
            raise ControllerException(exceptions)

    def create(self, *, provider_states: List[ProviderState]):
        resources = self.config.get_resource_configs()
        resource_state_map = self._build_state_map(provider_states)
        exceptions = []

        self.logger.info(f"Starting CREATE_PHASE: Calling CREATE ... for {len(resources)} resource(s)")

        for resource in resources:
            resource.attributes[Constants.SAVED_STATES] = list()
            if resource.label in resource_state_map:
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.create_resource(resource=resource.attributes)
            except Exception as e:
                exceptions.append(e)
                self.logger.error(e, exc_info=True)

        if exceptions:
            raise ControllerException(exceptions)

    def delete(self, *, provider_states: List[ProviderState]):
        exceptions = []
        remaining_resources = list()
        skip_resources = set()

        resource_state_map = self._build_state_map(provider_states)
        resources = self.config.get_resource_configs()
        resources.reverse()

        for resource in resources:
            resource.attributes[Constants.SAVED_STATES] = list()
            if resource.label in resource_state_map:
                key = resource.provider.label
                external_dependencies = resource.attributes.get(Constants.EXTERNAL_DEPENDENCIES, [])
                external_states = [resource_state_map[ed.resource.label] for ed in external_dependencies]
                resource.attributes[Constants.EXTERNAL_DEPENDENCY_STATES] = sum(external_states, [])
                resource.attributes[Constants.SAVED_STATES] = resource_state_map[resource.label]

        for resource in resources:
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
