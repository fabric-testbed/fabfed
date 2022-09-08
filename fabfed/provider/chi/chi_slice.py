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

from fabfed.model import Slice
from fabfed.model.state import SliceState
from fabfed.provider.chi.chi_network import ChiNetwork
from fabfed.provider.chi.chi_node import ChiNode
from fabfed.util.config import Config


class ChiSlice(Slice):
    DEFAULT_NETWORKS = ["sharednet1", "sharedwan1", "containernet1"]

    def __init__(self, *, name: str, logger: logging.Logger, key_pair: str, project_name: str):
        super().__init__(name=name)
        self.logger = logger
        self.key_pair = key_pair
        self.project_name = project_name
        self.resource_listener = None

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def add_network(self, resource: dict):
        site = resource.get(Config.RES_SITE)
        subnet = resource.get(Config.RES_SUBNET)
        pool_start = resource.get(Config.RES_NET_POOL_START, None)
        pool_end = resource.get(Config.RES_NET_POOL_END, None)
        gateway = resource.get(Config.RES_NET_GATEWAY, None)
        stitch_provider = resource.get(Config.RES_NET_STITCH_PROV, None)

        net_name = resource.get(Config.RES_NAME_PREFIX)
        net = ChiNetwork(name=net_name, site=site, logger=self.logger,
                         slice_name=self.name, subnet=subnet, pool_start=pool_start, pool_end=pool_end,
                         gateway=gateway, stitch_provider=stitch_provider,
                         project_name=self.project_name)
        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(self, self.name, vars(net))

    def add_node(self, resource: dict):
        site = resource.get(Config.RES_SITE)
        network = resource.get(Config.RES_NETWORK)

        if not isinstance(network, str):
            found = False

            for net in self._networks:
                if net.name == network.resource.name:
                    net_vars = vars(net)
                    network = net_vars[network.attribute]
                    found = True
                    break

            if not found:
                raise Exception(f"could not resolve internal network dependency {network}")

        node_count = resource.get(Config.RES_COUNT, 1)
        image = resource.get(Config.RES_IMAGE)
        node_name_prefix = resource.get(Config.RES_NAME_PREFIX)
        flavor = resource.get(Config.RES_FLAVOR)[Config.RES_FLAVOR_NAME]

        for n in range(0, node_count):
            node_name = f"{node_name_prefix}{n}"
            node = ChiNode(name=node_name, image=image, site=site, flavor=flavor, logger=self.logger,
                           key_pair=self.key_pair, slice_name=self.name, network=network,
                           project_name=self.project_name)
            self._nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(self, self.name, vars(node))

    def add_resource(self, *, resource: dict):
        rtype = resource.get(Config.RES_TYPE)
        if rtype == Config.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        else:
            self.add_node(resource)

    def create(self):
        for n in self._networks:
            n.create()

            if self.resource_listener:
                self.resource_listener.on_created(self, self.name, vars(n))

        for n in self._nodes:
            n.create()

            if self.resource_listener:
                self.resource_listener.on_created(self, self.name, vars(n))

    def destroy(self, *, slice_state: SliceState):
        node_states = slice_state.node_states

        for node_state in node_states:
            self.logger.info(f"Deleting node: {node_state}")
            site = node_state.attributes.get('site')

            node = ChiNode(name=node_state.name, image=None, site=site, flavor=None, logger=self.logger,
                           key_pair=None, slice_name=self.name, network=None,
                           project_name=self.project_name)
            node.delete()

        network_states = slice_state.network_states

        for network_state in network_states:
            self.logger.info(f"Deleting node: {network_state}")
            site = network_state.attributes.get('site')

            net = ChiNetwork(name=network_state.name, site=site, logger=self.logger,
                             slice_name=self.name, subnet=None, pool_start=None, pool_end=None,
                             gateway=None, stitch_provider=None,
                             project_name=self.project_name)
            net.delete()