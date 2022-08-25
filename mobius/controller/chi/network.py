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
import json
import logging
import time

import chi
# from chi.lease import Lease
# from chi.server import get_server


class Network:
    def __init__(self, *, name: str, site: str, project_name: str,
                 logger: logging.Logger, slice_name: str, subnet: str, pool_start: str,
                 pool_end: str, gateway: str, stitch_provider: str):
        self.name = name
        self.site = site
        self.project_name = project_name
        self.slice_name = slice_name
        self.subnet = subnet
        self.pool_start = pool_start
        self.pool_end = pool_end
        self.gateway = gateway
        self.stitch_provider = stitch_provider
        self.lease = None
        self.logger = logger
        self.retry = 5
        self.state = None
        self.leased_resource_name = f'{self.slice_name}-{self.name}'
        self.vlans = list()

    def __is_lease_active(self) -> bool:
        lease = chi.lease.get_lease(self.leased_resource_name)

        if lease is not None:
            status = lease["status"]
            self.logger.debug(f"Lease {self.leased_resource_name} is in state {status}")

            if status == 'ERROR':
                return False
            elif status == 'ACTIVE':
                return True

        return False

    def __delete_lease(self):
        self.logger.info(f"Deleting lease: {self.leased_resource_name}")
        chi.lease.delete_lease(self.leased_resource_name)

    def __create_lease(self) -> bool:
        # Check if the lease exists
        existing_lease = None
        try:
            existing_lease = chi.lease.get_lease(self.leased_resource_name)
        except:
            self.logger.info(f"No lease found with name: {self.leased_resource_name}")

        # Lease Exists
        if existing_lease is not None:
            # Lease is not ACTIVE; delete it
            if not self.__is_lease_active():
                self.logger.info("Deleting the existing non-Active lease")
                self.__delete_lease()
            # Use existing lease
            else:
                return True

        # Lease doesn't exist Create a Lease
        self.logger.info(f"Creating the lease - {self.leased_resource_name}")
        reservations = [{
            "resource_type": "network",
            "network_name": self.name,
            "network_properties": "",
            "resource_properties": json.dumps(
                ["==", "$stitch_provider", self.stitch_provider]
            ),
        }]
        chi.lease.create_lease(lease_name=self.leased_resource_name, reservations=reservations)

        for i in range(self.retry):
            try:
                self.logger.info(f"Waiting for the lease to be Active try={i+1}")
                chi.lease.wait_for_active(self.leased_resource_name)
                return True
            except:
                self.logger.warning(f"Error occurred while waiting for the lease to be Active tried  {i+1}")

        return False

    def get_reservation_id(self):
        existing_lease = None
        try:
            existing_lease = chi.lease.get_lease(self.leased_resource_name)
        except Exception as e:
            self.logger.info(f"No lease found with name: {self.leased_resource_name}")
            return existing_lease
        return existing_lease["reservations"][0]["id"]

    def get_vlans(self) -> list:
        return self.vlans

    def create(self):
        # Select your project  and your site
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')
        chi.use_site(self.site)

        if not self.__create_lease():
            self.logger.error(f"Stopping the provisioning as the lease {self.leased_resource_name} could not be created")
            return

        if not self.__is_lease_active():
            self.logger.error(f"Stopping the provisioning as the lease {self.leased_resource_name} is not active")
            return

        self.logger.info(f"Using Active lease {self.leased_resource_name}")

        network_vlan = None

        while not network_vlan:
            try:
                chameleon_network = chi.network.get_network(self.name)
                chameleon_network_id = chameleon_network['id']
                network_vlan = chameleon_network['provider:segmentation_id']
            except:
                self.logger.info(f'Chameleon Network is not ready. Trying again!')
                time.sleep(10)

        self.logger.info(f'Chameleon: network_name: {self.name}, network_vlan: {network_vlan}')
        self.vlans.append(network_vlan)

        chameleon_subnet_name = self.name + '-subnet'
        try:
            chameleon_subnet = chi.network.get_subnet(chameleon_subnet_name)
        except Exception:
            chameleon_subnet = None

        if not chameleon_subnet:
            chameleon_subnet = chi.network.create_subnet(chameleon_subnet_name, chameleon_network_id,
                                                         cidr=self.subnet,
                                                         allocation_pool_start=self.pool_start,
                                                         allocation_pool_end=self.pool_end,
                                                         gateway_ip=self.gateway)

        self.logger.debug(f'Chameleon: subnet: {chameleon_subnet}')
        chameleon_router_name = self.name + '-router'

        chameleon_router = None

        # we do not use get as it throws an exception if not found. So we list them
        for router in chi.network.list_routers():
            if router['name'] == chameleon_router_name:
                chameleon_router = router
                break

        if chameleon_router:
            self.logger.info(f'Chameleon: router already created  : {chameleon_router_name}')
            self.logger.debug(f'Chameleon: router: {chameleon_router}')
        else:
            chameleon_router = chi.network.create_router(chameleon_router_name, gw_network_name='public')
            chi.network.add_subnet_to_router_by_name(chameleon_router_name, chameleon_subnet_name)
            self.logger.info(f'Chameleon: router created : {chameleon_router_name}')
            self.logger.debug(f'Chameleon: router: {chameleon_router}')

    def delete(self):
        net_id = chi.server.get_network_id(f"{self.name}")

        if net_id:
            self.logger.info(f"Deleting network {self.name} net_id={net_id}")
            chi.network.delete_network(net_id=net_id)
