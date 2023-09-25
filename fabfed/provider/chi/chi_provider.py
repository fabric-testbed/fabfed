import logging
import os

from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from .chi_constants import *
import fabfed.provider.api.dependency_util as util


class ChiProvider(Provider):
    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.helper = None

    def setup_environment(self):
        pass

    def _setup_environment(self, *, site: str):
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

            if profile not in config:
                from fabfed.exceptions import ProviderException

                raise ProviderException(
                    f"credential file {credential_file} does not have a section for keyword {profile}")

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

    def do_add_resource(self, *, resource: dict):
        site = resource.get(Constants.RES_SITE)
        self._setup_environment(site=site)
        key_pair = self.config[CHI_KEY_PAIR]
        project_name = self.config[CHI_PROJECT_NAME]
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            layer3 = resource.get(Constants.RES_LAYER3)
            stitch_info = resource.get(Constants.RES_STITCH_INFO)
            assert stitch_info and stitch_info.consumer, f"resource {label} missing stitch provider"
            net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
            from fabfed.provider.chi.chi_network import ChiNetwork

            net = ChiNetwork(label=label, name=net_name, site=site, logger=self.logger,
                             layer3=layer3, stitch_provider=stitch_info.consumer,
                             project_name=project_name)
            self._networks.append(net)

            if self.resource_listener:
                self.resource_listener.on_added(source=self, provider=self, resource=net)

        else:
            network = resource.get(Constants.RES_NETWORK, DEFAULT_NETWORK)

            if util.has_resolved_internal_dependencies(resource=resource, attribute='network'):
                net = util.get_single_value_for_dependency(resource=resource, attribute='network')
                network = net.name

            node_count = resource.get(Constants.RES_COUNT, 1)
            image = resource.get(Constants.RES_IMAGE)
            node_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
            flavor = resource.get(Constants.RES_FLAVOR, DEFAULT_FLAVOR)
            label = resource.get(Constants.LABEL)

            for n in range(0, node_count):
                node_name = f"{self.name}-{node_name_prefix}{n}"

                from fabfed.provider.chi.chi_node import ChiNode

                node = ChiNode(label=label, name=node_name, image=image, site=site, flavor=flavor, logger=self.logger,
                               key_pair=key_pair, network=network, project_name=project_name)
                self._nodes.append(node)

                if self.resource_listener:
                    self.resource_listener.on_added(source=self, provider=self, resource=node)

    def do_create_resource(self, *, resource: dict):
        site = resource.get(Constants.RES_SITE)
        self._setup_environment(site=site)
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            temp = [net for net in self._networks if net.label == label]

            for net in temp:
                net.create()

                if self.resource_listener:
                    self.resource_listener.on_created(source=self, provider=self, resource=net)

        else:
            temp = [node for node in self._nodes if node.label == label]

            for node in temp:
                node.create()

            for node in temp:
                node.wait_for_active()

            for node in temp:
                node.wait_for_ssh()

                if self.resource_listener:
                    self.resource_listener.on_created(source=self, provider=self, resource=node)

    # noinspection PyTypeChecker
    def do_delete_resource(self, *, resource: dict):
        site = resource.get(Constants.RES_SITE)
        self._setup_environment(site=site)
        key_pair = self.config[CHI_KEY_PAIR]
        project_name = self.config[CHI_PROJECT_NAME]
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
            self.logger.debug(f"Deleting network: {net_name} at site {site}")
            from fabfed.provider.chi.chi_network import ChiNetwork
            from ...util.config_models import Config

            layer3 = Config("", "", {})

            net = ChiNetwork(label=label, name=net_name, site=site, logger=self.logger,
                             layer3=layer3, stitch_provider=None, project_name=project_name)
            net.delete()
            self.logger.info(f"Deleted network: {net_name} at site {site}")

            if self.resource_listener:
                self.resource_listener.on_deleted(source=self, provider=self, resource=net)
        else:
            node_count = resource.get(Constants.RES_COUNT, 1)

            for n in range(0, node_count):
                node_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
                node_name = f"{self.name}-{node_name_prefix}{n}"
                self.logger.debug(f"Deleting node: {node_name} at site {site}")

                from fabfed.provider.chi.chi_node import ChiNode

                node = ChiNode(label=label, name=node_name, image=None, site=site, flavor=None, logger=self.logger,
                               key_pair=key_pair, network=None, project_name=project_name)
                node.delete()
                self.logger.info(f"Deleted node: {node_name} at site {site}")

                if self.resource_listener:
                    self.resource_listener.on_deleted(source=self, provider=self, resource=node)
