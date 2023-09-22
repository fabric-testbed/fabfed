from fabfed.policy.policy_helper import get_stitch_port_for_provider
from fabfed.exceptions import ResourceTypeNotSupported
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from fabfed.util.utils import get_logger
from . import sense_utils
from .sense_exceptions import SenseException

logger = get_logger()


class SenseProvider(Provider):
    def __init__(self, *, type, label, name, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.supported_resources = [Constants.RES_TYPE_NETWORK.lower(),  Constants.RES_TYPE_NODE.lower()]

    def setup_environment(self):
        from fabfed.util import utils

        credential_file = self.config.get(Constants.CREDENTIAL_FILE)
        profile = self.config.get(Constants.PROFILE)
        config = utils.load_yaml_from_file(credential_file)

        if profile not in config:
            from fabfed.exceptions import ProviderException

            raise ProviderException(
                f"credential file {credential_file} does not have a section for keyword {profile}"
            )

        self.config = config[profile]
        from .sense_client import init_client

        init_client(self.config)

    @property
    def private_key_file_location(self):
        from .sense_constants import SENSE_SLICE_PRIVATE_KEY_LOCATION

        return self.config.get(SENSE_SLICE_PRIVATE_KEY_LOCATION)

    def _handle_peering_config(self, resource):
        import fabfed.provider.api.dependency_util as util
        from fabfed.model import Network

        peering = resource.get(Constants.RES_PEERING)
        prop = 'stitch_interface'

        if peering and util.has_resolved_external_dependencies(resource=resource, attribute=prop):
            net = util.get_single_value_for_dependency(resource=resource, attribute=prop)

            if isinstance(net, Network):
                iface = net.interface

                if isinstance(iface, list):
                    iface = iface[0]

                if isinstance(iface, dict) and iface.get("provider") == "fabric":
                    peering.attributes[Constants.RES_ID] = iface[Constants.RES_ID]
                    peering.attributes[Constants.RES_SECURITY] = iface[Constants.RES_SECURITY]
                    self.logger.info(f"Added id and password to peering config:id={iface[Constants.RES_ID]}")

        return peering

    def do_add_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype not in self.supported_resources:
            raise ResourceTypeNotSupported(f"{rtype} for {label}")

        name_prefix = resource.get(Constants.RES_NAME_PREFIX)

        if rtype == Constants.RES_TYPE_NODE.lower():
            from .sense_node import SenseNode
            import fabfed.provider.api.dependency_util as util

            assert util.has_resolved_internal_dependencies(resource=resource, attribute='network')
            net = util.get_single_value_for_dependency(resource=resource, attribute='network')
            profile_uuid = sense_utils.get_profile_uuid(profile=net.profile)
            vms = sense_utils.get_vms_specs_from_profile(profile_uuid=profile_uuid)
            node_name = f'{self.name}-{name_prefix}'

            for idx, vm in enumerate(vms):
                node = SenseNode(label=label, name=f'{node_name}-{idx}', network=net.name, spec=vm, provider=self)
                self._nodes.append(node)

                if self.resource_listener:
                    self.resource_listener.on_added(source=self, provider=self, resource=node)

            return

        sense_stitch_port = get_stitch_port_for_provider(resource=resource, provider=self.type)
        interfaces = resource.get(Constants.RES_INTERFACES)

        if not interfaces and 'option' in sense_stitch_port:
            interfaces = sense_stitch_port['option'].get('interface')

        if interfaces:
            for interface in interfaces:
                if not interface.get(Constants.RES_BANDWIDTH):
                    interface[Constants.RES_BANDWIDTH] = resource.get(Constants.RES_BANDWIDTH)

        net_name = f'{self.name}-{name_prefix}'
        profile = resource.get(Constants.RES_PROFILE)

        if not profile and sense_stitch_port:
            profile = sense_stitch_port.get(Constants.RES_PROFILE)

        if not profile:
            raise SenseException(f"Must have a profile for {net_name}")

        layer3 = resource.get(Constants.RES_LAYER3)
        peering = self._handle_peering_config(resource)
        bandwidth = resource.get(Constants.RES_BANDWIDTH)

        from .sense_network import SenseNetwork

        net = SenseNetwork(label=label, name=net_name, profile=profile,
                           bandwidth=bandwidth, layer3=layer3, peering=peering, interfaces=interfaces)

        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self, resource=net)

    def do_create_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype in self.supported_resources

        label = resource.get(Constants.LABEL)

        if rtype == Constants.RES_TYPE_NODE.lower():
            for node in [node for node in self._nodes if node.label == label]:
                self.logger.debug(f"Creating node: {vars(node)}")
                node.create()

                if self.resource_listener:
                    self.resource_listener.on_created(source=self, provider=self, resource=node)

                self.logger.debug(f"Created node: {vars(node)}")

            return

        for net in [net for net in self._networks if net.label == label]:
            self.logger.debug(f"Creating network: {vars(net)}")
            net.create()

            if self.resource_listener:
                self.resource_listener.on_created(source=self, provider=self, resource=net)

            self.logger.debug(f"Created network: {vars(net)}")

    def do_delete_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype in self.supported_resources
        label = resource.get(Constants.LABEL)

        if rtype == Constants.RES_TYPE_NODE.lower():
            # DO NOTHING
            return

        net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'

        logger.debug(f"Deleting network: {net_name}")

        from .sense_network import SenseNetwork

        net = SenseNetwork(label=label, name=net_name, bandwidth=None, profile=None, layer3=None, interfaces=None,
                           peering=None)

        net.delete()
        logger.debug(f"Done Deleting network: {net_name}")

        if self.resource_listener:
            self.resource_listener.on_deleted(source=self, provider=self, resource=net)
