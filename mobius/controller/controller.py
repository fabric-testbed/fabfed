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
import os
import traceback
from logging.handlers import RotatingFileHandler

from mobius.controller.chi.chi_client import ChiClient
from mobius.controller.util.config import Config


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

        runtime_config = None  # self.config.get_runtime_config()
        fabric_config = self.config.get_fabric_config()
        if fabric_config is not None:
            self.__setup_fabric(fabric_config=fabric_config, runtime_config=runtime_config)
            from mobius.controller.fabric.fabric_client import FabricClient
            self.fabric_client = FabricClient(logger=self.logger, fabric_config=runtime_config,
                                              runtime_config=runtime_config)

        chi_config = self.config.get_chi_config()
        if chi_config is not None:
            self.chi_client = ChiClient(logger=self.logger, chi_config=chi_config)

    @staticmethod
    def __setup_fabric(*, fabric_config: dict, runtime_config: dict):
        os.environ['FABRIC_CREDMGR_HOST'] = fabric_config.get(Config.FABRIC_CM_HOST)
        os.environ['FABRIC_ORCHESTRATOR_HOST'] = fabric_config.get(Config.FABRIC_OC_HOST)
        os.environ['FABRIC_TOKEN_LOCATION'] = fabric_config.get(Config.FABRIC_TOKEN_LOCATION)

        # Set your FABRIC PROJECT ID
        os.environ['FABRIC_PROJECT_ID'] = fabric_config.get(Config.FABRIC_PROJECT_ID)

        # Bastion IPs
        os.environ['FABRIC_BASTION_HOST'] = fabric_config.get(Config.FABRIC_BASTION_HOST)

        # Set your Bastion username and private key
        os.environ['FABRIC_BASTION_USERNAME'] = fabric_config.get(Config.FABRIC_BASTION_USER_NAME)
        os.environ['FABRIC_BASTION_KEY_LOCATION'] = fabric_config.get(Config.FABRIC_BASTION_KEY_LOCATION)

        # Set the keypair FABRIC will install in your slice.
        os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE'] = runtime_config.get(Config.RUNTIME_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'] = runtime_config.get(Config.RUNTIME_SLICE_PUBLIC_KEY_LOCATION)

        # If your slice private key uses a passphrase, set the passphrase
        # from getpass import getpass
        # print('Please input private key passphrase. Press enter for no passphrase.')
        # os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']=getpass()

    def create(self, *, slice_name: str = None, connected: str = None):
        try:
            self.logger.debug("Starting create")
            if slice_name is None:
                raise Exception("TODO Handle slice name")
                # TODO slice_name = self.config.get_runtime_config()[Config.RUNTIME_SLICE_NAME]
            resources = self.config.get_resource_config()
            active = dict()
            for resource in resources:
                resource_dict = resource.get(Config.RESOURCE)
                r_type = resource_dict.get(Config.RES_TYPE).lower()
                site = resource_dict.get("site", None)
                if not site:
                    self.logger.info("No site configured, skipping resource")
                    continue
                if site.lower().startswith("fabric"):
                    client = self.fabric_client
                elif site.lower().startswith("chi"):
                    client = self.chi_client
                else:
                    self.logger.info(f"Unknown site type {site}")
                    continue

                key = f"{site}-{r_type}"
                if r_type in [Config.RES_TYPE_BM.lower(), Config.RES_TYPE_VM.lower()]:
                    # XXX make these dicts classes
                    active.update({key: {"client": client,
                                          "type": Config.RES_TYPE_NODE,
                                          "priority": 100,
                                          "resource": client.add_resources(resource=resource_dict, slice_name=slice_name)}})
                elif connected and r_type == Config.RES_TYPE_NETWORK.lower():
                    # Network resources.
                    net_priority = 20 if "vlan" in resource_dict and resource_dict.get("vlan") == None else 10
                    active.update({key: {"client": client,
                                          "type": Config.RES_TYPE_NETWORK,
                                          "priority": net_priority,
                                          "resource": client.add_resources(resource=resource_dict, slice_name=slice_name)}})

            # XXX set callback data based on priorities
            sorted_dict = dict(sorted(active.items(), key=lambda item: item[1]["priority"]))
            first = None
            for site, item in sorted_dict.items():
                if not first:
                    first = item
                else:
                    item.get("resource").register_callback(first.get("client").get_network_vlans)

            # Actually instantiate all the added resources above
            for site, item in sorted_dict.items():
                self.logger.info(f"Creating {item.get('type')} resource at {site} for priority {item.get('priority')} item")
                item.get("client").create_resources(rtype=item.get("type"))
        except Exception as e:
            self.logger.error(f"Exception occurred while creating resources: {e}")
            self.logger.error(traceback.format_exc())

    def delete(self, *, slice_name: str = None):
        self.fabric_client.delete_resources(slice_name=slice_name)
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

