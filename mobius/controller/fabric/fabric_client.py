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
import traceback
from typing import List

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.resources import Resources
from fabrictestbed_extensions.fablib.slice import Slice

from mobius.controller.api.api_client import ApiClient
from mobius.controller.util.config import Config

# XXX monkeypatch fablic Slice
def register_callback(self, cb):
    self.callbacks.append(cb)
Slice.callbacks = []
Slice.register_callback = register_callback

class FabricClient(ApiClient):
    def __init__(self, *, logger: logging.Logger, fabric_config: dict):
        """ Constructor """
        self.logger = logger
        self.fabric_config = fabric_config
        self.node_counter = 0
        self.slices = {}

    def setup_environment(self, *, site: str):
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

        # import json
        #
        # print(json.dumps(fablib.get_config(), indent=4))

    def get_resources(self, slice_id: str = None, slice_name: str = None) -> List[Slice] or None:
        if slice_id is None and slice_name is None and len(self.slices) == 0:
            return None
        try:
            result = []
            self.logger.info("get slice_id")
            if slice_id is not None:
                self.logger.info("slice_id: " + str(slice_id))
                result.append(fablib.get_slice(slice_id=slice_id))
            elif slice_name is not None:
                self.logger.info("slice id is none. slice name: " + slice_name)
                result.append(fablib.get_slice(name=slice_name))
            else:
                result = self.slices.values()
            return result
        except Exception as e:
            self.logger.info(f"Exception: {e}")

    def get_available_resources(self) -> Resources:
        try:
            available_resources = fablib.get_available_resources()
            self.logger.info(f"Available Resources: {available_resources}")
            return available_resources
        except Exception as e:
            self.logger.info(f"Error: {e}")

    def get_network_vlans(self):
        return

    def add_network(self, slice_object: Slice, resource: dict):
        site = resource.get(Config.RES_SITE)
        pool_start = resource.get(Config.RES_NET_POOL_START, None)
        pool_end = resource.get(Config.RES_NET_POOL_END, None)
        gateway = resource.get(Config.RES_NET_GATEWAY, None)
        stitch_provider = resource.get(Config.RES_NET_STITCH_PROV, None)
        callback = resource.get(Config.RES_NET_CALLBACK, None)

        if callback:
            # We need to wait or modify before create
            pass

    def add_node(self, slice_object: Slice, resource: dict):
        interface_list = []
        node_count = resource.get(Config.RES_COUNT)
        node_name_prefix = resource.get(Config.RES_NAME_PREFIX)
        image = resource.get(Config.RES_IMAGE)
        nic_model = resource.get(Config.RES_NIC_MODEL)
        network_type = resource.get(Config.RES_NETWORK)[Config.RES_TYPE]
        site = resource.get(Config.RES_SITE)
        cores = resource.get(Config.RES_FLAVOR)[Config.RES_FLAVOR_CORES]
        ram = resource.get(Config.RES_FLAVOR)[Config.RES_FLAVOR_RAM]
        disk = resource.get(Config.RES_FLAVOR)[Config.RES_FLAVOR_DISK]
        if site == Config.FABRIC_RANDOM:
            site = fablib.get_random_site()

        # Add node
        for i in range(node_count):
            node_name = f"{node_name_prefix}{self.node_counter}"
            self.node_counter += 1
            node = slice_object.add_node(name=node_name, image=image, site=site, cores=cores, ram=ram, disk=disk)

            iface = node.add_component(model=nic_model, name=f"{node_name}-nic1").get_interfaces()[0]
            interface_list.append(iface)

        # Layer3 Network (provides data plane internet access)
        #slice_object.add_l3network(name=f"{site}-network", interfaces=interface_list, type=network_type)

    def add_resources(self, *, resource: dict, slice_name: str) -> Slice or None:
        if resource.get(Config.RES_COUNT) < 1:
            return None
        # Create Slice
        if slice_name in self.slices:
            self.logger.info(f"Slice {slice_name} already exists!")
            slice_object = self.slices[slice_name]
        else:
            slice_object = fablib.new_slice(slice_name)
            self.slices[slice_name] = slice_object

        self.logger.debug(f"Adding {resource} to {slice_name}")
        rtype = resource.get(Config.RES_TYPE)
        if rtype == Config.RES_TYPE_NETWORK.lower():
            self.add_network(slice_object, resource)
        else:
            self.add_node(slice_object, resource)
        return slice_object

    def submit_and_wait(self, *, slice_object: Slice) -> str or None:
        try:
            if slice_object is None:
                raise Exception("Add Resources to the Slice, before calling create")

            # Check if slice already exists; return existing slice
            existing_slices = self.get_resources(slice_name=slice_object.get_name())

            if existing_slices is not None:
                existing_slices = [slice_object for slice_object in existing_slices if slice_object is not None]

                if len(existing_slices) > 0:
                    self.slices[slice_object.get_name()] = existing_slices[0]
                    return existing_slices[0].get_slice_id()

            # See if there are callbacks with info to modify slice resources
            for cb in slice_object.callbacks:
                data = cb()
                self.logger.info(f"Callback data: {data} (Available VLANs)")
                if not len(data):
                    exit(1)

            # Check if the slice has more than one site then add a layer2 network
            # Submit Slice Request
            self.logger.debug("Submit slice request")
            slice_id = slice_object.submit(wait=False)
            self.logger.debug("Waiting for the slice to Stable")
            slice_object.wait(progress=True)
            slice_object.update()
            slice_object.post_boot_config()
            self.logger.debug("Slice provisioning successful")
            return slice_id
        except Exception as e:
            self.logger.error(f"Exception occurred: {e}")
            self.logger.error(traceback.format_exc())
        return None

    def create_resources(self, *, slice_id: str = None, slice_name: str = None, rtype: str = None):
        for sname, sobj in self.slices.items():
            self.logger.info(f"Creating FABRIC slice {sname}")
            self.submit_and_wait(slice_object=sobj)

    def delete_resources(self, *, slice_id: str = None, slice_name: str = None):
        if slice_id is None and slice_name is None and len(self.slices) == 0:
            return None
        try:
            if slice_id is not None:
                slice_object = fablib.get_slice(slice_id=slice_id)
                slice_object.delete()
            elif slice_name is not None:
                slice_object = fablib.get_slice(slice_name)
                slice_object.delete()
            else:
                for s in self.slices.values():
                    s.delete()
        except Exception as e:
            self.logger.info(f"Fail: {e}")
