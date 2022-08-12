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


# XXX monkeypatch fablic Slice
def register_callback(self, cb, cb_key=None):
    self._callbacks.update({cb_key: cb})
Slice._callbacks = dict()
Slice.register_callback = register_callback


class FabricClient(ApiClient):
    def __init__(self, *, logger: logging.Logger, fabric_config: dict):
        """ Constructor """
        self.logger = logger
        self.fabric_config = fabric_config
        self.node_counter = 0
        self.slices = {}
        self.slice_created = {}
        self.pending = {}

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

    def _add_network(self, slice_object: Slice, resource: dict):
        print("********************** BEGIN ADDING NEWTOWK  ...", file=sys.stderr)
        print(resource['has_dependencies'], file=sys.stderr)
        print(resource['dependencies'], file=sys.stderr)
        network_name = resource['resource_name']
        interfaces = []

        try:
            if resource['has_dependencies']:
                for key, item in resource['dependencies']:
                    # if item[1] != 'node':
                    #     raise Exception("only handling node dependencies for now")

                    # print("&&&&& BbEGIN &&&&&", file=sys.stderr)
                    # print("ME:", resource, file=sys.stderr)
                    # print("key:", key, file=sys.stderr)
                    # print(item.name, file=sys.stderr)
                    # print(item.type, file=sys.stderr)
                    # print(item.attributes, file=sys.stderr)
                    # print("theirslice", item.slice.name, file=sys.stderr)
                    # print("this slice", slice_object.slice_name, file=sys.stderr)
                    # print('count:', item.attributes.get('count', 1), file=sys.stderr)
                    # print("&&&&& END  &&&&&", file=sys.stderr)

                    node_count = item.attributes.get('count', 1)
                    node_name = item.name

                    if node_count == 1:
                        node = slice_object.get_node(name=node_name)
                        print("Coucou:", node.get_name(), file=sys.stderr)
                        iface = node.get_interfaces()[0]
                        interfaces.append(iface)
                        continue

                    for i in range(node_count):
                        node_name = f"{node_name}{i}"
                        node = slice_object.get_node(name=node_name)
                        iface = node.get_interfaces()[0]
                        interfaces.append(iface)

        except Exception as e:
            self.logger.warning(f"Exception attempted when creating network  {network_name}  : {e}")
            # TODO HANDLE LIST
            self.pending[slice_object.get_name()] = [resource]
            print("*********************** END ADDING NEWTOWK  ...", file=sys.stderr)
            return

        print("AHAAAAAAHHHHA:", len(interfaces), file=sys.stderr)
        slice_object.add_l2network(name=network_name, interfaces=interfaces)
        print("*********************** END ADDING NEWTOWK  ...", file=sys.stderr)
        # sys.exit(1)

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
        node_name = resource.get('resource_name')
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

        # Add node
        if node_count == 1:
            node = slice_object.add_node(name=node_name, image=image, site=site, cores=cores, ram=ram, disk=disk)
            node.add_component(model=nic_model, name="nic1")
            return

        for i in range(node_count):
            node_name = f"{node_name}{i}"
            node = slice_object.add_node(name=node_name, image=image, site=site, cores=cores, ram=ram, disk=disk)
            node.add_component(model=nic_model, name=f"{node_name}-nic1")

            # TODO iface = node.add_component(model=nic_model, name=f"{node_name}-nic1").get_interfaces()[0]
            # TODO interface_list.append(iface)

        # Layer3 Network (provides data plane internet access)
        # slice_object.add_l3network(name=f"{site}-network", interfaces=interface_list, type=network_type)

    def add_resources(self, *, resource: dict, slice_name: str) -> Slice or None:
        print("aes_add_resources:", resource, file=sys.stderr)

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
            else:
                self.slices[slice_name] = slice_object
                self.slice_created[slice_name] = True

        # TODO ALLOW NETWORK THIS TO GO THROUGH
        # rtype = resource.get('resource_type')
        # if rtype == Config.RES_TYPE_NETWORK.lower():
        #     self._add_network(slice_object, resource)
        #     return

        if self.slice_created[slice_name]:
            self.logger.warning(f"already provisioned ...  will not bother to add any resource to {slice_name}")
            return slice_object

        self.logger.debug(f"Adding {resource} to {slice_name}")
        rtype = resource.get('resource_type')
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

        print("$$$$$$$$$$$$ BEGIN CREATE", file=sys.stderr)
        slice_object = self.slices[slice_name]
        print("Before", self.pending, file=sys.stderr)

        if slice_name in self.pending:
            pending = self.pending.get(slice_name)
            for resource in pending:
                self.add_resources(resource=resource, slice_name=slice_name)

            # TODO pop only if all pending have been crated
            self.pending.pop(slice_name)

        print("After", self.pending, file=sys.stderr)
        self._submit_and_wait(slice_object=slice_object)
        self.slice_created[slice_name] = True
        print("$$$$$$$$$$$$ END CREATE", file=sys.stderr)

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
