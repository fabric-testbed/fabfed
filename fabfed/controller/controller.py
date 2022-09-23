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
from typing import List

from fabfed.model import Slice
from fabfed.model.state import ProviderState
from fabfed.util.config import Config
from .helper import ControllerResourceListener
from ..util.constants import Constants
from .provider_factory import ProviderFactory


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

        try:
            self.logger.info(f"Starting PLAN_PHASE: Calling ADD ... for {len(resources)} resource(s)")
            for resource in resources:
                slice_config = resource.slice
                provider = self.provider_factory.get_provider(label=slice_config.provider.label)
                slice_name = slice_config.name
                resource_dict = resource.attributes
                resource_dict[Constants.RES_TYPE] = resource.type
                resource_dict[Constants.RES_NAME_PREFIX] = resource.name
                resource_dict[Constants.LABEL] = resource.label

                if resource.has_dependencies():
                    resource_dict['has_dependencies'] = True
                    resource_dict['dependencies'] = resource.dependencies
                    resource_dict['resolved_dependencies'] = set()
                else:
                    resource_dict['has_dependencies'] = False

                provider.add_resource(resource=resource_dict, slice_name=slice_name)
        except Exception as e:
            self.logger.error(f"Exception occurred while adding resources: {e}")
            raise e

    def create(self):
        resources = self.config.get_resource_config()

        try:
            self.logger.info(f"Starting CREATE_PHASE: Calling CREATE ... for {len(resources)} resource(s)")
            for resource in resources:
                provider = self.provider_factory.get_provider(label=resource.slice.provider.label)
                slice_name = resource.slice.name
                provider.create_resources(slice_name=slice_name)
        except Exception as e:
            self.logger.error(f"Exception occurred while creating resources: {e}")
            raise e

    def delete(self, *, provider_states: List[ProviderState]):
        for provider_state in provider_states:
            provider = self.provider_factory.get_provider(label=provider_state.label)
            provider.destroy_resources(provider_state=provider_state)

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
