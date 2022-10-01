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

from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from .chi_constants import *


class ChiProvider(Provider):
    def __init__(self, *, type, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, name=name, logger=logger, config=config)
        self.mappings = dict()

    def setup_environment(self, *, site: str):
        """
        Setup the environment variables for Chameleon
        Should be invoked before any of the chi packages are imported otherwise, none of the CHI APIs work and
        fail with BAD REQUEST error
        @param site: site name
        """
        config = self.config
        credential_file = config.get(Constants.CREDENTIAL_FILE, None)

        if credential_file:
            from fabfed.util import utils

            profile = config.get(Constants.PROFILE)
            config = utils.load_yaml_from_file(credential_file)
            self.config = config = config[profile]

        site_id = self.__get_site_identifier(site=site)
        os.environ['OS_AUTH_URL'] = config.get(CHI_AUTH_URL, DEFAULT_AUTH_URLS)[site_id]
        os.environ['OS_IDENTITY_API_VERSION'] = "3"
        os.environ['OS_INTERFACE'] = "public"
        os.environ['OS_PROJECT_ID'] = config.get(CHI_PROJECT_ID, DEFAULT_PROJECT_IDS)[site_id]
        os.environ['OS_USERNAME'] = config.get(CHI_USER)
        os.environ['OS_PROTOCOL'] = "openid"
        os.environ['OS_AUTH_TYPE'] = "v3oidcpassword"
        os.environ['OS_PASSWORD'] = config.get(CHI_PASSWORD)
        os.environ['OS_IDENTITY_PROVIDER'] = "chameleon"
        os.environ['OS_DISCOVERY_ENDPOINT'] = DEFAULT_DISCOVERY_URL
        os.environ['OS_CLIENT_ID'] = config.get(CHI_CLIENT_ID, DEFAULT_CLIENT_IDS)[site_id]
        os.environ['OS_ACCESS_TOKEN_TYPE'] = "access_token"
        os.environ['OS_CLIENT_SECRET'] = "none"
        os.environ['OS_REGION_NAME'] = site
        os.environ['OS_SLICE_PRIVATE_KEY_FILE'] = config.get(CHI_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['OS_SLICE_PUBLIC_KEY_FILE'] = config.get(CHI_SLICE_PUBLIC_KEY_LOCATION)

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
        self.logger.debug(f"Initializing {slice_name}: {slice_config}")
        label = slice_config.get(Constants.LABEL)

        if slice_name in self.mappings:
            raise Exception("provider cannot have more than one slice with same name")

        self.mappings[slice_name] = label

        label = self.mappings[slice_name]
        from fabfed.provider.chi.chi_slice import ChiSlice

        slice_object = ChiSlice(label=label, name=slice_name, logger=self.logger,
                                key_pair=self.config.get(CHI_KEY_PAIR),
                                project_name=self.config.get(CHI_PROJECT_NAME))
        slice_object.set_resource_listener(self)
        self.slices[slice_name] = slice_object

    def add_resource(self, *, resource: dict, slice_name: str):
        site = resource.get(Constants.RES_SITE)
        self.setup_environment(site=site)
        slice_object = self.slices[slice_name]
        slice_object.use_key_pair(self.config[CHI_KEY_PAIR])
        slice_object.use_project_name(self.config[CHI_PROJECT_NAME])
        super().add_resource(resource=resource, slice_name=slice_name)

    def delete_resource(self, *, resource: dict, slice_name: str):
        """
            Delete provisioned resource
        """
        site = resource.get(Constants.RES_SITE)
        self.setup_environment(site=site)
        slice_object = self.slices[slice_name]
        slice_object.use_key_pair(self.config[CHI_KEY_PAIR])
        slice_object.use_project_name(self.config[CHI_PROJECT_NAME])
        super().delete_resource(resource=resource, slice_name=slice_name)
