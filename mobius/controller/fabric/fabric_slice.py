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
from collections import namedtuple

from fabrictestbed_extensions.fablib.fablib import fablib
from fabrictestbed_extensions.fablib.slice import Slice
from tabulate import tabulate

from mobius.controller.util.config import Config
from mobius.models import AbstractResourceListener
from mobius.models import AbstractSlice
from .fabric_node import FabricNode, NodeBuilder
from .fabric_network import FabricNetwork, NetworkBuilder


class FabricSlice(AbstractSlice, AbstractResourceListener):
    def __init__(self, *, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self._nodes = list()
        self._networks = list()
        self._services = list()
        self.pending = []
        self.slice_object: Slice = fablib.get_slice(name=name)

        if self.slice_object:
            self.slice_created = True

            for node in self.slice_object.get_nodes():
                self._nodes.append(FabricNode(delegate=node))

        else:
            self.slice_created = False
            self.slice_object = fablib.new_slice(name)

        self.resource_listener = None

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, source, slice_name, resource: dict):
        pass

    def on_deleted(self, source, slice_name, resource):
        pass

    def on_created(self, source, slice_name, resource):
        for pending_resource in self.pending:
            for dependency in pending_resource['dependencies']:
                temp = dependency[1]

                # TODO add temp.type to this if statement ....
                if temp.slice.name == slice_name and temp.name == resource['name']:
                    resolved_dependencies = pending_resource['resolved_dependencies']
                    ResolvedDependency = namedtuple("ResolvedDependency", "attr  value")
                    value = resource[dependency[2]]

                    if isinstance(value, list):
                        resolved_dependency = ResolvedDependency(attr=dependency[0], value=tuple(value))
                    else:
                        resolved_dependency = ResolvedDependency(attr=dependency[0], value=value)

                    resolved_dependencies.add(resolved_dependency)

    def add_network(self, resource: dict):
        if not resource['resolved_dependencies']:
            if resource not in self.pending:
                self.pending.append(resource)
            return

        self.logger.info(f"I have resolved dependencies {resource['resolved_dependencies']}")
        # Double check that vlan is satisfied
        network_builder = NetworkBuilder(self.slice_object, resource)
        network_builder.handle_facility_port()
        interfaces = []   # TODO handle this internal dependency

        for node in self.nodes:
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
        node_count = resource.get(Config.RES_COUNT, 1)
        name_prefix = resource.get(Config.RES_NAME_PREFIX)
        nic_model = resource.get(Config.RES_NIC_MODEL, 'NIC_Basic')

        for i in range(node_count):
            name = f"{name_prefix}{i}"
            node_builder = NodeBuilder(self.slice_object, name, resource)
            node_builder.add_component(model=nic_model, name="nic1")
            node = node_builder.build()
            self._nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(self, self.name, vars(node))

    def add_resource(self, *, resource: dict):
        if self.slice_created:
            return

        rtype = resource.get(Config.RES_TYPE)
        if rtype == Config.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        elif rtype == Config.RES_TYPE_NODE.lower():
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
            return None

    def create(self, rtype: str = None):
        if self.slice_created:
            self.logger.warning(f"already provisioned. Will not bother to create any resource to {self.name}")
            return

        for resource in self.pending:
            self.add_resource(resource=resource)

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        self._submit_and_wait()
        self.slice_created = True

        self._nodes = []

        for node in self.slice_object.get_nodes():
            self._nodes.append(FabricNode(delegate=node))

        available_ips = self._networks[0].available_ips()
        subnet = self._networks[0].subnet
        net_name = self._networks[0].name

        for node in self.nodes:
            iface = node.get_interface(network_name=net_name)
            node_addr = available_ips.pop(0)
            iface.ip_addr_add(addr=node_addr, subnet=subnet)

    def delete(self, rtpe: str = None):
        if self.slice_created:
            self.slice_object.delete()

    def list_nodes(self) -> list:
        table = []
        for node in self._nodes:
            table.append([node.get_reservation_id(),
                          node.get_name(),
                          node.get_site(),
                          node.get_flavor(),
                          node.get_image(),
                          node.get_management_ip(),
                          node.get_reservation_state()
                          ])

        return tabulate(table, headers=["ID", "Name", "Site", "Flavor", "Image",
                                        "Management IP", "State"])

    def __str__(self):
        table = [["Slice Name", self.name],
                 ]

        return tabulate(table)
