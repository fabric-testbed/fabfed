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

from mobius.controller.api.api_client import ApiClient
from mobius.controller.util.config import Config

from mobius.models import AbstractResourceListener


class ChiClient(ApiClient, AbstractResourceListener):
    def __init__(self, *, logger: logging.Logger, chi_config: dict):
        self.logger = logger
        self.chi_config = chi_config
        self.slices = {}
        self.resource_listener = None

    def setup_environment(self, *, site: str):
        """
        Setup the environment variables for Chameleon
        Should be invoked before any of the chi packages are imported otherwise, none of the CHI APIs work and
        fail with BAD REQUEST error
        @param site: site name
        """
        site_id = self.__get_site_identifier(site=site)
        os.environ['OS_AUTH_URL'] = self.chi_config.get(Config.CHI_AUTH_URL)[site_id]
        os.environ['OS_IDENTITY_API_VERSION'] = "3"
        os.environ['OS_INTERFACE'] = "public"
        os.environ['OS_PROJECT_ID'] = self.chi_config.get(Config.CHI_PROJECT_ID)[site_id]
        os.environ['OS_USERNAME'] = self.chi_config.get(Config.CHI_USER)
        os.environ['OS_PROTOCOL'] = "openid"
        os.environ['OS_AUTH_TYPE'] = "v3oidcpassword"
        os.environ['OS_PASSWORD'] = self.chi_config.get(Config.CHI_PASSWORD)
        os.environ['OS_IDENTITY_PROVIDER'] = "chameleon"
        os.environ['OS_DISCOVERY_ENDPOINT'] = "https://auth.chameleoncloud.org/auth/realms/chameleon/.well-known/openid-configuration"
        os.environ['OS_CLIENT_ID'] = self.chi_config.get(Config.CHI_CLIENT_ID)[site_id]
        os.environ['OS_ACCESS_TOKEN_TYPE'] = "access_token"
        os.environ['OS_CLIENT_SECRET'] = "none"
        os.environ['OS_REGION_NAME'] = site
        os.environ['OS_SLICE_PRIVATE_KEY_FILE'] = self.chi_config.get(Config.RUNTIME_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['OS_SLICE_PUBLIC_KEY_FILE'] = self.chi_config.get(Config.RUNTIME_SLICE_PUBLIC_KEY_LOCATION)

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, source, slice_name, resource: dict):
        if self.resource_listener:
            self.resource_listener.on_added(self, slice_name, resource)

    def on_created(self, source, slice_name, resource: dict):
        if self.resource_listener:
            self.resource_listener.on_created(self, slice_name, resource)

    def on_deleted(self, source, slice_name, resource: dict):
        if self.resource_listener:
            self.resource_listener.on_deleted(self, slice_name, resource)

    @staticmethod
    def __get_site_identifier(*, site: str):
        if site == "CHI@UC":
            return "uc"
        elif site == "CHI@TACC":
            return "tacc"
        elif site == "CHI@NU":
            return "nu"
        elif site == "KVM@TACC":
            return "kvm"
        elif site == "CHI@Edge":
            return "edge"

    def init_slice(self, *, resource: dict, slice_name: str):
        self.logger.info(f"initializing  slice {slice_name}: slice_attributes={resource}")

        if slice_name not in self.slices:
            from mobius.controller.chi.chi_slice import Slice

            slice_object = Slice(name=slice_name, logger=self.logger, key_pair=self.chi_config.get(Config.CHI_KEY_PAIR),
                                 project_name=self.chi_config.get(Config.CHI_PROJECT_NAME))
            slice_object.set_resource_listener(self)
            self.slices[slice_name] = slice_object

    def get_resources(self, *, slice_name: str = None):
        if slice_name is not None:
            if slice_name in self.slices:
                return [self.slices.get(slice_name)]
        else:
            return self.slices.values()

    def get_available_resources(self):
        pass

    def get_network_vlans(self, slice_name: str = None):
        for sname, sobj in self.slices.items():
            for n in sobj.networks:
                return n.get_vlans()

    def add_resources(self, *, resource: dict, slice_name: str):
        # Network info may be amended
        if resource.get(Config.RES_COUNT, 1) < 1:
            return None

        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")
        self.logger.debug(f"Adding {resource} to {slice_name}")

        site = resource.get(Config.RES_SITE)
        self.setup_environment(site=site)

        # Should be done only after setting up the environment
        from mobius.controller.chi.chi_slice import Slice
        if slice_name in self.slices:
            slice_object = self.slices[slice_name]
        else:
            slice_object = Slice(name=slice_name, logger=self.logger, key_pair=self.chi_config.get(Config.CHI_KEY_PAIR),
                                 project_name=self.chi_config.get(Config.CHI_PROJECT_NAME))
            slice_object.set_resource_listener(self)
            self.slices[slice_name] = slice_object

        slice_object.add_resource(resource=resource)
        return slice_object

    def create_resources(self, *,  slice_name: str = None, rtype: str = None):
        self.logger.info(f"Creating  CHI using slice {slice_name} rtype={rtype}")

        chi_slice = self.slices[slice_name]
        chi_slice.create()

    def delete_resources(self, *, slice_name: str = None):
        if slice_name in self.slices:
            self.logger.info(f"Deleting CHI slice {slice_name}")
            slice_object = self.slices[slice_name]
            slice_object.delete()
            return

        for slice_name, slice_object in self.slices.items():
            self.logger.info(f"Deleting CHI slice {slice_name}")
            slice_object.delete()
