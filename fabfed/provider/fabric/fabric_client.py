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
from typing import List, Dict

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.resources import Resources
from fabfed.provider.api.api_client import ApiClient
from fabfed.provider.fabric.fabric_slice import FabricSlice
from fabfed.util.config import Config
from fabfed.model import AbstractResourceListener


class FabricClient(ApiClient, AbstractResourceListener):
    def __init__(self, *, logger: logging.Logger, fabric_config: dict):
        """ Constructor """
        self.logger = logger
        self.fabric_config = fabric_config
        self.slices: Dict[str, FabricSlice] = {}
        self.resource_listener = None

    def setup_environment(self):
        import os

        fabric_config = self.fabric_config

        os.environ['FABRIC_CREDMGR_HOST'] = fabric_config.get(Config.FABRIC_CM_HOST)
        os.environ['FABRIC_ORCHESTRATOR_HOST'] = fabric_config.get(Config.FABRIC_OC_HOST)
        os.environ['FABRIC_TOKEN_LOCATION'] = fabric_config.get(Config.FABRIC_TOKEN_LOCATION)
        os.environ['FABRIC_PROJECT_ID'] = fabric_config.get(Config.FABRIC_PROJECT_ID)

        os.environ['FABRIC_BASTION_HOST'] = fabric_config.get(Config.FABRIC_BASTION_HOST)
        os.environ['FABRIC_BASTION_USERNAME'] = fabric_config.get(Config.FABRIC_BASTION_USER_NAME)
        os.environ['FABRIC_BASTION_KEY_LOCATION'] = fabric_config.get(Config.FABRIC_BASTION_KEY_LOCATION)

        os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE'] = fabric_config.get(Config.RUNTIME_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'] = fabric_config.get(Config.RUNTIME_SLICE_PUBLIC_KEY_LOCATION)

        fablib.fablib_object = fablib()
        # fablib.show_config()

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, source, slice_name, resource: dict):
        pass

    def on_created(self, source, slice_name, resource: dict):
        for fabric_slice in self.slices.values():
            fabric_slice.on_created(source, slice_name, resource)

    def on_deleted(self, source, slice_name, resource):
        pass

    def init_slice(self, *, resource: dict, slice_name: str):
        self.logger.info(f"initializing  slice {slice_name}: slice_attributes={resource}")

        if slice_name not in self.slices:
            fabric_slice = FabricSlice(name=slice_name, logger=self.logger)
            self.slices[slice_name] = fabric_slice

    def get_resources(self, *, slice_name: str = None) -> List[FabricSlice]:
        if not slice_name:
            fabric_slices = []
            fabric_slices.extend(self.slices.values())
            return fabric_slices

        if slice_name in self.slices:
            return [self.slices[slice_name]]

    def get_available_resources(self) -> Resources:
        try:
            available_resources = fablib.get_available_resources()
            self.logger.info(f"Available Resources: {available_resources}")
            return available_resources
        except Exception as e:
            self.logger.info(f"Error: {e}")

    def add_resources(self, *, resource: dict, slice_name: str):
        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")
        self.logger.debug(f"Adding {resource} to {slice_name}")

        if resource.get(Config.RES_COUNT, 1) < 1:
            self.logger.debug(f"will not add {resource['name_prefix']} to {slice_name}: Count is zero")
            return

        if slice_name in self.slices:
            fabric_slice = self.slices[slice_name]
        else:
            fabric_slice = FabricSlice(name=slice_name, logger=self.logger)
            self.slices[slice_name] = fabric_slice

        fabric_slice.add_resource(resource=resource)

    def create_resources(self, *, slice_name: str,  rtype: str):
        self.logger.info(f"Creating FABRIC using slice {slice_name} rtype={rtype}")

        fabric_slice = self.slices[slice_name]
        fabric_slice.create()

    def delete_resources(self, *, slice_name: str = None):
        if slice_name:
            fabric_slice = self.slices[slice_name]
            self.logger.info(f"Deleting FABRIC slice {slice_name}")
            fabric_slice.delete()
            return

        for slice_name, fabric_slice in self.slices.items():
            self.logger.info(f"Deleting FABRIC slice {fabric_slice}")
            fabric_slice.delete()
