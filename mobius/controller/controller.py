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
from logging.handlers import RotatingFileHandler

from mobius.controller.chi.chi_client import ChiClient
from mobius.controller.util.config import Config

from mobius.models import AbstractResourceListener


class ResourceListener(AbstractResourceListener):
    def __init__(self,  providers):
        self.providers = providers

    def on_added(self, source, slice_name, resource: dict):
        pass

    def on_created(self, source, slice_name, resource):
        for provider in self.providers.values():
            if provider != source:
                provider.on_created(self, slice_name, resource)

    def on_deleted(self, source, slice_name, resource):
        pass


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

        provider_configs = self.config.get_provider_config()
        self.providers = {}

        for provider_config in provider_configs:
            if provider_config.type == 'fabric':
                from mobius.controller.fabric.fabric_client import FabricClient

                provider = FabricClient(logger=self.logger, fabric_config=provider_config.attributes)
                provider.setup_environment()
                self.providers[provider_config.name] = provider
            elif provider_config.type == 'chi':
                provider = ChiClient(logger=self.logger, chi_config=provider_config.attributes)
                self.providers[provider_config.name] = provider
            else:
                raise Exception(f"no provider for {provider_config.name}")

    def create(self):
        resources = self.config.get_resource_config()
        resource_listener = ResourceListener(self.providers)

        for provider in self.providers.values():
            provider.set_resource_listener(resource_listener)

        try:
            self.logger.debug("Starting adding")
            for resource in resources:
                slice_config = resource.slice
                client = self.providers[slice_config.provider_name]
                slice_name = slice_config.name
                resource_dict = resource.attributes
                resource_dict[Config.RES_TYPE] = resource.type
                resource_dict[Config.RES_NAME_PREFIX] = resource.name

                if resource.has_dependencies():
                    resource_dict['has_dependencies'] = True
                    resource_dict['dependencies'] = resource.dependencies
                    resource_dict['resolved_dependencies'] = set()
                else:
                    resource_dict['has_dependencies'] = False

                if resource.is_node:
                    client.add_resources(resource=resource_dict, slice_name=slice_name)
                elif resource.is_network:
                    client.add_resources(resource=resource_dict, slice_name=slice_name)
        except Exception as e:
            self.logger.error(f"Exception occurred while adding resources: {e}")
            raise e

        try:
            self.logger.debug("Starting adding")
            for resource in resources:
                client = self.providers[resource.slice.provider_name]
                slice_name = resource.slice.name

                client.create_resources(slice_name=slice_name, rtype=None)
        except Exception as e:
            self.logger.error(f"Exception occurred while creating resources: {e}")
            raise e

    def delete(self, *, slice_name: str = None):
        for slice_config in self.config.get_slice_config():
            if not slice_name or slice_name == slice_config.name:
                client = self.providers[slice_config.provider_name]
                client.init_slice(slice_name=slice_config.name, resource=slice_config.attributes)
                client.delete_resources(slice_name=slice_config.name)

    def get_resources(self) -> list:
        resources = []

        for provider in self.providers.values():
            slices = provider.get_resources()

            if slices:
                resources.extend(slices)

        return resources
