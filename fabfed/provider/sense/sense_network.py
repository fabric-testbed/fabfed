import logging

from fabfed.model import Network
from .sense_constants import SERVICE_INSTANCE_KEYS
from . import sense_utils


class SenseNetwork(Network):
    def __init__(self, *, label, name: str, bandwidth, profile, layer3, interfaces, logger: logging.Logger):
        super().__init__(label=label, name=name, site="no_site")
        self.logger = logger
        self.profile = profile
        self.layer3 = layer3
        self.interfaces = interfaces
        self.bandwidth = bandwidth

    def create(self):
        si_uuid = sense_utils.find_instance_by_alias(alias=self.name)

        if not si_uuid:
            self.logger.info(f"Creating {self.name}")
            si_uuid = sense_utils.create_instance(profile=self.profile, bandwidth=self.bandwidth, alias=self.name,
                                                  layer3=self.layer3, interfaces=self.interfaces)
        else:
            self.logger.info(f"Already created {self.name}")

        instance_dict = sense_utils.service_instance_details(si_uuid=si_uuid)

        for key in SERVICE_INSTANCE_KEYS:
            self.__setattr__(key, instance_dict.get(key))

    def delete(self):
        from . import sense_utils

        si_uuid = sense_utils.find_instance_by_alias(alias=self.name)

        if si_uuid:
            self.logger.info(f"Deleting {self.name}")
            sense_utils.delete_instance(si_uuid=si_uuid)
