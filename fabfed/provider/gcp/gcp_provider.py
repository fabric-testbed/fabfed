from fabfed.exceptions import ResourceTypeNotSupported, ProviderException
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from fabfed.util.utils import get_logger
from . import gcp_constants

logger = get_logger()


class GcpProvider(Provider):
    def __init__(self, *, type, label, name, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.supported_resources = [Constants.RES_TYPE_NETWORK.lower()]

    @property
    def project(self):
        return self.config.get(gcp_constants.PROJECT)

    @property
    def service_key_path(self):
        return self.config.get(gcp_constants.SERVICE_KEY_PATH)

    def setup_environment(self):
        normalized_config = {}

        for k, v in self.config.items():
            normalized_config[k.upper()] = v

        self.config = normalized_config
        assert self.config.get(gcp_constants.SERVICE_KEY_PATH)
        assert self.config.get(gcp_constants.PROJECT)

        for attr in [gcp_constants.PROJECT, gcp_constants.SERVICE_KEY_PATH]:
            if self.config.get(attr) is None:
                raise ProviderException(f"{self.name}: Expecting a value for {attr}")

        skey = self.config[gcp_constants.SERVICE_KEY_PATH]

        from fabfed.util.utils import can_read, absolute_path

        skey = absolute_path(skey)

        if not can_read(skey):
            raise ProviderException(f"{self.name}: unable to read service key in {skey}")

        try:
            with open(skey, 'r') as fp:
                import json

                json.load(fp)
        except Exception as e:
            raise ProviderException(f"{self.name}:Unable to parse {skey} to json:{e}")

        self.config[gcp_constants.SERVICE_KEY_PATH] = skey

    def do_add_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype not in self.supported_resources:
            raise ResourceTypeNotSupported(f"{rtype} for {label}")

        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        net_name = f'{self.name}-{name_prefix}'
        layer3 = resource.get(Constants.RES_LAYER3)
        peering = resource.get(Constants.RES_PEERING)

        from .gcp_network import GcpNetwork

        net = GcpNetwork(label=label, name=net_name, provider=self, layer3=layer3, peering=peering)
        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self, resource=net)

    def do_create_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype in self.supported_resources
        label = resource.get(Constants.LABEL)

        for net in [net for net in self._networks if net.label == label]:
            self.logger.debug(f"Creating network: {vars(net)}")
            net.create()
            self.logger.debug(f"Created network: {vars(net)}")

            if self.resource_listener:
                self.resource_listener.on_created(source=self, provider=self, resource=net)

    def do_delete_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype in self.supported_resources
        label = resource.get(Constants.LABEL)

        if rtype == Constants.RES_TYPE_NODE.lower():
            # DO NOTHING
            return

        net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
        logger.debug(f"Deleting network: {net_name}")

        from .gcp_network import GcpNetwork

        layer3 = resource.get(Constants.RES_LAYER3)
        peering = resource.get(Constants.RES_PEERING)
        net = GcpNetwork(label=label, name=net_name, provider=self, layer3=layer3, peering=peering)
        net.delete()
        logger.debug(f"Done Deleting network: {net_name}")

        if self.resource_listener:
            self.resource_listener.on_deleted(source=self, provider=self, resource=net)
