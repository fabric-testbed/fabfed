from fabrictestbed_extensions.fablib.node import Node as Delegate
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Node
from fabfed.util.constants import Constants
from fabfed.util.utils import get_logger
from .fabric_constants import *

logger = get_logger()


class FabricNode(Node):
    def __init__(self, *, label, delegate: Delegate, nic_model: str, network_label: str):
        flavor = {'cores': delegate.get_cores(), 'ram': delegate.get_ram(), 'disk': delegate.get_disk()}
        super().__init__(label=label, name=delegate.get_name(), image=delegate.get_image(), site=delegate.get_site(),
                         flavor=str(flavor))
        logger.info(f" Node {self.name} construtor called ... ")
        self._delegate = delegate
        self.nic_model = nic_model
        self._slice_object = delegate.get_slice()
        self.slice_name = self._slice_object.get_name()
        self.mgmt_ip = delegate.get_management_ip()
        self.mgmt_ip = str(self.mgmt_ip) if self.mgmt_ip else None
        self.network_label = network_label
        self.username = delegate.get_username()
        self.user = self.username
        self.state = delegate.get_reservation_state()
        self.state = self.state.lower() if self.state else None
        self.host = self.mgmt_ip
        self.keyfile = self._delegate.get_private_key_file()
        self.jump_user = self._delegate.get_fablib_manager().get_bastion_username()
        self.jump_host = self._delegate.get_fablib_manager().get_bastion_host()
        self.jump_keyfile = self._delegate.get_fablib_manager().get_bastion_key_location()
        self._used_dataplane_ipv4 = None
        self.dataplane_ipv4 = None
        self.dataplane_ipv6 = None
        self.id = delegate.get_reservation_id()
        self.components = [dict(name=c.get_name(), model=c.get_model()) for c in delegate.get_components()]
        self.addr_list = {}

    def handle_networking(self):
        slice_object = self._slice_object

        if not self.mgmt_ip:
            logger.warning(f" Node {self.name} has no management ip ")
            return

        v6_dev = v4_dev = stitch_dev = None

        try:
            # XXX Finding interfaces on stitched networks is currently not working on fablib==1.4.0
            # Search for interface directly...
            stitch_iface = slice_object.get_interface(name=f"{self.name}-{FABRIC_STITCH_NET_IFACE_NAME}-p1")
            stitch_dev = stitch_iface.get_device_name()
            logger.info(f" Node {self.name} has stitch device={stitch_dev}")
        except Exception as e:
            logger.warning(f" Node {self.name} checking for stitch network/device: {e}")

        try:
            if stitch_dev is None and INCLUDE_FABNET_V4:
                for itf in slice_object.get_interfaces():
                    if self.v4net_name in itf.get_name():
                        v4_dev = itf.get_device_name()
                        logger.info(f" Node {self.name} has v4 device={v4_dev}")
                        break
        except Exception as e:
            logger.warning(f"Node {self.name} checking for ipv4/ipv6: {e}")

        try:
            if stitch_dev is None and INCLUDE_FABNET_V6:
                for itf in slice_object.get_interfaces():
                    if self.v6net_name in itf.get_name():
                        v6_dev = itf.get_device_name()
                        logger.info(f" Node {self.name} has v6 device={v6_dev}")
                        break
        except Exception as e:
            logger.warning(f"Node {self.name} checking for ipv4/ipv6: {e}")

        try:
            if stitch_dev and INCLUDE_FABNETS:
                v4_net = slice_object.get_network(name=self.v4net_name)
                v4_dev = v4_net.get_interfaces()[0].get_device_name() if v4_net and v4_net.get_interfaces() else None
                logger.info(f" Node {self.name} has v4 device={v4_dev}")

                v6_net = slice_object.get_network(name=self.v6net_name)
                v6_dev = v6_net.get_interfaces()[0].get_device_name() if v6_net and v6_net.get_interfaces() else None
                logger.info(f" Node {self.name} has v6 device={v6_dev}")
        except Exception as e:
            logger.warning(f"Node {self.name} checking for ipv4/ipv6: {e}")

        try:
            for ip_addr in self._delegate.ip_addr_list(output='json', update=False):
                ifname = ip_addr['ifname']
                self.addr_list[ifname] = []

                for addr_info in ip_addr['addr_info']:
                    self.addr_list[ifname].append(addr_info['local'])
                    if stitch_dev:
                        if stitch_dev == ifname and addr_info['family'] == 'inet':
                            self.dataplane_ipv4 = addr_info['local']

                        if stitch_dev == ifname and addr_info['family'] == 'inet6':
                            self.dataplane_ipv6 = addr_info['local']
                    else:
                        if v4_dev == ifname and addr_info['family'] == 'inet':
                            self.dataplane_ipv4 = addr_info['local']

                        if v6_dev == ifname and addr_info['family'] == 'inet6':
                            self.dataplane_ipv6 = addr_info['local']
        except Exception as e:
            logger.warning(f"Node {self.name} checking for dataplane address: {e}")

    @property
    def delegate(self) -> Delegate:
        return self._delegate

    @property
    def v4net_name(self):
        if INCLUDE_FABNET_V4:
            return f"FABNET_IPv4_{self.site}"

        return f"{self.name}-{FABRIC_IPV4_NET_NAME}"

    @property
    def v6net_name(self):
        if INCLUDE_FABNET_V6:
            return f"FABNET_IPv6_{self.site}"

        return f"{self.name}-{FABRIC_IPV6_NET_NAME}"

    def set_network_label(self, network_label):
        self.network_label = network_label

    def used_dataplane_ipv4(self):
        return self._used_dataplane_ipv4

    def set_used_dataplane_ipv4(self, used_dataplane_ipv4):
        self._used_dataplane_ipv4 = used_dataplane_ipv4

    def get_interfaces(self):
        return self._delegate.get_interfaces()

    def get_interface(self, *, network_name):
        assert network_name
        return self._delegate.get_interface(network_name=network_name)

    def upload_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self._delegate.upload_file(local_file_path, remote_file_path, retry, retry_interval)

    def download_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self._delegate.download_file(local_file_path, remote_file_path, retry, retry_interval)

    def upload_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        self._delegate.upload_directory(local_directory_path, remote_directory_path, retry, retry_interval)

    def download_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        self._delegate.download_directory(local_directory_path, remote_directory_path, retry, retry_interval)

    def execute(self, command, retry=3, retry_interval=10):
        self._delegate.execute(command, retry, retry_interval)

    def add_route(self, subnet, gateway):
        self._delegate.ip_route_add(subnet=subnet, gateway=gateway)

    def get_management_ip(self) -> str:
        return self._delegate.get_management_ip()

    def get_dataplane_address(self, network=None, interface=None, af=Constants.IPv4):
        if af == Constants.IPv4:
            return self.dataplane_ipv4
        elif af == Constants.IPv6:
            return self.dataplane_ipv6
        else:
            return None

    def get_reservation_id(self) -> str:
        return self._delegate.get_reservation_id()

    def get_reservation_state(self) -> str:
        return self._delegate.get_reservation_state()


