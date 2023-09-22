from ipaddress import IPv4Address

from fabrictestbed_extensions.fablib.network_service import NetworkService
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Network
from fabfed.util.constants import Constants
from ...util.config_models import Config
from fabfed.exceptions import FabfedException
from .fabric_provider import FabricProvider
from fabfed.policy.policy_helper import get_stitch_port_for_provider

from fabfed.util.utils import get_logger

logger = get_logger()


class FabricNetwork(Network):
    def __init__(self, *, label, delegate: NetworkService, layer3: Config, peering: Config, peer_layer3):
        self.name = delegate.get_name()
        self.site = delegate.get_site()
        super().__init__(label=label, name=self.name, site=self.site)
        self._delegate = delegate
        self.site = delegate.get_site()
        self.slice_name = self._delegate.get_slice().get_name()
        self.type = str(delegate.get_type())

        self.layer3 = layer3
        self.peering = peering
        self.peer_layer3 = peer_layer3
        ns = self._delegate.get_fim_network_service()
        self.interface = []


        # TODO This is only needed for sense-aws and aws
        if self.peering and Constants.RES_CLOUD_ACCOUNT in self.peering.attributes:
            account_id = self.peering.attributes[Constants.RES_CLOUD_ACCOUNT]
            key = self.slice_name + "-" + account_id
            self.interface.append(dict(id=key, provider="fabric", password='0xzsEwC7xk6c1fK_h.xHyAdx'))

        for key, iface in ns.interfaces.items():
            if hasattr(iface.labels, "vlan") and iface.labels.vlan:
                self.interface.append(dict(id=key, vlan=iface.labels.vlan))

        self.id = self._delegate.get_reservation_id()
        self.state = self._delegate.get_reservation_state()

    @property
    def subnet(self):
        return self.layer3.attributes.get(Constants.RES_SUBNET) if self.layer3 else None

    @property
    def gateway(self):
        return self.layer3.attributes.get(Constants.RES_NET_GATEWAY) if self.layer3 else None

    def available_ips(self):
        available_ips = []

        if self.layer3:
            ip_start = self.layer3.attributes.get(Constants.RES_LAYER3_DHCP_START)
            ip_end = self.layer3.attributes.get(Constants.RES_LAYER3_DHCP_END)

            if ip_start and ip_end:
                pool_start = int(IPv4Address(ip_start))
                pool_end = int(IPv4Address(ip_end))

                for ip_int in range(pool_start + 1, pool_end + 1):
                    available_ips.append(IPv4Address(ip_int))

        return available_ips

    def get_reservation_id(self):
        self._delegate.get_reservation_id()

    def get_site(self):
        return self._delegate.get_site()


