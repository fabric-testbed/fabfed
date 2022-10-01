import logging
from abc import ABC, abstractmethod
from fabfed.model import Slice
from typing import List
from fabfed.model.state import ProviderState


class Provider(ABC):
    def __init__(self, *, type, name, logger: logging.Logger, config: dict):
        self.type = type
        self.name = name
        self.logger = logger
        self.config = config
        self.slices = {}
        self.resource_listener = None

    def set_resource_listener(self, resource_listener):
        """
        Set the resource listener
        """
        self.resource_listener = resource_listener

    @abstractmethod
    def init_slice(self, *, slice_config: dict, slice_name: str):
        pass

    def get_slices(self) -> List[Slice]:
        """
        Returns list of the allocated slices
        """
        return list(self.slices.values())

    def on_added(self, source, slice_name, resource: dict):
        if self.resource_listener and source != self.resource_listener:
            self.resource_listener.on_added(self, slice_name, resource)

        for slice_object in self.slices.values():
            if source != slice_object:
                slice_object.on_added(source, slice_name, resource)

    def on_created(self, source, slice_name, resource: dict):
        if self.resource_listener and source != self.resource_listener:
            self.resource_listener.on_created(self, slice_name, resource)

        for slice_object in self.slices.values():
            if source != slice_object:
                slice_object.on_created(source, slice_name, resource)

    def on_deleted(self, source, slice_name, resource):
        if self.resource_listener and source != self.resource_listener:
            self.resource_listener.on_deleted(self, slice_name, resource)

        for slice_object in self.slices.values():
            if source != slice_object:
                slice_object.on_deleted(source, slice_name, resource)

    def add_resource(self, *, resource: dict, slice_name: str):
        self.logger.debug(f"Provider {self.name} calling slice.add {slice_name}")
        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")

        from fabfed.util.constants import Constants
        count = resource.get(Constants.RES_COUNT, 1)

        if count < 1:
            self.logger.debug(f"Skipping {resource} to {slice_name} {count}")
            return

        slice_object = self.slices[slice_name]

        try:
            slice_object.add_resource(resource=resource)
        except Exception as e:
            # slice_object.pending.append(resource)
            raise e

    def create_resource(self, *, resource: dict, slice_name: str):
        """
        This call will be called for every resource
        """

        self.logger.debug(f"Provider {self.name} calling slice.create {slice_name}")
        slice_object = self.slices[slice_name]
        try:
            slice_object.create_resource(resource=resource)
        except Exception as e:
            # if resource not in slice_object.pending:
            #     slice_object.pending.append(resource)
            raise e

    def delete_resource(self, *, resource: dict, slice_name: str):
        slice_object = self.slices[slice_name]
        slice_object.delete_resource(resource=resource)

    def get_state(self) -> ProviderState:
        """
        Returns state of resources
        """
        slice_states = []

        for slice_object in self.slices.values():
            slice_state = slice_object.get_state()

            if slice_state.network_states or slice_state.node_states or slice_state.pending:
                slice_states.append(slice_state)

        return ProviderState(self.type, self.name, dict(), slice_states)
