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

from collections import namedtuple
from typing import List

from fabrictestbed_extensions.fablib.node import Node as Delegate
from fabrictestbed_extensions.fablib.slice import Slice

from fabfed.model import Node
from fabfed.util.config import Config

Component = namedtuple("Component", "model  name")


class FabricNode(Node):
    def __init__(self, *, delegate: Delegate):
        flavor = {'cores': delegate.get_cores(), 'ram': delegate.get_ram(), 'disk': delegate.get_disk()}
        super().__init__(name=delegate.get_name(), image=delegate.get_image(), site=delegate.get_site(),
                         flavor=str(flavor))

        self._delegate = delegate
        self._slice_object = delegate.get_slice()
        self.management_ip = str(delegate.get_management_ip())
        self._components: List[Component] = []

        for component in delegate.get_components():
            self._components.append(Component(name=component.get_name(), model=component.get_model()))

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


class NodeBuilder:
    def __init__(self, slice_object: Slice, name: str,  resource: dict):
        site = resource.get(Config.RES_SITE, Config.FABRIC_RANDOM)

        if site == Config.FABRIC_RANDOM:
            from fabrictestbed_extensions.fablib.fablib import fablib

            site = fablib.get_random_site()

        image = resource.get(Config.RES_IMAGE, Delegate.default_image)
        flavor = resource.get(Config.RES_FLAVOR, {'cores': 2, 'ram': 8, 'disk': 10})
        cores = flavor.get(Config.RES_FLAVOR_CORES, Delegate.default_cores)
        ram = flavor.get(Config.RES_FLAVOR_RAM, Delegate.default_ram)
        disk = flavor.get(Config.RES_FLAVOR_DISK, Delegate.default_disk)
        self.node: Delegate = slice_object.add_node(name=name, image=image, site=site, cores=cores, ram=ram, disk=disk)

    def add_component(self, model=None, name=None):
        self.node.add_component(model=model, name=name)

    def build(self) -> FabricNode:
        return FabricNode(delegate=self.node)
