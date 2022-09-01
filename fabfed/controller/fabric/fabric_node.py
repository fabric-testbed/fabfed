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

from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.slice import Slice

from mobius.controller.util.config import Config
from mobius.models import AbstractNode

Component = namedtuple("Component", "model  name")


class FabricNode(AbstractNode):
    def __init__(self, *, delegate: Node):
        self.delegate = delegate
        self.slice_object = delegate.get_slice()
        self.name = delegate.get_name()
        self.image = delegate.get_image()
        self.site = delegate.get_site()
        self.flavor = {'cores': delegate.get_cores(), 'ram':  delegate.get_ram(), 'disk': delegate.get_disk()}
        self.management_ip = delegate.get_management_ip()
        self.components: List[Component] = []

        for component in delegate.get_components():
            self.components.append(Component(name=component.get_name(), model=component.get_model()))

    def get_interfaces(self):
        return self.delegate.get_interfaces()

    def get_interface(self, *, network_name):
        return self.delegate.get_interface(network_name=network_name)

    def upload_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self.delegate.upload_file(local_file_path, remote_file_path, retry, retry_interval)

    def download_file(self, local_file_path, remote_file_path, retry=3, retry_interval=10):
        self.delegate.download_file(local_file_path, remote_file_path, retry, retry_interval)

    def upload_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        self.delegate.upload_directory(local_directory_path, remote_directory_path, retry, retry_interval)

    def download_directory(self, local_directory_path, remote_directory_path, retry=3, retry_interval=10):
        self.delegate.download_directory(local_directory_path, remote_directory_path, retry, retry_interval)

    def execute(self, command, retry=3, retry_interval=10):
        self.delegate.execute(command, retry, retry_interval)

    def get_name(self) -> str:
        return self.name

    def get_site(self) -> str:
        return self.site

    def get_flavor(self) -> dict:
        return self.flavor

    def get_image(self) -> str:
        return self.image

    def get_management_ip(self) -> str:
        return self.delegate.get_management_ip()

    def get_reservation_id(self):
        return self.delegate.get_reservation_id()

    def get_reservation_state(self):
        return self.delegate.get_reservation_state()


class NodeBuilder:
    def __init__(self, slice_object: Slice, name: str,  resource: dict):
        site = resource.get(Config.RES_SITE, Config.FABRIC_RANDOM)

        if site == Config.FABRIC_RANDOM:
            from fabrictestbed_extensions.fablib.fablib import fablib

            site = fablib.get_random_site()

        image = resource.get(Config.RES_IMAGE, Node.default_image)
        flavor = resource.get(Config.RES_FLAVOR, {'cores': 2, 'ram': 8, 'disk': 10})
        cores = flavor.get(Config.RES_FLAVOR_CORES, Node.default_cores)
        ram = flavor.get(Config.RES_FLAVOR_RAM, Node.default_ram)
        disk = flavor.get(Config.RES_FLAVOR_DISK, Node.default_disk)
        self.node: Node = slice_object.add_node(name=name, image=image, site=site, cores=cores, ram=ram, disk=disk)

    def add_component(self, model=None, name=None):
        self.node.add_component(model=model, name=name)

    def build(self) -> FabricNode:
        return FabricNode(delegate=self.node)
