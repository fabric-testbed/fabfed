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

from ipaddress import IPv4Address, IPv4Network

from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.slice import Slice

from mobius.controller.util.config import Config
from mobius.models import AbstractNetwork


class FabricNetwork(AbstractNetwork):
    def __init__(self, *, delegate: NetworkService, subnet: IPv4Network, pool_start: IPv4Address, pool_end: IPv4Address):
        self.delegate = delegate
        self.subnet = subnet
        self.pool_start = pool_start
        self.pool_end = pool_end
        self.name = delegate.get_name()

    def available_ips(self):
        available_ips = []

        for ip_int in range(int(self.pool_start) + 1, int(self.pool_end) + 1):
            available_ips.append(IPv4Address(ip_int))

        return available_ips

    def get_reservation_id(self):
        self.delegate.get_reservation_id()

    def get_site(self):
        return self.delegate.get_name()


class NetworkBuilder:
    def __init__(self,  slice_object: Slice, resource: dict):
        self.slice_object = slice_object
        self.facility_port_vlan = None

        for resolved_dependency in resource['resolved_dependencies']:
            self.facility_port_vlan = str(resolved_dependency.value[0])
            break

        self.facility_port = 'Chameleon-StarLight'
        self.facility_port_site = resource.get(Config.RES_SITE)
        self.interfaces = []
        self.net_name = f'net_facility_port'
        from ipaddress import IPv4Address, IPv4Network

        self.subnet = IPv4Network(resource.get(Config.RES_SUBNET))
        self.pool_start = IPv4Address(resource.get(Config.RES_NET_POOL_START))
        self.pool_end = IPv4Address(resource.get(Config.RES_NET_POOL_END))
        self.net = None

    def handle_facility_port(self):
        facility_port = self.slice_object.add_facility_port(name=self.facility_port, site=self.facility_port_site,
                                                            vlan=self.facility_port_vlan)
        facility_port_interface = facility_port.get_interfaces()[0]
        self.interfaces.append(facility_port_interface)

    def handle_l2network(self, interfaces):
        assert len(interfaces) > 0
        assert len(self.interfaces) == 1
        self.interfaces.extend(interfaces)
        self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name, interfaces=self.interfaces)

    def build(self) -> FabricNetwork:
        assert self.net
        assert self.subnet
        assert self.pool_start
        assert self.pool_end
        return FabricNetwork(delegate=self.net, subnet=self.subnet, pool_start=self.pool_start, pool_end=self.pool_end)
