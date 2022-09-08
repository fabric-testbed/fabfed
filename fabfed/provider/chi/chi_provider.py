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

from fabfed.provider.api.api_client import Provider
from fabfed.util.config import Config

from fabfed.model import ResourceListener
from fabfed.model.state import ProviderState


class ChiProvider(Provider, ResourceListener):
    def __init__(self, *, type, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, name=name, logger=logger, config=config)

    def setup_environment(self, *, site: str):
        """
        Setup the environment variables for Chameleon
        Should be invoked before any of the chi packages are imported otherwise, none of the CHI APIs work and
        fail with BAD REQUEST error
        @param site: site name
        """
        site_id = self.__get_site_identifier(site=site)
        os.environ['OS_AUTH_URL'] = self.config.get(Config.CHI_AUTH_URL)[site_id]
        os.environ['OS_IDENTITY_API_VERSION'] = "3"
        os.environ['OS_INTERFACE'] = "public"
        os.environ['OS_PROJECT_ID'] = self.config.get(Config.CHI_PROJECT_ID)[site_id]
        os.environ['OS_USERNAME'] = self.config.get(Config.CHI_USER)
        os.environ['OS_PROTOCOL'] = "openid"
        os.environ['OS_AUTH_TYPE'] = "v3oidcpassword"
        os.environ['OS_PASSWORD'] = self.config.get(Config.CHI_PASSWORD)
        os.environ['OS_IDENTITY_PROVIDER'] = "chameleon"
        os.environ['OS_DISCOVERY_ENDPOINT'] = \
            "https://auth.chameleoncloud.org/auth/realms/chameleon/.well-known/openid-configuration"
        os.environ['OS_CLIENT_ID'] = self.config.get(Config.CHI_CLIENT_ID)[site_id]
        os.environ['OS_ACCESS_TOKEN_TYPE'] = "access_token"
        os.environ['OS_CLIENT_SECRET'] = "none"
        os.environ['OS_REGION_NAME'] = site
        os.environ['OS_SLICE_PRIVATE_KEY_FILE'] = self.config.get(Config.RUNTIME_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['OS_SLICE_PUBLIC_KEY_FILE'] = self.config.get(Config.RUNTIME_SLICE_PUBLIC_KEY_LOCATION)

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
        else:
            return "uc"

    def init_slice(self, *, slice_config: dict, slice_name: str):
        pass

    def add_resource(self, *, resource: dict, slice_name: str):
        # Network info may be amended
        if resource.get(Config.RES_COUNT, 1) < 1:
            return None

        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")
        self.logger.debug(f"Adding {resource} to {slice_name}")

        site = resource.get(Config.RES_SITE)
        self.setup_environment(site=site)

        # Should be done only after setting up the environment
        from fabfed.provider.chi.chi_slice import ChiSlice
        if slice_name in self.slices:
            slice_object = self.slices[slice_name]
        else:
            slice_object = ChiSlice(name=slice_name, logger=self.logger, key_pair=self.config.get(Config.CHI_KEY_PAIR),
                                    project_name=self.config.get(Config.CHI_PROJECT_NAME))
            slice_object.set_resource_listener(self)
            self.slices[slice_name] = slice_object

        slice_object.add_resource(resource=resource)
        return slice_object

    def destroy_resources(self, *, provider_state: ProviderState):
        """
        Delete provisioned resources
         """
        for slice_state in provider_state.slice_states:
            self.logger.info(f"Deleting slice {slice_state.name}")

            all = []
            all.extend(slice_state.network_states)
            all.extend(slice_state.node_states)

            site = None

            for temp in all:
                site = temp.attributes.get('site', None)

                if site:
                    break

            assert site, "no site ...."

            self.setup_environment(site=site)

            from fabfed.provider.chi.chi_slice import ChiSlice

            if slice_state.name in self.slices:
                slice_object = self.slices[slice_state.name]
            else:
                slice_object = ChiSlice(name=slice_state.name, logger=self.logger,
                                        key_pair=self.config.get(Config.CHI_KEY_PAIR),
                                        project_name=self.config.get(Config.CHI_PROJECT_NAME))
                slice_object.set_resource_listener(self)
                self.slices[slice_state.name] = slice_object

            slice_object.destroy(slice_state=slice_state)
