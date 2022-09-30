import logging
from typing import List

from fabfed.model import Slice
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

    def init(self, provider_factory: ProviderFactory):
        for provider_config in self.config.get_provider_config():
            provider_factory.init_provider(type=provider_config.type,
                                           label=provider_config.label,
                                           attributes=provider_config.attributes,
                                           logger=self.logger)

        for slice_config in self.config.get_slice_config():
            client = provider_factory.get_provider(label=slice_config.provider.label)
            slice_config.attributes[Constants.LABEL] = slice_config.label
            client.init_slice(slice_name=slice_config.name, slice_config=slice_config.attributes)

        self.provider_factory = provider_factory

    def plan(self):
        resources = self.config.get_resource_config()
        providers = self.provider_factory.providers
        resource_listener = ControllerResourceListener(providers)

        for provider in providers:
            provider.set_resource_listener(resource_listener)

        for resource in resources:
            resource_dict = resource.attributes
            resource_dict[Constants.RES_TYPE] = resource.type
            resource_dict[Constants.RES_NAME_PREFIX] = resource.name
            resource_dict[Constants.LABEL] = resource.label
            resource_dict['has_dependencies'] = resource.has_dependencies()
            resource_dict['dependencies'] = resource.dependencies
            resource_dict['resolved_dependencies'] = list()

        networks = [resource for resource in resources if resource.is_network]

        for network in networks:
            network.attributes[Constants.RES_NET_STITCH_PROVS] = list()

        for network in networks:
            if network.has_dependencies():
                for dependency in network.dependencies:
                    if dependency.resource.is_network:
                        stitch_provider = network.slice.provider.type

                        if stitch_provider not in dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS]:
                            self.logger.info(
                                f"Stitching network {dependency.resource.label} to {network.slice.provider.type}")
                            dependency.resource.attributes[Constants.RES_NET_STITCH_PROVS].append(stitch_provider)

        self.logger.info(f"Starting PLAN_PHASE: Calling ADD ... for {len(resources)} resource(s)")

        exceptions = []
        for resource in resources:
            label = resource.slice.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.add_resource(resource=resource.attributes, slice_name=resource.slice.name)
            except Exception as e:
                self.logger.warning(
                    f"Exception occurred while adding resource: {e} using {label}/{resource.slice.name}")
                exceptions.append(e)

        if exceptions:
            raise exceptions[0]

    def create(self):
        resources = self.config.get_resource_config()
        exceptions = []

        self.logger.info(f"Starting CREATE_PHASE: Calling CREATE ... for {len(resources)} resource(s)")

        for resource in resources:
            label = resource.slice.provider.label
            provider = self.provider_factory.get_provider(label=label)

            try:
                provider.create_resources(slice_name=resource.slice.name)
            except Exception as e:
                self.logger.warning(
                    f"Exception occurred while creating resource: {e} using {label}/{resource.slice.name}")
                exceptions.append(e)

        if exceptions:
            raise exceptions[0]

    def delete(self, *, provider_states: List[ProviderState]):
        exceptions = []
        resource_state_map = dict()
        slice_state_map = dict()

        for provider_state in provider_states:
            for slice_state in provider_state.slice_states:
                for network_state in slice_state.network_states:
                    resource_state_map[network_state.label] = network_state

                for node_state in slice_state.node_states:
                    resource_state_map[node_state.label] = node_state

                key = slice_state.attributes['name'] + ':' + provider_state.label
                slice_state_map[key] = list()

        temp = self.config.get_resource_config()
        temp.reverse()

        for resource in temp:
            if resource.label in resource_state_map:
                key = resource.slice.name + ":" + resource.slice.provider.label
                slice_state_map[key].append(resource)

        remaining_resources = list()

        for key, slice_resources in slice_state_map.items():
            idx = key.index(':')
            slice_name = key[0:idx]
            provider_label = key[idx+1:]
            provider = self.provider_factory.get_provider(label=provider_label)

            for resource in slice_resources:
                try:
                    resource_dict = resource.attributes
                    resource_dict[Constants.RES_TYPE] = resource.type
                    resource_dict[Constants.RES_NAME_PREFIX] = resource.name
                    resource_dict[Constants.LABEL] = resource.label
                    provider.delete_resource(resource=resource_dict, slice_name=slice_name)
                except Exception as e:
                    self.logger.warning(f"Exception occurred while deleting resource: {e} using {provider_label}")
                    remaining_resources.append(resource)
                    exceptions.append(e)

        provider_states_copy = provider_states.copy()
        provider_states.clear()

        for provider_state in provider_states_copy:
            slice_states_copy = provider_state.slice_states.copy()
            provider_state.slice_states.clear()

            for slice_state in slice_states_copy:
                slice_state.node_states.clear()
                slice_state.network_states.clear()

                for remaining_resource in remaining_resources:
                    resource_state = resource_state_map[remaining_resource.label]
                    slice_object = remaining_resource.slice

                    if slice_object.label == slice_state.label and slice_object.provider.label == provider_state.label:
                        if remaining_resource.is_network:
                            slice_state.node_states.append(resource_state)
                        else:
                            slice_state.network_states.append(resource_state)

                if slice_state.node_states or slice_state.network_states:
                    provider_state.slice_states.append(slice_state)

            if provider_state.slice_states:
                provider_states.append(provider_state)

        if exceptions:
            raise exceptions[0]

    def get_slices(self) -> List[Slice]:
        resources = []

        for provider in self.provider_factory.providers:
            slices = provider.get_slices()

            if slices:
                resources.extend(slices)

        return resources

    def get_states(self) -> List[ProviderState]:
        provider_states = []

        for provider in self.provider_factory.providers:
            provider_state = provider.get_state()

            if provider_state.slice_states:
                provider_states.append(provider_state)

        return provider_states
