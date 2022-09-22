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

from fabfed.model import Slice
from ...util.constants import Constants
from .fabric_network import NetworkBuilder, FabricNetwork
from .fabric_node import FabricNode, NodeBuilder


class FabricSlice(Slice):
    def __init__(self, *, label, name: str, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.notified_create = False

        from fabrictestbed_extensions.fablib.fablib import fablib

        # noinspection PyBroadException
        try:
            self.slice_object = fablib.get_slice(name=name)
        except Exception:
            self.slice_object = None

        if self.slice_object:
            self.slice_created = True
        else:
            self.slice_created = False
            self.slice_object = fablib.new_slice(name)

    def add_network(self, resource: dict):
        if not resource['resolved_dependencies']:
            if resource not in self.pending:
                self.logger.info(f"Adding to pending: {resource['name_prefix']}")
                self.pending.append(resource)
            return

        self.logger.info(f"I have resolved dependencies {resource['resolved_dependencies']}")
        # Double check that vlan is satisfied
        label = resource.get(Constants.LABEL)
        network_builder = NetworkBuilder(label, self.slice_object, resource)
        network_builder.handle_facility_port()
        interfaces = []   # TODO handle this internal dependency

        for node in self._nodes:
            interfaces.append(node.get_interfaces()[0])

        assert len(interfaces) > 0
        network_builder.handle_l2network(interfaces)
        net = network_builder.build()
        self._networks.append(net)

        if resource in self.pending:
            self.pending.remove(resource)

        if self.resource_listener:
            self.resource_listener.on_added(self, self.name, vars(net))

    def add_node(self, resource: dict):
        node_count = resource.get(Constants.RES_COUNT, 1)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        nic_model = resource.get(Constants.RES_NIC_MODEL, 'NIC_Basic')
        label = resource.get(Constants.LABEL)

        for i in range(node_count):
            name = f"{name_prefix}{i}"
            node_builder = NodeBuilder(label, self.slice_object, name, resource)
            node_builder.add_component(model=nic_model, name="nic1")
            node = node_builder.build()
            self._nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(self, self.name, vars(node))

    def add_resource(self, *, resource: dict):
        # TODO we need to handle modified config after slice has been created. now exception will be thrown
        if self.slice_created:
            rtype = resource.get(Constants.RES_TYPE)
            label = resource.get(Constants.LABEL)

            if rtype == Constants.RES_TYPE_NODE.lower():
                node_count = resource.get(Constants.RES_COUNT, 1)
                name_prefix = resource.get(Constants.RES_NAME_PREFIX)

                for i in range(node_count):
                    name = f"{name_prefix}{i}"
                    delegate = self.slice_object.get_node(name)
                    fabric_node = FabricNode(label=label, delegate=delegate)
                    self._nodes.append(fabric_node)

                    if self.resource_listener:
                        self.resource_listener.on_added(self, self.name, vars(fabric_node))
            elif rtype == Constants.RES_TYPE_NETWORK.lower():
                delegates = self.slice_object.get_network_services()
                # noinspection PyTypeChecker
                fabric_network = FabricNetwork(label=label,
                                               delegate=delegates[0],
                                               subnet=None,
                                               pool_start=None,
                                               pool_end=None)
                self._networks.append(fabric_network)

                if self.resource_listener:
                    self.resource_listener.on_added(self, self.name, vars(fabric_network))
            else:
                raise Exception("Unknown resource ....")
            return

        rtype = resource.get(Constants.RES_TYPE)
        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        elif rtype == Constants.RES_TYPE_NODE.lower():
            self.add_node(resource)
        else:
            raise Exception("Unknown resource ....")

    def _submit_and_wait(self) -> str or None:
        try:
            # TODO Check if the slice has more than one site then add a layer2 network
            # Submit Slice Request
            self.logger.info("Submit slice request")
            slice_id = self.slice_object.submit(wait=False)
            self.logger.info("Waiting for the slice to Stable")
            self.slice_object.wait(progress=True)

            try:
                self.slice_object.update()
                self.slice_object.post_boot_config()
            except Exception as e:
                self.logger.warning(f"Exception occurred while update/post_boot_config: {e}")

            self.logger.info(f"Slice provisioning successful {self.slice_object.get_state()}")
            return slice_id
        except Exception as e:
            self.logger.error(f"Exception occurred: {e}")
            self.logger.error(traceback.format_exc())
            raise e

    def create(self,):
        if self.slice_created:
            if not self.notified_create:
                self.logger.info(f"already provisioned. Will not bother to create any resource to {self.name}")
            else:
                self.logger.debug(f"already provisioned. Will not bother to create any resource to {self.name}")

            if not self.notified_create and self.resource_listener:
                for node in self.nodes:
                    self.resource_listener.on_created(self, self.name, vars(node))

                for net in self.networks:
                    self.resource_listener.on_created(self, self.name, vars(net))

                self.notified_create = True

            return

        for resource in self.pending:
            self.add_resource(resource=resource)

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        self._submit_and_wait()
        self.slice_created = True

        # TODO WHY ARE WE RELOADING?
        temp = []

        for node in self.nodes:
            delegate = self.slice_object.get_node(node.name)
            temp.append(FabricNode(label=node.label, delegate=delegate))

        self._nodes = temp

        if self.networks:
            from ipaddress import IPv4Network
            available_ips = self._networks[0].available_ips()
            subnet = IPv4Network(self._networks[0].subnet)
            net_name = self._networks[0].name

            for node in self._nodes:
                iface = node.get_interface(network_name=net_name)
                node_addr = available_ips.pop(0)
                iface.ip_addr_add(addr=node_addr, subnet=subnet)

        if self.resource_listener:
            for node in self.nodes:
                self.resource_listener.on_created(self, self.name, vars(node))

            for net in self.networks:
                self.resource_listener.on_created(self, self.name, vars(net))

            self.notified_create = True

    def destroy(self, *, slice_state):
        if self.slice_created:
            self.slice_object.delete()
            self.slice_created = False
