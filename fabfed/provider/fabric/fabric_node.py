from typing import List, Dict

from fabrictestbed_extensions.fablib.node import Node as Delegate
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Node, SSHInfo
from fabfed.util.constants import Constants


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

        if self.state:
            self.state = self.state.lower()

        self.id = delegate.get_reservation_id()

        self.addr_list = []

        if delegate.get_management_ip():
            for ip_addr in self._delegate.ip_addr_list(output='json', update=False):
                ifname = ip_addr['ifname']

                for addr_info in ip_addr['addr_info']:
                    self.addr_list.append(dict(ifname=ifname, addr_info=addr_info['local']))

        self.components: List[Dict[str, str]] = []

        for component in delegate.get_components():
            self.components.append(dict(name=component.get_name(), model=component.get_model()))

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

    def get_management_ip(self) -> str:
        return self._delegate.get_management_ip()

    def get_reservation_id(self) -> str:
        return self._delegate.get_reservation_id()

    def get_reservation_state(self) -> str:
        return self._delegate.get_reservation_state()

    def get_ssh_info(self) -> (str, str, str):
        return SSHInfo(self.username, self.mgmt_ip,
                       self._delegate.get_private_key_file(),
                       self._delegate.get_fablib_manager().get_bastion_username(),
                       self._delegate.get_fablib_manager().get_bastion_public_addr())

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

    def add_component(self, model=None, name=None):
        self.node.add_component(model=model, name=name)

    def build(self) -> FabricNode:
        return FabricNode(label=self.label, delegate=self.node)
