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


class NetworkBuilder:
    def __init__(self, label, slice_object: Slice, name, resource: dict):
        self.slice_object = slice_object
        self.vlan = None # facility port vlan
        self.facility_port = 'Chameleon-StarLight'

        prop = 'stitch_interface'

        if isinstance(resource.get(prop), dict):   # This is just to simplify testing ....
            self.vlan = resource.get(prop)
            self.vlan = self.vlan['vlan']
            if resource.get(prop).get("provider", None) == 'sense':
                self.facility_port = 'UKY-AL2S'

        if not self.vlan:
            import fabfed.provider.api.dependency_util as util

            # TDO MODIFY Chameleon
            # if util.has_resolved_external_dependencies(resource=resource, attribute=prop):
            #     net = util.get_single_value_for_dependency(resource=resource, attribute=prop)
            #     self.vlan = net.vlans[0]

            if util.has_resolved_external_dependencies(resource=resource, attribute=prop):
                net = util.get_single_value_for_dependency(resource=resource, attribute=prop)

                if isinstance(net, Network):
                    net = net.interface

                if isinstance(net, list):
                    net = net[0]

                if isinstance(net, dict):
                    self.vlan = net['vlan']

                    if net.get("provider", None) == 'sense':
                        self.facility_port = 'UKY-AL2S'

        if isinstance(self.vlan, list):
            self.vlan = self.vlan[0]

        self.interfaces = []
        self.net_name = name  # f'net_facility_port'
        # self.facility_port = 'UKY-AL2S' # 'Chameleon-StarLight' # TODO Use configuration file .... Or Even allow user to provide this ???
        self.facility_port_site = resource.get(Constants.RES_SITE)
        self.layer3 = resource.get(Constants.RES_LAYER3)
        self.label = label
        self.net = None
        self.type = resource.get('net_type')

        if self.vlan:
            logger.info(
                f"Network {self.net_name}: Got vlan={self.vlan},facility_port={self.facility_port},site={self.facility_port_site}")
        else:
            logger.warning(f"Network {self.net_name} has no vlan ...")

    def handle_facility_port(self):
        if not self.vlan:
            logger.warning(f"Network {self.net_name} has no vlan so no facility port will be added ")
            return

        # self.vlan = 3307
        facility_port = self.slice_object.add_facility_port(name=self.facility_port, site=self.facility_port_site,
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

        # type = 'L2STS' ????
        # logger.info(f"Adding Network {self.net_name} using type={self.type}")
        self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name,
                                                                   interfaces=interfaces, type='L2STS')

    def build(self) -> FabricNetwork:
        assert self.net
        assert self.layer3
        return FabricNetwork(label=self.label, delegate=self.net, layer3=self.layer3)
