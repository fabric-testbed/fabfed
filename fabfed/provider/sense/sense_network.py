from fabfed.model import Network
from fabfed.util.utils import get_logger
from . import sense_utils
from .sense_constants import SERVICE_INSTANCE_KEYS

logger = get_logger()


class SenseNetwork(Network):
    def __init__(self, *, label, name: str, bandwidth, profile, layer3, peering, interfaces):
        super().__init__(label=label, name=name, site="")
        self.profile = profile
        self.layer3 = layer3
        self.peering = peering
        self.interface = interfaces
        self.bandwidth = bandwidth
        self.switch_ports = []
        self.id = ''

        # CREATE - COMPILED, CREATE - COMMITTING, CREATE - COMMITTED, CREATE - READY
    def create(self):
        si_uuid = sense_utils.find_instance_by_alias(alias=self.name)

        if not si_uuid:
            logger.debug(f"Creating {self.name}")
            si_uuid, status = sense_utils.create_instance(profile=self.profile, bandwidth=self.bandwidth,
                                                          alias=self.name,
                                                          layer3=self.layer3, peering=self.peering,
                                                          interfaces=self.interface)
        else:
            logger.debug(f"Found {self.name} {si_uuid}")
            assert si_uuid
            status = sense_utils.instance_get_status(si_uuid=si_uuid)
            logger.info(f"Found existing {self.name} {si_uuid} with status={status}")

        if 'FAILED' in status:
            logger.warn(f"In Create: Deleting {self.name} {si_uuid} with status={status}")
            sense_utils.delete_instance(si_uuid=si_uuid)
            si_uuid, status = sense_utils.create_instance(profile=self.profile, bandwidth=self.bandwidth,
                                                          alias=self.name,
                                                          layer3=self.layer3, peering=self.peering,
                                                          interfaces=self.interface)

        if 'FAILED' not in status and 'CREATE - READY' not in status:
            logger.debug(f"Provisioning {self.name}")
            status = sense_utils.instance_operate(si_uuid=si_uuid)

        logger.debug(f"Retrieving details {self.name} {status}")
        instance_dict = sense_utils.service_instance_details(si_uuid=si_uuid)

        import json

        logger.debug(f"Retrieved details {self.name} {status}: \n{ json.dumps(instance_dict, indent=2)}")

        for key in SERVICE_INSTANCE_KEYS:
            self.__setattr__(key, instance_dict.get(key))

        self.id = self.referenceUUID

        if 'CREATE - READY' not in status:
            raise Exception(f"Creation failed for {si_uuid} {status}")

        if self.intents[0]['json']['service'] == 'dnc':
            try:
                template_file = 'l2-template.json'
                details = sense_utils.manifest_create(si_uuid=si_uuid, template_file=template_file)
                self.switch_ports = details.get("Switch Ports", [])
            except:
                pass

        if self.switch_ports:
            temp = [dict(id=self.switch_ports[0]["Port"], provider="sense", vlan=self.switch_ports[0]["Vlan"]),
                    dict(id=self.switch_ports[1]["Port"], provider="sense", vlan=self.switch_ports[1]["Vlan"])]
            self.interface = temp

    def delete(self):
        from . import sense_utils

        si_uuid = sense_utils.find_instance_by_alias(alias=self.name)

        logger.debug(f"Deleting {self.name} {si_uuid}")

        if si_uuid:
            sense_utils.delete_instance(si_uuid=si_uuid)
            logger.debug(f"Deleted {self.name} {si_uuid}")
