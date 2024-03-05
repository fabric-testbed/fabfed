import logging

from fabfed.provider.api.provider import Provider
from ...util.constants import Constants
from .fabric_constants import *


class FabricProvider(Provider):
    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.slice = None

        from fabrictestbed_extensions.fablib.constants import Constants as FC
        from fabfed.util.utils import get_base_dir

        FC.DEFAULT_FABRIC_CONFIG_DIR = get_base_dir(self.name)
        FC.DEFAULT_FABRIC_RC = f"{FC.DEFAULT_FABRIC_CONFIG_DIR}/fabric_rc"

    def setup_environment(self):
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

        import os

        os.environ['FABRIC_CREDMGR_HOST'] = config.get(FABRIC_CM_HOST, DEFAULT_CM_HOST)
        os.environ['FABRIC_ORCHESTRATOR_HOST'] = config.get(FABRIC_OC_HOST, DEFAULT_OC_HOST)
        os.environ['FABRIC_TOKEN_LOCATION'] = config.get(FABRIC_TOKEN_LOCATION)
        os.environ['FABRIC_PROJECT_ID'] = config.get(FABRIC_PROJECT_ID)

        os.environ['FABRIC_BASTION_HOST'] = config.get(FABRIC_BASTION_HOST, DEFAULT_BASTION_HOST)
        os.environ['FABRIC_BASTION_USERNAME'] = config.get(FABRIC_BASTION_USER_NAME)
        os.environ['FABRIC_BASTION_KEY_LOCATION'] = config.get(FABRIC_BASTION_KEY_LOCATION)

        os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE'] = config.get(FABRIC_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'] = config.get(FABRIC_SLICE_PUBLIC_KEY_LOCATION)

        from fabfed.util.utils import get_log_level, get_log_location

        location = get_log_location()

        from fabrictestbed_extensions.fablib.fablib import fablib

        if fablib.get_default_fablib_manager().get_log_file() != location:
            self.logger.debug("Initializing fablib extensions logging ...")
            fablib.get_default_fablib_manager().set_log_file(location)
            fablib.get_default_fablib_manager().set_log_level(get_log_level())

            for handler in logging.root.handlers.copy():
                logging.root.removeHandler(handler)

            for handler in self.logger.handlers:
                logging.root.addHandler(handler)

    def _init_slice(self):
        if not self.slice:
            self.logger.info(f"Initializing slice {self.name}")

            from fabfed.provider.fabric.fabric_slice import FabricSlice

            temp = FabricSlice(provider=self, logger=self.logger)
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
