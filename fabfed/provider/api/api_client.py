#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 RENCI NRIG
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author Komal Thareja (kthare10@renci.org)
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

    @abstractmethod
    def add_resource(self, *, resource: dict, slice_name: str):
        """
        Build the topology
        """

    def create_resources(self, *,  slice_name: str):
        """
        This call will be called for every resource
        """

        self.logger.info(f"Creating slice {slice_name}")
        chi_slice = self.slices[slice_name]
        chi_slice.create()

    def get_state(self) -> ProviderState:
        """
        Returns state of resources
        """
        slice_states = []

        for slice_object in self.slices.values():
            slice_states.append(slice_object.get_state())

        return ProviderState(self.type, self.name, dict(), slice_states)

    def destroy_resources(self, *, provider_state: ProviderState):
        """
        Delete provisioned resources
         """
        for slice_state in provider_state.slice_states:
            slice_object = self.slices[slice_state.name]
            self.logger.info(f"Deleting slice {slice_state.name}")
            slice_object.destroy(slice_state=slice_state)