class NetworkBuilder:
    def __init__(self, label, provider: FabricProvider, slice_object: Slice, name, resource: dict):
        self.slice_object = slice_object
        self.stitch_info = resource.get(Constants.RES_STITCH_INFO)
        self.stitch_port = get_stitch_port_for_provider(resource=resource, provider=provider.type)
        self.vlan = None
        self.site = resource.get(Constants.RES_SITE)
        self.interfaces = []
        self.net_name = name
        self.layer3 = resource.get(Constants.RES_LAYER3)
        self.peering = resource.get(Constants.RES_PEERING)
        self.peer_layer3 = resource.get(Constants.RES_PEER_LAYER3)
        self.device = None
        self.stitching_net = None
        self.label = label
        self.net = None
        self.type = resource.get('net_type')     # TODO: type
        self.discovered_stitch_info = {}

        if self.stitch_port:
            self.device = self.stitch_port.get(Constants.STITCH_PORT_DEVICE_NAME)
            self.site = self.stitch_port.get(Constants.STITCH_PORT_SITE)

        import fabfed.provider.api.dependency_util as util

        if util.has_resolved_external_dependencies(resource=resource, attribute=Constants.RES_STITCH_INTERFACE):
            self.stitching_net = util.get_single_value_for_dependency(resource=resource,
                                                                      attribute=Constants.RES_STITCH_INTERFACE)

            if not isinstance(self.stitching_net, Network):
                raise FabfedException(f"Expecting Network. Got {type(self.stitching_net)}")

            self.check_stitch_net()

        if self.peering:
            from .plugins import Plugins
            import traceback
            try:
                Plugins.load()
            except Exception:
                traceback.print_exc()

        logger.info(
            f'{self.net_name}:vlan={self.vlan},stitch_port={self.stitch_port},device={self.device},site={self.site}')

    def check_stitch_net(self):
        assert self.stitching_net

        if hasattr(self.stitching_net, 'interface'):
            interface = self.stitching_net.interface

            if isinstance(interface, list):
                temp = [i for i in interface if isinstance(i, dict) and 'provider' in i]

                if temp:
                    interface = temp[0]

            if isinstance(interface, dict) and 'provider' in interface:
                logger.info(f'Network {self.net_name} found stitching interface {interface}')
                self.vlan = interface.get('vlan')
                self.discovered_stitch_info = interface

    def handle_facility_port(self):
        from fim.slivers.capacities_labels import Labels, Capacities

        if not self.vlan and not self.peering:
            logger.warning(f"Network {self.net_name} has no vlan and no peering so no facility port will be added ")
            return

        if self.peering:
            cloud = self.peering.attributes.get(Constants.RES_CLOUD_FACILITY)
            asn = self.peering.attributes.get(Constants.RES_REMOTE_ASN)
            account_id = self.peering.attributes.get(Constants.RES_CLOUD_ACCOUNT)

            if account_id is None:
                account_id = self.discovered_stitch_info.get("id")

            subnet = self.peering.attributes.get(Constants.RES_LOCAL_ADDRESS)
            peer_subnet = self.peering.attributes.get(Constants.RES_REMOTE_ADDRESS)
            region= self.peering.attributes.get(Constants.RES_CLOUD_REGION)
            device = self.peering.attributes.get(Constants.RES_LOCAL_DEVICE)
            port = self.peering.attributes.get(Constants.RES_LOCAL_PORT)
            vlan = self.peering.attributes.get('cloud_vlan')

            if not device:
                device = self.stitch_port.get(Constants.STITCH_PORT_DEVICE_NAME)

            if not port:
                port = self.stitch_port.get(Constants.STITCH_PORT_LOCAL_NAME)

            if not region:
                region = self.stitch_port.get(Constants.STITCH_PORT_REGION)

            if not cloud:
                cloud = self.stitch_port.get(Constants.STITCH_PORT_SITE)
                self.peering.attributes[Constants.RES_CLOUD_FACILITY] = cloud # TODO WORKAROUND FOR NOW

            if not vlan:
                vlan = self.stitch_port.get('vlan')   # TODO WORKAROUND GCP NEEDS THIS

            labels = Labels(ipv4_subnet=subnet)

            if vlan:
                labels = Labels.update(labels, vlan=str(vlan))

            # if region:
            #     labels = Labels.update(labels, region=region)

            if device: 
                labels = Labels.update(labels, device_name=device)
            if port: 
                labels = Labels.update(labels, local_name=port)

            peer_labels = Labels(ipv4_subnet=peer_subnet,
                                 asn=str(asn),
                                 bgp_key='0xzsEwC7xk6c1fK_h.xHyAdx',
                                 account_id=account_id)

            logger.info(f"Creating Facility Port:Labels: {labels}")
            logger.info(f"Creating Facility Port:PeerLabels: {peer_labels}")

            facility_port = self.slice_object.add_facility_port(
                name='Cloud-Facility-' + cloud,
                site=cloud,
                labels=labels,
                peer_labels=peer_labels,
                capacities=Capacities(bw=1, mtu=9001))

            logger.info("CreatedFacilityPort:" + facility_port.toJson())
        else:
            logger.info(f"Creating Facility Port: name={self.device}:site={self.site}:vlan={self.vlan}")

            facility_port = self.slice_object.add_facility_port(name=self.device,
                                                                site=self.site,
                                                                vlan=str(self.vlan))
            logger.info(f"Created Facility Port: name={self.device}:site={self.site}:vlan={self.vlan}")

        facility_port_interface = facility_port.get_interfaces()[0]
        self.interfaces.append(facility_port_interface)

    def handle_network(self, nodes):
        from fim.slivers.capacities_labels import Labels, Capacities

        if not self.peering:
            interfaces = [self.interfaces[0]]

            for node in nodes:
                node_interfaces = [i for i in node.get_interfaces() if not i.get_network()]

                if node_interfaces:
                    logger.info(f"Node {node.name} has interface for stitching NAME={node_interfaces[0].get_name()} ")
                    interfaces.append(node_interfaces[0])
                else:
                    logger.warning(f"Node {node.name} has no available interface to stitch to network {self.net_name} ")

            # Use type='L2STS'?
            logger.info(f"Creating Layer2 Network:{self.net_name}:interfaces={[i.get_name() for i in interfaces]}")
            self.net: NetworkService = self.slice_object.add_l2network(name=self.net_name, interfaces=interfaces)
            return

        tech = 'AL2S'
        net_type = 'L3VPN'
        port_name= self.interfaces[0].get_name()

        logger.info(f"Creating Network:{self.net_name}:FacilityPort:{port_name},type={net_type}:techonolgy={tech}")

        self.net = self.slice_object.add_l3network(name=self.net_name,
                                                   interfaces=self.interfaces, type=net_type,
                                                   technology=tech)
        interfaces = []

        for node in nodes:
            node_interfaces = [i for i in node.get_interfaces() if not i.get_network()]

            if node_interfaces:
                logger.info(f"Node {node.name} has interface for stitching NAME={node_interfaces[0].get_name()} ")
                interfaces.append(node_interfaces[0])
            else:
                logger.warning(f"Node {node.name} has no available interface to stitch to network {self.net_name} ")

        # TODO DO WE NEED REALLY THIS?
        for iface in interfaces:
            fim_iface1 = iface.get_fim_interface()

            if self.layer3:
                ipv4_gateway = self.layer3.attributes.get(Constants.RES_NET_GATEWAY)
                if ipv4_gateway:
                    ipv4_subnet = self.layer3.attributes.get(Constants.RES_SUBNET)
                    if ipv4_subnet and '/' in ipv4_subnet:
                        ipv4_netmask = ipv4_subnet.split('/')[1]
                        ipv4_subnet = f'{ipv4_gateway}/{ipv4_netmask}'
                else:
                    ipv4_subnet = self.layer3.attributes.get(Constants.RES_SUBNET)
                fim_iface1.labels = Labels.update(fim_iface1.labels, ipv4_subnet=f'{ipv4_subnet}')

        aux_name = self.net_name + "_aux"
        aux_net = self.slice_object.add_l3network(name=aux_name, interfaces=interfaces, type='L3VPN')

        # bw must be set to 0 and mtu 9001 for Peered Interfaces
        self.net.fim_network_service.peer(
            aux_net.fim_network_service,
            labels=Labels(bgp_key='secret', ipv4_subnet='192.168.50.1/24'),
            capacities=Capacities(mtu=9001))

    def build(self) -> FabricNetwork:
        assert self.net
        return FabricNetwork(label=self.label, delegate=self.net, layer3=self.layer3,
                             peering=self.peering, peer_layer3=self.peer_layer3)
