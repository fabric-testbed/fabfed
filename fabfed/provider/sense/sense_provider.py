import logging

from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from .sense_constants import SENSE_EDIT
from .sense_constants import SENSE_PROFILE_UID
from fabfed.exceptions import ResourceTypeNotSupported


class SenseProvider(Provider):
    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)

    def setup_environment(self):
        from fabfed.util import utils

        credential_file = self.config.get(Constants.CREDENTIAL_FILE)
        profile = self.config.get(Constants.PROFILE)
        config = utils.load_yaml_from_file(credential_file)
        self.config = config[profile]
        from .sense_client import init_client

        init_client(config)

    def do_add_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype != Constants.RES_TYPE_NETWORK.lower():
            raise ResourceTypeNotSupported(f"{rtype} for {label}")

        label = resource.get(Constants.LABEL)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        net_name = f'{self.name}-{name_prefix}'
        profile_uuid = resource.get(SENSE_PROFILE_UID)
        edit = resource.get(SENSE_EDIT, dict())

        from .sense_network import SenseNetwork

        net = SenseNetwork(label=label, name=net_name, profile_uuid=profile_uuid, edit=edit,
                           logger=self.logger)

        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self, resource=net)

    def do_create_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        assert rtype == Constants.RES_TYPE_NETWORK.lower()

        label = resource.get(Constants.LABEL)
        temp = [net for net in self._networks if net.label == label]

        for net in temp:
            self.logger.debug(f"Creating network: {vars(net)}")
            net.create()

            if self.resource_listener:
                self.resource_listener.on_created(source=self, provider=self, resource=net)

            self.logger.debug(f"Created network: {vars(net)}")

    def do_delete_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)

        if rtype != Constants.RES_TYPE_NETWORK.lower():
            raise Exception(f"Unknown resource {rtype}")

        net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'

        self.logger.debug(f"Deleting network: {net_name}")
        label = resource.get(Constants.LABEL)
        profile_uuid = resource.get(SENSE_PROFILE_UID)
        edit = resource.get(SENSE_EDIT, dict())

        from .sense_network import SenseNetwork

        net = SenseNetwork(label=label, name=net_name, profile_uuid=profile_uuid, edit=edit,
                           logger=self.logger)
        net.delete()
        self.logger.info(f"Deleted network: {net_name}")

        if self.resource_listener:
            self.resource_listener.on_delete(source=self, provider=self, resource=net)
