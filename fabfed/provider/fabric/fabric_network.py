from ipaddress import IPv4Address

from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Network
from fabfed.util.constants import Constants
from ...util.parser import Config

from fabfed.util.utils import get_logger

logger = get_logger()


class FabricNetwork(Network):
    def __init__(self, *, label, delegate: NetworkService, layer3: Config):
        self.name = delegate.get_name()
        self.site = delegate.get_site()
        super().__init__(label=label, name=self.name, site=self.site)
        self._delegate = delegate
        self.site = delegate.get_site()
        self.slice_name = self._delegate.get_slice().get_name()
        self.type = str(delegate.get_type())
        self.layer3 = layer3
        self.subnet = layer3.attributes.get(Constants.RES_SUBNET)
        self.ip_start = layer3.attributes.get(Constants.RES_LAYER3_DHCP_START)
        self.ip_end = layer3.attributes.get(Constants.RES_LAYER3_DHCP_END)
        ns = self._delegate.get_fim_network_service()
        self.interface = []

        for key, iface in ns.interfaces.items():
            if hasattr(iface.labels, "vlan") and iface.labels.vlan:
                self.interface.append(dict(id=key, vlan=iface.labels.vlan))

        self.id = self._delegate.get_reservation_id()
        self.state = self._delegate.get_reservation_state()

    def available_ips(self):
        available_ips = []

        pool_start = int(IPv4Address(self.ip_start))
        pool_end = int(IPv4Address(self.ip_end))

        for ip_int in range(pool_start + 1, pool_end + 1):
            available_ips.append(IPv4Address(ip_int))

        return available_ips

    def get_reservation_id(self):
        self._delegate.get_reservation_id()

    def get_site(self):
        return self._delegate.get_site()


class FabricUtil:
    @staticmethod
    def get_facility_ports():
        import os
        import json

        port_file = os.path.join(os.path.dirname(__file__), 'inventory', "facility_ports.json")
        with open(port_file, 'r') as fp:
            ports = json.load(fp)
        return ports


class NetworkBuilder:
    def __init__(self, label, slice_object: Slice, name, resource: dict):
        self.slice_object = slice_object
        self.vlan = None  # facility port vlan
        self.site = resource.get(Constants.RES_SITE)  # facility port site

        ports = FabricUtil.get_facility_ports()
        prop = 'stitch_interface'

        if not self.vlan:
            import fabfed.provider.api.dependency_util as util
            from fabfed.exceptions import FabfedException

            if util.has_resolved_external_dependencies(resource=resource, attribute=prop):
                net = util.get_single_value_for_dependency(resource=resource, attribute=prop)

                if isinstance(net, Network):
                    net = net.interface

                if isinstance(net, list):
                    net = net[0]

                if isinstance(net, dict):
                    self.vlan = net['vlan']
                    provider = net['provider']

                    if provider not in ports or not ports[provider]:
                        raise FabfedException(f"no facility ports for provider {provider}:available_ports={ports}")

                    provider_ports = ports[provider]

                    if self.site not in provider_ports:
                        port_tuple = list(provider_ports.items())[0]
                        self.site = port_tuple[0]
                        self.facility_port = port_tuple[1]['name']
                    else:
                        self.facility_port = provider_ports[self.site]['name']

        if isinstance(self.vlan, list):
            self.vlan = self.vlan[0]

        self.interfaces = []
        self.net_name = name
        self.layer3 = resource.get(Constants.RES_LAYER3)
        self.label = label
        self.net = None
        self.type = resource.get('net_type')

        if self.vlan:
            logger.info(
                f'Network {self.net_name}:Got vlan={self.vlan},facility_port={self.facility_port},site={self.site}')
        else:
            logger.warning(f"Network {self.net_name} has no vlan ...")

    def handle_facility_port(self):
        if not self.vlan:
            logger.warning(f"Network {self.net_name} has no vlan so no facility port will be added ")
            return

        facility_port = self.slice_object.add_facility_port(name=self.facility_port,
                                                            site=self.site,
                                                            vlan=str(self.vlan))
        facility_port_interface = facility_port.get_interfaces()[0]
        self.interfaces.append(facility_port_interface)

    def handle_l2network(self, nodes):
        interfaces = [self.interfaces[0]]

        for node in nodes:
            node_interfaces = [i for i in node.get_interfaces() if not i.get_network()]

            if node_interfaces:
                logger.info(f"Node {node.name} has interface for stitching {node_interfaces[0].get_name()} ")
                interfaces.append(node_interfaces[0])
            else:
                logger.warning(f"Node {node.name} has no available interface to stitch to network {self.net_name} ")

        # self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name,
        #                                                            interfaces=interfaces, type='L2STS')
        self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name, interfaces=interfaces)

    def build(self) -> FabricNetwork:
        assert self.net
        assert self.layer3
        return FabricNetwork(label=self.label, delegate=self.net, layer3=self.layer3)
