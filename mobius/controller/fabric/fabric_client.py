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
import sys
import traceback
from typing import List

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.resources import Resources
from fabrictestbed_extensions.fablib.slice import Slice

from mobius.controller.api.api_client import ApiClient
from mobius.controller.util.config import Config

from mobius.models import AbstractResourceListener

# XXX monkeypatch fablic Slice
def register_callback(self, cb, cb_key=None):
    self._callbacks.update({cb_key: cb})
Slice._callbacks = dict()
Slice.register_callback = register_callback


class FabricClient(ApiClient, AbstractResourceListener):
    def __init__(self, *, logger: logging.Logger, fabric_config: dict):
        """ Constructor """
        self.logger = logger
        self.fabric_config = fabric_config
        self.node_counter = 0
        self.slices = {}
        self.slice_created = {}
        self.pending = {}
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

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, source, slice_name, resource: dict):
        pass

    def on_created(self, source, slice_name, resource):
        for pending_resources in self.pending.values():
            for pending_resource in pending_resources:
                for dependency in pending_resource['dependencies']:
                    temp = dependency[1]

                    if temp.slice.name == slice_name and temp.name == resource['name']:
                        resolved_dependencies = pending_resource['resolved_dependencies']
                        resolved_dependency = (dependency[0], resource[dependency[2]])
                        resolved_dependencies.append(resolved_dependency)

    def on_deleted(self, source, slice_name, resource):
        pass

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

    def _add_network(self, slice_object: Slice, resource: dict):
        if resource['resolved_dependencies']:
            print("I have vlan ", resource['resolved_dependencies'], file=sys.stderr)

            if resource in self.pending[slice_object.get_name()]:
                self.pending[slice_object.get_name()].remove(resource)
        else:
            print("I am mising vlan ", resource['resolved_dependencies'], file=sys.stderr)

            if resource not in self.pending[slice_object.get_name()]:
                self.pending[slice_object.get_name()].append(resource)

        # site = resource.get(Config.RES_SITE)
        # pool_start = resource.get(Config.RES_NET_POOL_START, None)
        # pool_end = resource.get(Config.RES_NET_POOL_END, None)
        # gateway = resource.get(Config.RES_NET_GATEWAY, None)
        # stitch_provider = resource.get(Config.RES_NET_STITCH_PROV, None)
        # callback = resource.get(Config.RES_NET_CALLBACK, None)
        #
        # if callback:
        #     # We need to wait or modify before create
        #     pass

    def _add_node(self, slice_object: Slice, resource: dict):
        # TODO interface_list = []
        node_count = resource.get(Config.RES_COUNT, 1)
        node_name = resource.get(Config.RES_NAME_PREFIX)
        image = resource.get(Config.RES_IMAGE)
        nic_model = resource.get(Config.RES_NIC_MODEL, 'NIC_Basic')
        site = resource.get(Config.RES_SITE, Config.FABRIC_RANDOM)
        flavor = resource.get(Config.RES_FLAVOR, {'cores': 2, 'ram': 8, 'disk': 10})
        cores = flavor[Config.RES_FLAVOR_CORES]
        ram = flavor[Config.RES_FLAVOR_RAM]
        disk = flavor[Config.RES_FLAVOR_DISK]

        if site == Config.FABRIC_RANDOM:
            self.logger.info("getting random site ")
            site = fablib.get_random_site()
            self.logger.info(f"getting random site {site}")

        for i in range(node_count):
            node_name = f"{node_name}{i}"
            node = slice_object.add_node(name=node_name, image=image, site=site, cores=cores, ram=ram, disk=disk)
            node.add_component(model=nic_model, name=f"{node_name}-nic1")

            # TODO iface = node.add_component(model=nic_model, name=f"{node_name}-nic1").get_interfaces()[0]
            # TODO interface_list.append(iface)

        # Layer3 Network (provides data plane internet access)
        # slice_object.add_l3network(name=f"{site}-network", interfaces=interface_list, type=network_type)

    def add_resources(self, *, resource: dict, slice_name: str) -> Slice or None:
        if resource.get(Config.RES_COUNT, 1) < 1:
            return None

        if slice_name in self.slices:
            slice_object = self.slices[slice_name]
        else:
            slice_object = fablib.get_slice(name=slice_name)

            if not slice_object:
                slice_object = fablib.new_slice(slice_name)
                self.slices[slice_name] = slice_object
                self.slice_created[slice_name] = False
                self.pending[slice_name] = []
            else:
                self.slices[slice_name] = slice_object
                self.slice_created[slice_name] = True
                self.pending[slice_name] = []

        if self.slice_created[slice_name]:
            self.logger.warning(f"already provisioned ...  will not bother to add any resource to {slice_name}")
            return slice_object

        self.logger.debug(f"Adding {resource} to {slice_name}")
        rtype = resource.get(Config.RES_TYPE)
        if rtype == Config.RES_TYPE_NETWORK.lower():
            self._add_network(slice_object, resource)
        elif rtype == Config.RES_TYPE_NODE.lower():
            self._add_node(slice_object, resource)
        else:
            raise Exception(f"did not expect resource {rtype}")

        return slice_object

    def _submit_and_wait(self, *, slice_object: Slice) -> str or None:
        try:
            # See if there are callbacks with info to modify slice resources
            for cb in slice_object._callbacks:
                data = cb()
                self.logger.info(f"Callback data: {data} (Available VLANs)")
                if not len(data):
                    exit(1)

            # TODO Check if the slice has more than one site then add a layer2 network
            # Submit Slice Request
            self.logger.info("Submit slice request")
            slice_id = slice_object.submit(wait=False)
            self.logger.info("Waiting for the slice to Stable")
            slice_object.wait(progress=True)

            try:
                slice_object.update()
                slice_object.post_boot_config()
            except Exception as e:
                self.logger.warning(f"Exception occurred while update/post_boot_config: {e}")

            self.logger.info(f"Slice provisioning successful {slice_object.get_state()}")
            return slice_id
        except Exception as e:
            self.logger.error(f"Exception occurred: {e}")
            self.logger.error(traceback.format_exc())
            return None

    # noinspection PyUnusedLocal
    def create_resources(self, *, slice_name: str,  rtype: str):
        if self.slice_created[slice_name]:
            self.logger.warning(f"already provisioned ...  will not bother to create any resource to {slice_name}")
            return

        slice_object = self.slices[slice_name]
        pending = self.pending.get(slice_name)

        for resource in pending:
            self.add_resources(resource=resource, slice_name=slice_name)

        if slice_name in self.pending:
            for resource in pending:
                self.add_resources(resource=resource, slice_name=slice_name)

        if pending:
            self.logger.warning(f"still have pending {len(pending)} resources")
            return

        self._submit_and_wait(slice_object=slice_object)
        self.slice_created[slice_name] = True

    def delete_resources(self, *, slice_id: str = None, slice_name: str = None):
        if slice_id is None and slice_name is None and len(self.slices) == 0:
            return None
        try:
            if slice_id is not None:
                slice_object = fablib.get_slice(slice_id=slice_id)
                self.logger.info(f"Deleting  FABRIC slice {slice_object}")
                slice_object.delete()
            elif slice_name is not None:
                slice_object = fablib.get_slice(slice_name)
                self.logger.info(f"Deleting  FABRIC slice {slice_object}")
                slice_object.delete()
            else:
                for slice_object in self.slices.values():
                    self.logger.info(f"Deleting  FABRIC slice {slice_object}")
                    slice_object.delete()
        except Exception as e:
            self.logger.info(f"Fail: {e}")
