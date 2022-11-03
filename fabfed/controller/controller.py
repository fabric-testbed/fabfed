import logging
from typing import List

from fabfed.model.state import ProviderState
from fabfed.util.config import Config
from .helper import ControllerResourceListener
from .provider_factory import ProviderFactory
from ..util.constants import Constants


class Controller:
    def __init__(self, *, config: Config, logger: logging.Logger):
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

        resources = self.config.get_resource_config()

        for resource in resources:
            resource_dict = resource.attributes
            resource_dict[Constants.RES_TYPE] = resource.type
            resource_dict[Constants.RES_NAME_PREFIX] = resource.name
            resource_dict[Constants.LABEL] = resource.label
            resource_dict['has_dependencies'] = resource.has_dependencies()  # TODO: Fix Controller test and remove this
            external_dependencies = resource_dict[Constants.EXTERNAL_DEPENDENCIES] = list()
            resource_dict[Constants.RESOLVED_EXTERNAL_DEPENDENCIES] = list()

            for dependency in resource.dependencies:
                if dependency.is_external:
                    external_dependencies.append(dependency)

            if resource.is_network:
                resource.attributes[Constants.RES_NET_STITCH_PROVS] = list()

        for network in [resource for resource in resources if resource.is_network]:
            for dependency in network.dependencies:
                if dependency.resource.is_network:
                    stitch_provider = network.provider.type

                    if stitch_provider not in dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS]:
                        dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS].append(stitch_provider)

    def plan(self):
        resources = self.config.get_resource_config()
        self.logger.info(f"Starting PLAN_PHASE: Calling ADD ... for {len(resources)} resource(s)")

        exceptions = []
        for resource in resources:
            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.add_resource(resource=resource.attributes)
            except Exception as e:
                self.logger.warning(
                    f"Exception occurred while adding resource: {e} using {label}/{resource.name}")
                exceptions.append(e)
                self.logger.warning(e, exc_info=True)

        if exceptions:
            raise exceptions[0]

    def create(self):
        resources = self.config.get_resource_config()
        exceptions = []

        self.logger.info(f"Starting CREATE_PHASE: Calling CREATE ... for {len(resources)} resource(s)")

        for resource in resources:
            label = resource.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.create_resource(resource=resource.attributes)
            except Exception as e:
                self.logger.warning(
                    f"Exception occurred while creating resource: {e} using {label}/{resource.provider.name}")
                exceptions.append(e)
                self.logger.warning(e, exc_info=True)

        if exceptions:
            raise exceptions[0]

    def delete(self, *, provider_states: List[ProviderState]):
        exceptions = []
        resource_state_map = dict()
        provider_resource_map = dict()

        for provider_state in provider_states:
            for network_state in provider_state.network_states:
                resource_state_map[network_state.label] = network_state

            for node_state in provider_state.node_states:
                resource_state_map[node_state.label] = node_state

            for service_state in provider_state.service_states:
                resource_state_map[service_state.label] = service_state

            key = provider_state.label
            provider_resource_map[key] = list()

        temp = self.config.get_resource_config()
        temp.reverse()

        for resource in temp:
            if resource.label in resource_state_map:
                key = resource.provider.label
                provider_resource_map[key].append(resource)

        remaining_resources = list()

        for key, slice_resources in provider_resource_map.items():
            provider_label = key
            provider = self.provider_factory.get_provider(label=provider_label)

            for resource in slice_resources:
                try:
                    provider.delete_resource(resource=resource.attributes)
                except Exception as e:
                    self.logger.warning(f"Exception occurred while deleting resource: {e} using {provider_label}")
                    remaining_resources.append(resource)
                    exceptions.append(e)

        provider_states_copy = provider_states.copy()
        provider_states.clear()

        for provider_state in provider_states_copy:
            provider_state.node_states.clear()
            provider_state.network_states.clear()
            provider = self.provider_factory.get_provider(label=provider_state.label)
            provider_state.failed = provider.failed

            for remaining_resource in remaining_resources:
                resource_state = resource_state_map[remaining_resource.label]

                if remaining_resource.provider.label == provider_state.label:
                    if remaining_resource.is_network:
                        provider_state.network_states.append(resource_state)
                    elif remaining_resource.is_node:
                        provider_state.node_states.append(resource_state)
                    elif remaining_resource.is_service:
                        provider_state.service_states.append(resource_state)

            if provider_state.node_states or provider_state.network_states or provider_state.service_states:
                provider_states.append(provider_state)

        if exceptions:
            raise exceptions[0]

    def get_states(self) -> List[ProviderState]:
        provider_states = []

        for provider in self.provider_factory.providers:
            provider_state = provider.get_state()

            # TODO if provider_state.network_states or provider_state.node_states:
            provider_states.append(provider_state)

        return provider_states