class NodeBuilder:
    def __init__(self, label, slice_object: Slice, name: str,  resource: dict):
        from .fabric_constants import FABRIC_RANDOM
        site = resource.get(Constants.RES_SITE, FABRIC_RANDOM)

        if site == FABRIC_RANDOM:
            from fabrictestbed_extensions.fablib.fablib import fablib

            site = fablib.get_random_site()

        image = resource.get(Constants.RES_IMAGE, Delegate.default_image)
        flavor = resource.get(Constants.RES_FLAVOR, {'cores': 2, 'ram': 8, 'disk': 10})
        cores = flavor.get(Constants.RES_FLAVOR_CORES, Delegate.default_cores)
        ram = flavor.get(Constants.RES_FLAVOR_RAM, Delegate.default_ram)
        disk = flavor.get(Constants.RES_FLAVOR_DISK, Delegate.default_disk)
        self.label = label
        self.nic_model = resource.get(Constants.RES_NIC_MODEL, 'NIC_Basic')
        self.node: Delegate = slice_object.add_node(name=name, image=image, site=site, cores=cores, ram=ram, disk=disk)

        # Use fully automated ip v4
        if INCLUDE_FABNET_V4 and resource.get(Constants.RES_TYPE_NETWORK) is None:
            self.node.add_fabnet(net_type="IPv4", nic_type=self.nic_model)

        # Use fully automated ip v6
        if INCLUDE_FABNET_V6 and resource.get(Constants.RES_TYPE_NETWORK) is None:
            self.node.add_fabnet(net_type="IPv6", nic_type=self.nic_model)

        # This has been deprecated Include two basic NICs for FabNetv4/v6
        if INCLUDE_FABNETS and resource.get(Constants.RES_TYPE_NETWORK) is None:
            net_iface_v4 = self.node.add_component(model='NIC_Basic',
                                                   name=FABRIC_IPV4_NET_IFACE_NAME).get_interfaces()[0]
            # TODO: KOMAL:
            net_iface_v4.set_mode("auto")
            net_iface_v6 = self.node.add_component(model='NIC_Basic',
                                                   name=FABRIC_IPV6_NET_IFACE_NAME).get_interfaces()[0]
            # TODO: KOMAL
            net_iface_v6.set_mode("auto")
            slice_object.add_l3network(name=f"{name}-{FABRIC_IPV4_NET_NAME}", interfaces=[net_iface_v4], type='IPv4')
            slice_object.add_l3network(name=f"{name}-{FABRIC_IPV6_NET_NAME}", interfaces=[net_iface_v6], type='IPv6')

    def add_component(self, model=None, name=None):
        self.node.add_component(model=model, name=name)

    def build(self) -> FabricNode:
        return FabricNode(label=self.label, delegate=self.node, nic_model=self.nic_model, network_label="")
