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

from fabfed.model import Network
from fabfed.util.constants import Constants


class FabricNetwork(Network):
    def __init__(self, *, label, delegate: NetworkService, subnet: IPv4Network, pool_start: IPv4Address,
                 pool_end: IPv4Address):
        self.name = delegate.get_name()
        self.site = delegate.get_site()
        super().__init__(label=label, name=self.name, site=self.site)
        self._delegate = delegate
        self.site = delegate.get_site()
        self.slice_name = self._delegate.get_slice().get_name()
        self.type = str(delegate.get_type())
        self.subnet = str(subnet)
        self.pool_start = str(pool_start)
        self.pool_end = str(pool_end)

    def available_ips(self):
        available_ips = []
        pool_start = int(IPv4Address(self.pool_start))
        pool_end = int(IPv4Address(self.pool_end))

        for ip_int in range(pool_start + 1, pool_end + 1):
            available_ips.append(IPv4Address(ip_int))

        return available_ips

    def get_reservation_id(self):
        self._delegate.get_reservation_id()

    def get_site(self):
        return self._delegate.get_name()


class NetworkBuilder:
    def __init__(self, label, slice_object: Slice, name, resource: dict):
        self.slice_object = slice_object
        self.facility_port_vlan = None

        for resolved_dependency in resource['resolved_dependencies']:
            self.facility_port_vlan = str(resolved_dependency.value[0])
            break

        assert self.facility_port_vlan, "missing vlan"

        self.facility_port = 'Chameleon-StarLight'
        self.facility_port_site = resource.get(Constants.RES_SITE)
        self.interfaces = []
        self.net_name = name  # f'net_facility_port'
        from ipaddress import IPv4Address, IPv4Network

        self.subnet = IPv4Network(resource.get(Constants.RES_SUBNET))
        self.pool_start = IPv4Address(resource.get(Constants.RES_NET_POOL_START))
        self.pool_end = IPv4Address(resource.get(Constants.RES_NET_POOL_END))
        self.label = label
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
        return FabricNetwork(label=self.label, delegate=self.net, subnet=self.subnet, pool_start=self.pool_start,
                             pool_end=self.pool_end)
