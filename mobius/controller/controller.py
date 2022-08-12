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
import logging
import traceback
from logging.handlers import RotatingFileHandler

from mobius.controller.chi.chi_client import ChiClient
from mobius.controller.util.config import Config
import sys


class Controller:
    def __init__(self, *, config_file_location: str):
        self.config = Config(path=config_file_location)
        log_config = self.config.get_log_config()
        self.logger = logging.getLogger(str(log_config.get(Config.PROPERTY_CONF_LOGGER, __name__)))
        log_level = log_config.get(Config.PROPERTY_CONF_LOG_LEVEL, logging.INFO)

        self.logger.setLevel(log_level)
        file_handler = RotatingFileHandler(log_config.get(Config.PROPERTY_CONF_LOG_FILE),
                                           backupCount=int(log_config.get(Config.PROPERTY_CONF_LOG_RETAIN)),
                                           maxBytes=int(log_config.get(Config.PROPERTY_CONF_LOG_SIZE)))
        logging.basicConfig(level=log_level,
                            format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
                            handlers=[logging.StreamHandler(), file_handler], force=True)

        self.fabric_client = None
        self.chi_client = None

        fabric_config = self.config.get_fabric_config()
        if fabric_config is not None:
            from mobius.controller.fabric.fabric_client import FabricClient

            self.fabric_client = FabricClient(logger=self.logger, fabric_config=fabric_config)
            self.fabric_client.setup_environment()

        chi_config = self.config.get_chi_config()
        if chi_config is not None:
            self.chi_client = ChiClient(logger=self.logger, chi_config=chi_config)

    def simple_create(self):
        try:
            self.logger.debug("Starting create")
            resources = self.config.get_resource_config()
            for resource in resources:
                slice_config = resource.slice
                provider = slice_config.provider.type

                if provider == "fabric":
                    client = self.fabric_client
                elif provider == 'chi':
                    client = self.chi_client
                else:
                    self.logger.warning(f"Unknown provider type {provider}")
                    continue

                slice_name = slice_config.name
                resource_dict = resource.attributes
                resource_dict['resource_type'] = resource.type  # TODO pass along resource type/name differently
                resource_dict['resource_name'] = resource.name

                if resource.has_dependencies():
                    resource_dict['has_dependencies'] = True
                    resource_dict['dependencies'] = resource.dependencies
                else:
                    resource_dict['has_dependencies'] = False

                if resource.is_node:
                    client.add_resources(resource=resource_dict, slice_name=slice_name)
                elif resource.is_network:
                    client.add_resources(resource=resource_dict, slice_name=slice_name)

            client.create_resources(slice_name=slice_name, rtype=None)
        except Exception as e:
            self.logger.error(f"Exception occurred while creating resources: {e}")
            self.logger.error(traceback.format_exc())

    def create(self, *, connected: str = None):
        if True:
            return self.simple_create()

        try:
            self.logger.debug("Starting create")
            resources = self.config.get_resource_config()
            active = dict()
            for resource in resources:
                slice_config = resource.slice
                provider = slice_config.provider.type

                if provider == "fabric":
                    client = self.fabric_client
                elif provider == 'chi':
                    client = self.chi_client
                else:
                    self.logger.warning(f"Unknown provider type {provider}")
                    continue

                slice_name = slice_config.name
                resource_dict = resource.attributes
                key = f"{slice_name}-{resource.name}"  # TODO key may not be unique
                resource_dict['resource_type'] = resource.type  # TODO pass along resource type/name differently
                resource_dict['resource_name'] = resource.name

                if resource.has_dependencies():
                    resource_dict['has_dependencies'] = True
                    resource_dict['dependencies'] = resource.dependencies
                else:
                    resource_dict['has_dependencies'] = False

                if resource.is_node:
                    # TODO  make these dicts classes
                    active.update({key: {"client": client,
                                         "type": Config.RES_TYPE_NODE,
                                         "slice_name":  slice_name,
                                         "priority": 100,
                                         "resource": client.add_resources(resource=resource_dict,
                                                                          slice_name=slice_name)}})
                elif resource.is_network:
                    print("JJJJJ", resource, resource.attributes, file=sys.stderr)
                    net_priority = 20 if ("vlan" in resource_dict and not resource_dict.get(
                        "vlan")) and connected else 10
                    active.update({key: {"client": client,
                                         "type": Config.RES_TYPE_NETWORK,
                                         "slice_name": slice_name,
                                         "priority": net_priority,
                                         "resource": client.add_resources(resource=resource_dict,
                                                                          slice_name=slice_name)}})

            # XXX set callback data based on priorities
            sorted_dict = dict(sorted(active.items(), key=lambda it: it[1]["priority"]))
            print(sorted_dict, file=sys.stderr)
            first = None
            for key, item in sorted_dict.items():
                if not first:
                    first = item
                else:
                    item.get("resource").register_callback("vlans", first.get("client").get_network_vlans)

            # Actually instantiate all the added resources above
            for key, item in sorted_dict.items():
                self.logger.info(
                    f"Creating {item.get('type')} resource at {key} for priority {item.get('priority')} item")

                item.get("client").create_resources(slice_name=item.get("slice_name"), rtype=item.get("type"))

        except Exception as e:
            self.logger.error(f"Exception occurred while creating resources: {e}")
            self.logger.error(traceback.format_exc())

    def delete(self, *, slice_name: str = None):
        if self.fabric_client:
            self.fabric_client.delete_resources(slice_name=slice_name)

        if self.chi_client:
            self.chi_client.delete_resources(slice_name=slice_name)

    def get_resources(self) -> list:
        resources = []
        if self.chi_client:
            chi_slices = self.chi_client.get_resources()
            if chi_slices is not None:
                for x in chi_slices:
                    resources.append(x)

        if self.fabric_client:
            fabric_slices = self.fabric_client.get_resources()
            if fabric_slices is not None:
                for x in fabric_slices:
                    resources.append(x)

        return resources
