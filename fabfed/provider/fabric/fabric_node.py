from typing import List, Dict

from fabrictestbed_extensions.fablib.node import Node as Delegate
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Node
from fabfed.util.constants import Constants
from .fabric_constants import *


class FabricNode(Node):
    def __init__(self, *, label, delegate: Delegate):
        flavor = {'cores': delegate.get_cores(), 'ram': delegate.get_ram(), 'disk': delegate.get_disk()}
        super().__init__(label=label, name=delegate.get_name(), image=delegate.get_image(), site=delegate.get_site(),
                         flavor=str(flavor))

        self._delegate = delegate
        self.slice_name = delegate.get_slice().get_name()
        self.mgmt_ip = delegate.get_management_ip()

        if self.mgmt_ip:
            self.mgmt_ip = str(self.mgmt_ip)

        self.username = delegate.get_username()
        self.state = delegate.get_reservation_state()
        self.user = self.username
        self.host = self.mgmt_ip
        self.keyfile = self._delegate.get_private_key_file()
        self.jump_user = self._delegate.get_fablib_manager().get_bastion_username()
        self.jump_host = self._delegate.get_fablib_manager().get_bastion_public_addr()
        self.jump_keyfile = self._delegate.get_fablib_manager().get_bastion_key_filename()
        self.dataplane_ipv4 = self._delegate.get_slice().get_network(name=self.v4net_name).get_available_ips()
        self.dataplane_ipv6 = self._delegate.get_slice().get_network(name=self.v6net_name).get_available_ips()
        if self.dataplane_ipv4:
            self.dataplane_ipv4 = str(self.dataplane_ipv4.pop(0))
        if self.dataplane_ipv6:
            self.dataplane_ipv6 = str(self.dataplane_ipv6.pop(0))

        if self.state:
            self.state = self.state.lower()

        self.id = delegate.get_reservation_id()

        self.addr_list = []

        if delegate.get_management_ip():
            try:
                for ip_addr in self._delegate.ip_addr_list(output='json', update=False):
                    ifname = ip_addr['ifname']

                    for addr_info in ip_addr['addr_info']:
                        self.addr_list.append(dict(ifname=ifname, addr_info=addr_info['local']))
            except:
                pass # TODO LOG IT

        self.components: List[Dict[str, str]] = []

        for component in delegate.get_components():
            self.components.append(dict(name=component.get_name(), model=component.get_model()))

    @property
    def v4net_name(self):
        return f"{self.name}-{FABRIC_IPV4_NET_NAME}"

    @property
    def v6net_name(self):
        return f"{self.name}-{FABRIC_IPV6_NET_NAME}"

    def get_interfaces(self):
        return self._delegate.get_interfaces()

    def get_interface(self, *, network_name):
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
        self.node: Delegate = slice_object.add_node(name=name, image=image, site=site, cores=cores, ram=ram, disk=disk)
        # Fabfed will always include two basic NICs for FabNetv4/v6
        net_iface_v4 = self.node.add_component(model='NIC_Basic', name=FABRIC_IPV4_NET_IFACE_NAME).get_interfaces()[0]
        net_iface_v6 = self.node.add_component(model='NIC_Basic', name=FABRIC_IPV6_NET_IFACE_NAME).get_interfaces()[0]
        slice_object.add_l3network(name=f"{name}-{FABRIC_IPV4_NET_NAME}", interfaces=[net_iface_v4], type='IPv4')
        slice_object.add_l3network(name=f"{name}-{FABRIC_IPV6_NET_NAME}", interfaces=[net_iface_v6], type='IPv6')

    def add_component(self, model=None, name=None):
        self.node.add_component(model=model, name=name)

    def build(self) -> FabricNode:
        return FabricNode(label=self.label, delegate=self.node)
