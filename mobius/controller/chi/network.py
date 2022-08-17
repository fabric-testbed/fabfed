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
import os
import time
import json

import chi
from chi.lease import Lease, get_lease_id, get_node_reservation
from chi.server import get_server

class Network:
    def __init__(self, *, name: str, site: str, project_name: str,
                 logger: logging.Logger, slice_name: str, pool_start: str,
                 pool_end: str, gateway: str, stitch_provider: str):
        self.name = name
        self.site = site
        self.project_name = project_name
        self.slice_name = slice_name
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
            if status == 'ERROR':
                self.logger.error("Lease is in ERROR state")
                return False
            elif status == 'ACTIVE':
                self.logger.info("Lease is in ACTIVE state")
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
        except Exception as e:
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
        # Select your project
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')

        # Select your site
        chi.use_site(self.site)

        if not self.__create_lease():
            return

        # Created Lease is not Active
        if not self.__is_lease_active():
            self.logger.error("Stopping the provisioning as the lease could not be created")
            return

        self.logger.info(f"Using the lease {self.leased_resource_name}")

        network_vlan = None
        while network_vlan == None:
            try:
                #Get the network
                chameleon_network = chi.network.get_network(self.name)

                #Get the network ID
                chameleon_network_id = chameleon_network['id']
                print(f'Chameleon Network ID: {chameleon_network_id}')

                #Get the VLAN tag (needed for FABRIC stitching)
                network_vlan = chameleon_network['provider:segmentation_id']
                self.logger.info(f'network_vlan: {network_vlan}')
                self.vlans.append(network_vlan)
            except:
                self.logger.info(f'Chameleon Network is not ready. Trying again!')
                time.sleep(10)

    def delete(self):
        net_id = chi.server.get_network_id(f"{self.leased_resource_name}")
        if net_id is not None:
            self.logger.info("Deleting network")
            chi.server.delete_server(net_id=net_id)
