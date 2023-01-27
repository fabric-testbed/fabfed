import logging

from fabfed.model import Service, Node, SSHNode
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from .cloudlab_constants import *


class CloudlabProvider(Provider):

    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.slice = None

    def setup_environment(self):
        config = self.config
        credential_file = config.get(Constants.CREDENTIAL_FILE, None)

        if credential_file:
            from fabfed.util import utils

            profile = config.get(Constants.PROFILE)
            config = utils.load_yaml_from_file(credential_file)
            self.config = config = config[profile]

    def _init_slice(self):
        if not self.slice:
            self.logger.info(f"Initializing slice {self.name}")

            from fabfed.provider.cloudlab.cloudlab_slice import CloudlabSlice

            temp = CloudlabSlice(provider=self, logger=self.logger)
            temp.init()
            self.slice = temp

    def do_add_resource(self, *, resource: dict):
        self._init_slice()
        self.slice.add_resource(resource=resource)

    def do_create_resource(self, *, resource: dict):
        self._init_slice()
        self.slice.create_resource(resource=resource)

    def do_delete_resource(self, *, resource: dict):
        self._init_slice()
        self.slice.delete_resource(resource=resource)
