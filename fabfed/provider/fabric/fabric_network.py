from ipaddress import IPv4Address

from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Network
from fabfed.util.constants import Constants
from ...util.parser import Config


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
        self.pool_start = layer3.attributes.get(Constants.RES_LAYER3_DHCP_START)
        self.pool_end = layer3.attributes.get(Constants.RES_LAYER3_DHCP_END)

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
        self.vlan = resource.get('vlan')  # facility port vlan

        import fabfed.provider.api.dependency_util as util

        if util.has_resolved_external_dependencies(resource=resource, attribute='vlan'):
            net = util.get_single_value_for_dependency(resource=resource, attribute='vlan')
            self.vlan = net.vlans[0]

        self.interfaces = []
        self.net_name = name  # f'net_facility_port'

        # TODO AES_MERGE: CLEAN UP:
        # if self.vlan:
        #     from ipaddress import IPv4Address, IPv4Network
        #     self.subnet = IPv4Network(resource.get(Constants.RES_SUBNET))
        #     self.pool_start = IPv4Address(resource.get(Constants.RES_NET_POOL_START))
        #     self.pool_end = IPv4Address(resource.get(Constants.RES_NET_POOL_END))
        #     self.facility_port = 'Chameleon-StarLight'
        #     self.facility_port_site = resource.get(Constants.RES_SITE)
        # else:
        #     self.subnet = None
        #     self.pool_start = None
        #     self.pool_end = None

        self.layer3 = resource.get(Constants.RES_LAYER3)
        self.label = label
        self.net = None

    def handle_facility_port(self):
        if not self.vlan:
            return
        facility_port = self.slice_object.add_facility_port(name=self.facility_port, site=self.facility_port_site,
                                                            vlan=str(self.vlan))
        facility_port_interface = facility_port.get_interfaces()[0]
        self.interfaces.append(facility_port_interface)

    def handle_l2network(self, interfaces):
        assert len(interfaces) > 0
        # assert len(self.interfaces) == 1
        if not self.vlan:
            return
        self.interfaces.extend(interfaces)
        self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name, interfaces=self.interfaces)

    def handle_l3network(self, interfaces):
        assert len(interfaces) > 0
        # assert len(self.interfaces) == 1
        self.interfaces.extend(interfaces)
        self.net: NetworkService = self.slice_object.add_l3network(name=self.net_name, interfaces=self.interfaces)

    def build(self) -> FabricNetwork:
        assert self.net
        assert self.layer3

        return FabricNetwork(label=self.label, delegate=self.net, layer3=self.layer3)
