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

from tabulate import tabulate

from mobius.controller.chi.network import Network
from mobius.controller.chi.node import Node
from mobius.controller.util.config import Config
from mobius.models import AbstractSlice


class Slice(AbstractSlice):
    DEFAULT_NETWORKS = ["sharednet1", "sharedwan1", "containernet1"]

    def __init__(self, *, name: str, logger: logging.Logger, key_pair: str, project_name: str):
        self.name = name
        self.node_counter = 0
        self.logger = logger
        self.key_pair = key_pair
        self.project_name = project_name
        self._nodes = list()
        self._networks = list()
        self._services = list()
        self._callbacks = dict()

    def add_network(self, resource: dict):
        site = resource.get(Config.RES_SITE)
        pool_start = resource.get(Config.RES_NET_POOL_START, None)
        pool_end = resource.get(Config.RES_NET_POOL_END, None)
        gateway = resource.get(Config.RES_NET_GATEWAY, None)
        stitch_provider = resource.get(Config.RES_NET_STITCH_PROV, None)

        net_name = f"Network0"
        net = Network(name=net_name, site=site, logger=self.logger,
                      slice_name=self.name, pool_start=pool_start, pool_end=pool_end,
                      gateway=gateway, stitch_provider=stitch_provider,
                      project_name=self.project_name)
        self._networks.append(net)

    def add_node(self, resource: dict):
        site = resource.get(Config.RES_SITE)
        # Select your network; only sharednet and sharedwan works for now
        network = resource.get(Config.RES_NETWORK, None)
        if network:
            network = network[Config.RES_TYPE]
        if network not in self.DEFAULT_NETWORKS:
            raise Exception("Private network not supported")

        node_count = resource.get(Config.RES_COUNT)
        image = resource.get(Config.RES_IMAGE)
        node_name_prefix = resource.get(Config.RES_NAME_PREFIX)
        flavor = resource.get(Config.RES_FLAVOR)[Config.RES_FLAVOR_NAME]

        for n in range(0, node_count):
            node_name = f"{node_name_prefix}{self.node_counter}"
            self.node_counter += 1
            node = Node(name=node_name, image=image, site=site, flavor=flavor, logger=self.logger,
                        key_pair=self.key_pair, slice_name=self.name, network=network,
                        project_name=self.project_name)
            self._nodes.append(node)

    def add_resource(self, *, resource: dict):
        # Select your site
        rtype = resource.get(Config.RES_TYPE)
        if rtype == Config.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        else:
            self.add_node(resource)

    def create(self, rtype: str = None):
        if rtype in [None, Config.RES_TYPE_NETWORK]:
            for n in self.networks:
                n.create()
        if rtype in [None, Config.RES_TYPE_NODE]:
            for n in self.nodes:
                n.create()

    def delete(self):
        for n in self._nodes:
            self.logger.info(f"Deleting node: {n}")
            n.delete()
        for n in self._networks:
            self.logger.info(f"Deleting network: {n}")
            n.delete()

    def list_nodes(self) -> list:
        table = []
        for node in self.get_nodes():
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
