import json
import logging
import time

import chi
import chi.network
import chi.server

from fabfed.model import Network
from .chi_util import LeaseHelper


class ChiNetwork(Network):
    def __init__(self, *, label, name: str, site: str, project_name: str,
                 logger: logging.Logger, subnet: str, pool_start: str,
                 pool_end: str, gateway: str, stitch_provider: str):
        super().__init__(label=label, name=name, site=site)
        self.project_name = project_name
        # self.slice_name = slice_name
        self.subnet = subnet
        self.pool_start = pool_start
        self.pool_end = pool_end
        self.gateway = gateway
        # TODO assert stitch_provider, "expecting a stitch provider"
        self.stitch_provider = stitch_provider
        self._retry = 10
        self.lease_name = f'{name}-lease'
        self.subnet_name = f'{name}-subnet'
        self.router_name = f'{name}-router'
        self.reservations = [{
            "resource_type": "network",
            "network_name": self.name,
            "network_properties": "",
            "resource_properties": json.dumps(
                ["==", "$stitch_provider", self.stitch_provider]
            ),
        }]
        self.vlans = list()
        self.logger = logger
        self._lease_helper = LeaseHelper(lease_name=self.lease_name, logger=self.logger)

    def get_reservation_id(self):
        return self._lease_helper.get_reservation_id()

    def get_vlans(self) -> list:
        return self.vlans

    def create(self):
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')
        chi.use_site(self.site)
        self._lease_helper.create_lease_if_needed(reservations=self.reservations, retry=self._retry)
        self.logger.info(f"Using active lease {self.lease_name}")

        self.vlans = []
        network_vlan = None
        chameleon_network_id = None

        while not network_vlan:
            try:
                chameleon_network = chi.network.get_network(self.name)
                chameleon_network_id = chameleon_network['id']
                network_vlan = chameleon_network['provider:segmentation_id']
            except Exception as e:
                self.logger.warning(f'Network is not ready {self.name}. Trying again! {e}')
                time.sleep(10)

        self.logger.info(f'Got network. network_name: {self.name}, network_vlan: {network_vlan}')
        self.vlans.append(network_vlan)

        try:
            chameleon_subnet = chi.network.get_subnet(self.subnet_name)
            self.logger.info(f'Subnet already created: {self.subnet_name}')
        except Exception as e:
            self.logger.warning(f'Error while creating subnet: {self.subnet_name} {e}')
            chameleon_subnet = None

        if not chameleon_subnet:
            chameleon_subnet = chi.network.create_subnet(self.subnet_name, chameleon_network_id,
                                                         cidr=self.subnet,
                                                         allocation_pool_start=self.pool_start,
                                                         allocation_pool_end=self.pool_end,
                                                         gateway_ip=self.gateway)
            self.logger.info(f'Created subnet {self.subnet_name}')

        self.logger.debug(f'Subnet: {chameleon_subnet}')
        chameleon_router = None

        # we do not use get as it throws an exception if not found. So we list them
        for router in chi.network.list_routers():
            if router['name'] == self.router_name:
                chameleon_router = router
                break

        if chameleon_router:
            self.logger.info(f'Router already created: {self.router_name}')
            self.logger.debug(f'Router: {chameleon_router}')
        else:
            chameleon_router = chi.network.create_router(self.router_name, gw_network_name='public')
            self.logger.info(f'Router created: {self.router_name}')
            chi.network.add_subnet_to_router_by_name(self.router_name, self.subnet_name)
            self.logger.info(f'Attached subnet {self.subnet_name} to router  {self.router_name}')
            self.logger.debug(f'Router: {chameleon_router}')

    def delete(self):
        chi.set('project_name', self.project_name)
        chi.set('project_domain_name', 'default')
        chi.use_site(self.site)

        from neutronclient.common.exceptions import Conflict, NotFound
        from keystoneauth1.exceptions.connection import ConnectFailure
        import time

        while True:
            try:
                self.logger.debug(f"Removing subnet {self.subnet_name} from router {self.router_name}")
                subnet_id = chi.network.get_subnet_id(self.subnet_name)
                router_id = chi.network.get_router_id(self.router_name)
                chi.network.remove_subnet_from_router(router_id, subnet_id)
                self.logger.info(f"Removed subnet {self.subnet_name} from router {self.router_name}")
                break
            except (Conflict, ConnectFailure) as ce:
                self.logger.warning(f"Error Removing subnet .will try again ...{ce}")
                time.sleep(10)
            except NotFound as nf:
                self.logger.warning(f"Error Removing subnet ...{nf}")
                break
            except RuntimeError as re:
                if "No subnets found with" in str(re):
                    break

                raise re

        try:
            router_id = chi.network.get_router_id(self.router_name)
            chi.network.delete_router(router_id)
            self.logger.info(f"Deleted router  {self.router_name} net_id={router_id}")
        except RuntimeError as re:
            if "No routers found with" not in str(re):
                raise re

        try:
            subnet_id = chi.network.get_subnet_id(self.subnet_name)
            chi.network.delete_subnet(subnet_id)
            self.logger.info(f"Deleted subnet  {self.subnet_name} net_id={subnet_id}")
        except RuntimeError as re:
            if "No subnets found with" not in str(re):
                raise re

        try:
            net_id = chi.server.get_network_id(self.name)
            chi.network.delete_network(net_id)
            self.logger.info(f"Deleted network {self.name} net_id={net_id}")
        except RuntimeError as re:
            if "No networks found with" not in str(re):
                raise re

        self._lease_helper.delete_lease()
