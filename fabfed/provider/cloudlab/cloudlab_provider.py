from fabfed.exceptions import ResourceTypeNotSupported, ProviderException
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from fabfed.util.utils import get_logger
from .cloudlab_constants import *
from .cloudlab_exceptions import CloudlabException
from fabfed.policy.policy_helper import get_stitch_port_for_provider

logger = get_logger()


class CloudlabProvider(Provider):

    def __init__(self, *, type, label, name, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.supported_resources = [Constants.RES_TYPE_NETWORK.lower(), Constants.RES_TYPE_NODE.lower()]
        self.modified = None
        self.existing_map = {}

    def setup_environment(self):
        for attr in CLOUDLAB_CONF_ATTRS:
            if self.config.get(attr) is None:
                raise ProviderException(f"{self.name}: Expecting a value for {attr}")

        pkey = self.config[CLOUDLAB_SLICE_PRIVATE_KEY_LOCATION]

        from fabfed.util.utils import can_read, is_private_key, absolute_path

        pkey = absolute_path(pkey)

        if not can_read(pkey) or not is_private_key(pkey):
            raise ProviderException(f"{self.name}: unable to read/parse ssh key in {pkey}")

        self.config[CLOUDLAB_SLICE_PRIVATE_KEY_LOCATION] = pkey

        cert = self.config[CLOUDLAB_CERTIFICATE]
        cert = absolute_path(cert)

        if not can_read(cert):
            raise ProviderException(f"{self.name}: unable to read/parse ssh key in {cert}")

    @property
    def project(self):
        return self.config[CLOUDLAB_PROJECT]

    @property
    def cert(self):
        return self.config[CLOUDLAB_CERTIFICATE]

    @property
    def user(self):
        return self.config[CLOUDLAB_USER]

    @property
    def private_key_file_location(self):
        return self.config[CLOUDLAB_SLICE_PRIVATE_KEY_LOCATION]

    def experiment_params(self, name):
        exp_params = {
            "experiment": f"{self.project},{name}",
            "asjson": True
        }

        return exp_params

    def rpc_server(self):
        server_config = {
            "debug": 0,
            "impotent": 0,
            "verify": 0,
            "certificate": self.cert
        }

        import emulab_sslxmlrpc.xmlrpc as xmlrpc

        return xmlrpc.EmulabXMLRPC(server_config)

    def do_validate_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype not in self.supported_resources:
            raise ResourceTypeNotSupported(f"{rtype} for {label}")

        if rtype == Constants.RES_TYPE_NODE:
            creation_details = resource[Constants.RES_CREATION_DETAILS]

            if not creation_details['in_config_file']:
                return

            if not resource[Constants.INTERNAL_DEPENDENCIES]:
                raise ProviderException(f"{self.label} expecting node {label}'s to depend on clouldlab network")

            return

        interfaces = resource.get(Constants.RES_INTERFACES, list())

        if interfaces and 'vlan' not in interfaces[0]:
            raise ProviderException(f"{self.label} expecting {label}'s interface to have a vlan")

        creation_details = resource[Constants.RES_CREATION_DETAILS]

        if not creation_details['in_config_file']:
            return

        stitch_info = resource.get(Constants.RES_STITCH_INFO)

        if not stitch_info:
            raise ProviderException(f"{self.label} expecting stitch info in {rtype} resource {label}")

    def _get_interfaces(self, resource):
        interfaces = resource.get(Constants.RES_INTERFACES, list())
        cloudlab_stitch_port = get_stitch_port_for_provider(resource=resource, provider=self.type)

        if not interfaces:
            if 'option' in cloudlab_stitch_port and Constants.RES_INTERFACES in cloudlab_stitch_port['option']:
                interfaces = cloudlab_stitch_port['option'][Constants.RES_INTERFACES]

        return interfaces

    def do_add_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        label = resource.get(Constants.LABEL)
        self.existing_map[label] = []

        if self.saved_state and label in self.saved_state.creation_details:
            provider_saved_creation_details = self.saved_state.creation_details[label]

            if rtype == Constants.RES_NODES:
                for n in range(0, provider_saved_creation_details['total_count']):
                    node_name = f"{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}-{n}"
                    self.existing_map[label].append(node_name)
            else:
                assert provider_saved_creation_details['total_count'] == 1
                net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
                self.existing_map[label].append(net_name)

        creation_details = resource[Constants.RES_CREATION_DETAILS]

        if not creation_details['in_config_file']:
            return

        if rtype == Constants.RES_TYPE_NETWORK:
            states = resource[Constants.SAVED_STATES]

            if states:
                state = states[0]
                vlan = state.attributes['interface'][0]['vlan']
                interfaces = self._get_interfaces(resource)

                if isinstance(vlan, str):
                    vlan = int(vlan)

                if interfaces and interfaces[0]['vlan'] != vlan:
                    self.logger.warning(
                        f"{self.label} ignoring: {label}'s interface does not match provisioned vlan {vlan}")

                resource[Constants.RES_INTERFACES] = [{'vlan': vlan}]

        name_prefix = resource[Constants.RES_NAME_PREFIX]

        if rtype == Constants.RES_TYPE_NODE:
            from .cloudlab_node import CloudlabNode
            import fabfed.provider.api.dependency_util as util

            assert util.has_resolved_internal_dependencies(resource=resource, attribute='network')
            net = util.get_single_value_for_dependency(resource=resource, attribute='network')
            node_count = resource[Constants.RES_COUNT]

            for idx in range(0, node_count):
                node_name = f'{self.name}-{name_prefix}'
                node = CloudlabNode(label=label, name=f'{node_name}-{idx}', provider=self, network=net)
                self._nodes.append(node)
                self.resource_listener.on_added(source=self, provider=self, resource=node)
            return

        from .cloudlab_network import CloudNetwork

        net_name = f'{self.name}-{name_prefix}'
        profile = resource.get(Constants.RES_PROFILE)
        cloudlab_stitch_port = get_stitch_port_for_provider(resource=resource, provider=self.type)

        if not profile and cloudlab_stitch_port:
            profile = cloudlab_stitch_port.get(Constants.RES_PROFILE)

        if not profile:
            raise CloudlabException(message=f"must have a profile for {net_name}")

        cluster = resource.get(Constants.RES_CLUSTER)

        if not cluster and cloudlab_stitch_port:
            if 'option' in cloudlab_stitch_port and Constants.RES_CLUSTER in cloudlab_stitch_port['option']:
                cluster = cloudlab_stitch_port['option'][Constants.RES_CLUSTER]

        if not cluster:
            logger.warning(f"no cluster was was found for {net_name}")

        interfaces = resource.get(Constants.RES_INTERFACES, list())

        if not interfaces:
            if 'option' in cloudlab_stitch_port and Constants.RES_INTERFACES in cloudlab_stitch_port['option']:
                interfaces = cloudlab_stitch_port['option'][Constants.RES_INTERFACES]

        layer3 = resource.get(Constants.RES_LAYER3)
        net = CloudNetwork(label=label, name=net_name, provider=self, profile=profile, interfaces=interfaces,
                           layer3=layer3, cluster=cluster)
        self._networks.append(net)
        self.resource_listener.on_added(source=self, provider=self, resource=net)

    def do_create_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        label = resource.get(Constants.LABEL)

        if self.modified is None:
            added_map = {}

            for net in self.networks:
                if net.label not in added_map:
                    added_map[net.label] = []

                added_map[net.label].append(net.name)

            for node in self.nodes:
                if node.label not in added_map:
                    added_map[node.label] = []

                added_map[node.label].append(node.name)

            self.modified = (self.existing_map != added_map)

        if self.modified:
            assert rtype == Constants.RES_TYPE_NETWORK

            try:
                self.logger.info(f"Deleting cloudlab resources ....")
                net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
                logger.debug(f"Deleting network: {net_name}")

                from .cloudlab_network import CloudNetwork

                profile = resource.get(Constants.RES_PROFILE)
                interfaces = resource.get(Constants.RES_INTERFACES, list())
                layer3 = resource.get(Constants.RES_LAYER3)
                net = CloudNetwork(label=label, name=net_name, provider=self, profile=profile, interfaces=interfaces,
                                   layer3=layer3, cluster=None)

                net.delete()
                self.logger.info(f"Done deleting cloudlab resources ....")
                self.modified = False
                self.resource_listener.on_deleted(source=self, provider=self, resource=net)
            except Exception as e:
                self.logger.error(f"Exception deleting cloudlab resources ....", e)

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            if self.networks:
                self._networks[0].create()
                self.resource_listener.on_created(source=self, provider=self, resource=self._networks[0])

            return

        if rtype == Constants.RES_TYPE_NODE.lower():
            for node in [node for node in self._nodes if node.label == label]:
                self.logger.debug(f"Creating node: {vars(node)}")
                node.create()
                self.resource_listener.on_created(source=self, provider=self, resource=node)
                self.logger.debug(f"Created node: {vars(node)}")
            return

    def do_delete_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype in self.supported_resources
        label = resource.get(Constants.LABEL)

        if rtype == Constants.RES_TYPE_NODE.lower():
            # DO NOTHING
            return

        net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
        logger.debug(f"Deleting network: {net_name}")

        from .cloudlab_network import CloudNetwork

        profile = resource.get(Constants.RES_PROFILE)
        interfaces = resource.get(Constants.RES_INTERFACES, list())
        layer3 = resource.get(Constants.RES_LAYER3)
        net = CloudNetwork(label=label, name=net_name, provider=self, profile=profile, interfaces=interfaces,
                           layer3=layer3, cluster=None)
        net.delete()
        logger.info(f"Done Deleting network: {net_name}")
        self.resource_listener.on_deleted(source=self, provider=self, resource=net)
