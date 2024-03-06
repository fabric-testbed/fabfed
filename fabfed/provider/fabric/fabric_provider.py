import logging

from fabfed.provider.api.provider import Provider
from ...util.constants import Constants
from .fabric_constants import *
from fabfed.util.utils import get_logger

logger = get_logger()

class FabricProvider(Provider):
    def __init__(self, *, type, label, name, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        self.slice = None
        self.retry = 5
        self.slice_init = False

        from fabrictestbed_extensions.fablib.constants import Constants as FC
        from fabfed.util.utils import get_base_dir

        FC.DEFAULT_FABRIC_CONFIG_DIR = get_base_dir(self.name)
        FC.DEFAULT_FABRIC_RC = f"{FC.DEFAULT_FABRIC_CONFIG_DIR}/fabric_rc"

    def setup_environment(self):
        config = self.config

        import os

        os.environ['FABRIC_CREDMGR_HOST'] = config.get(FABRIC_CM_HOST, DEFAULT_CM_HOST)
        os.environ['FABRIC_ORCHESTRATOR_HOST'] = config.get(FABRIC_OC_HOST, DEFAULT_OC_HOST)
        os.environ['FABRIC_PROJECT_ID'] = config.get(FABRIC_PROJECT_ID)
        os.environ['FABRIC_BASTION_HOST'] = config.get(FABRIC_BASTION_HOST, DEFAULT_BASTION_HOST)
        os.environ['FABRIC_BASTION_USERNAME'] = config.get(FABRIC_BASTION_USER_NAME)
        os.environ['FABRIC_BASTION_KEY_LOCATION'] = config.get(FABRIC_BASTION_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE'] = config.get(FABRIC_SLICE_PRIVATE_KEY_LOCATION)
        os.environ['FABRIC_SLICE_PUBLIC_KEY_FILE'] = config.get(FABRIC_SLICE_PUBLIC_KEY_LOCATION)

        from pathlib import Path
        from fabfed.util.utils import get_log_level, get_log_location

        token_location = config.get(FABRIC_TOKEN_LOCATION)
        token_location = str(Path(token_location).expanduser().absolute())

        with open(token_location, 'r') as f:
            text = f.read()
            logger.info(f"{text}")

        with open(token_location, 'r') as fp:
            import json

            json.load(fp)

        if Constants.COPY_TOKENS:
            import shutil
            import uuid

            destination = f'/tmp/tokens/token-{self.name}-{uuid.uuid4()}.json'
            shutil.copy2(token_location, destination)

        os.environ['FABRIC_TOKEN_LOCATION'] = token_location

        from fabrictestbed_extensions.fablib.fablib import fablib

        location = get_log_location()

        if fablib.get_default_fablib_manager().get_log_file() != location:
            self.logger.debug("Initializing fablib extensions logging ...")
            fablib.get_default_fablib_manager().set_log_file(location)
            fablib.get_default_fablib_manager().set_log_level(get_log_level())

            json.load(fp)

    def _init_slice(self, destroy_phase=False):
        if not self.slice_init:
            self.logger.info(f"Initializing slice {self.name}")
            self.slice_init = True

            import time
            from fabfed.util.utils import get_log_level, get_log_location

            location = get_log_location()

            for attempt in range(self.retry):
                try:
                    from fabrictestbed_extensions.fablib.fablib import fablib

                    if fablib.get_default_fablib_manager().get_log_file() != location:
                        self.logger.debug("Initializing fablib extensions logging ...")
                        fablib.get_default_fablib_manager().set_log_file(location)
                        fablib.get_default_fablib_manager().set_log_level(get_log_level())

                        for handler in logging.root.handlers.copy():
                            logging.root.removeHandler(handler)

                        for handler in self.logger.handlers:
                            logging.root.addHandler(handler)

                    from fabfed.provider.fabric.fabric_slice import FabricSlice

                    temp = FabricSlice(provider=self, logger=self.logger)
                    temp.init(destroy_phase)
                    self.slice = temp
                    self.logger.info(f"Done initializing slice {self.name}")
                    break
                except Exception as e:
                    if attempt == self.retry - 1:
                        raise e

                self.logger.info(f"Initializing slice {self.name}. Going to sleep. Will retry ...")
                time.sleep(2)

    def supports_modify(self):
        return True

    def do_add_resource(self, *, resource: dict):
        self._init_slice()
        assert self.slice.slice_object is not None
        self.slice.add_resource(resource=resource)

    def do_create_resource(self, *, resource: dict):
        assert self.slice.slice_object is not None
        self.slice.create_resource(resource=resource)

    def do_delete_resource(self, *, resource: dict):
        self._init_slice(True)
        self.slice.delete_resource(resource=resource)

