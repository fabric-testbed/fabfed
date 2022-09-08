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

from fabfed.provider.api.api_client import Provider
from fabfed.util.config import Config
from fabfed.model import ResourceListener


class FabricProvider(Provider, ResourceListener):
    def __init__(self, *, type, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, name=name, logger=logger, config=config)

    def setup_environment(self):
        import os

        os.environ['FABRIC_CREDMGR_HOST'] = self.config.get(Config.FABRIC_CM_HOST)
        os.environ['FABRIC_ORCHESTRATOR_HOST'] = self.config.get(Config.FABRIC_OC_HOST)
        os.environ['FABRIC_TOKEN_LOCATION'] = self.config.get(Config.FABRIC_TOKEN_LOCATION)
        os.environ['FABRIC_PROJECT_ID'] = self.config.get(Config.FABRIC_PROJECT_ID)

        os.environ['FABRIC_BASTION_HOST'] = self.config.get(Config.FABRIC_BASTION_HOST)
        os.environ['FABRIC_BASTION_USERNAME'] = self.config.get(Config.FABRIC_BASTION_USER_NAME)
        os.environ['FABRIC_BASTION_KEY_LOCATION'] = self.config.get(Config.FABRIC_BASTION_KEY_LOCATION)

        os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE'] = self.config.get(Config.RUNTIME_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'] = self.config.get(Config.RUNTIME_SLICE_PUBLIC_KEY_LOCATION)

        # from fabrictestbed_extensions.fablib.fablib import fablib
        #
        # fablib.show_config()

    def on_added(self, source, slice_name, resource: dict):
        pass

    def on_created(self, source, slice_name, resource: dict):
        for fabric_slice in self.slices.values():
            fabric_slice.on_created(source, slice_name, resource)

    def on_deleted(self, source, slice_name, resource):
        pass

    def init_slice(self, *, slice_config: dict, slice_name: str):
        self.logger.debug(f"initializing  slice {slice_name}: slice_attributes={slice_config}")

        if slice_name not in self.slices:
            from fabfed.provider.fabric.fabric_slice import FabricSlice

            fabric_slice = FabricSlice(name=slice_name, logger=self.logger)
            self.slices[slice_name] = fabric_slice

    def add_resource(self, *, resource: dict, slice_name: str):
        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")
        self.logger.debug(f"Adding {resource} to {slice_name}")

        if resource.get(Config.RES_COUNT, 1) < 1:
            self.logger.debug(f"will not add {resource['name_prefix']} to {slice_name}: Count is zero")
            return

        if slice_name in self.slices:
            fabric_slice = self.slices[slice_name]
        else:
            from fabfed.provider.fabric.fabric_slice import FabricSlice

            fabric_slice = FabricSlice(name=slice_name, logger=self.logger)
            self.slices[slice_name] = fabric_slice

        fabric_slice.add_resource(resource=resource)
