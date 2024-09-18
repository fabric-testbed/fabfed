from fabfed.model import Network
from fabfed.util.utils import get_logger
from . import sense_utils
from .sense_constants import SERVICE_INSTANCE_KEYS, SENSE_DTN, SENSE_DTN_IP
from .sense_exceptions import SenseException

logger = get_logger()


class SenseNetwork(Network):
    def __init__(self, *, label, name: str, bandwidth, profile, layer3, peering, interfaces):
        super().__init__(label=label, name=name, site="")
        self.profile = profile
        self.layer3 = layer3
        self.peering = peering
        self.interface = interfaces or []
        self.bandwidth = bandwidth
        self.switch_ports = []
        self.dtn = []
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
            raise SenseException(f"Found instance {si_uuid} with status={status}")

        if 'CREATE - READY' not in status:
            logger.debug(f"Provisioning {self.name}")
            status = sense_utils.instance_operate(si_uuid=si_uuid)

        if 'CREATE - READY' not in status:
            raise Exception(f"Creation failed for {si_uuid} {status}")

        logger.debug(f"Retrieving details {self.name} {status}")
        instance_dict = sense_utils.service_instance_details(si_uuid=si_uuid)

        import json

        logger.info(f"Retrieved details {self.name} {status}: \n{ json.dumps(instance_dict, indent=2)}")

        for key in SERVICE_INSTANCE_KEYS:
            self.__setattr__(key, instance_dict.get(key))

        self.id = self.referenceUUID

        if self.intents[0]['json']['service'] == 'vcn':
            if "GCP" in self.intents[0]['json']['data']['gateways'][0]['type'].upper():
                try:
                    template_file = 'gcp-template.json'
                    details = sense_utils.manifest_create(si_uuid=si_uuid, template_file=template_file)

                    for node_details in details.get("Nodes", []):
                        pairing_key = node_details.get('Pairing Key')
                        self.interface.append(dict(id=pairing_key, provider="sense"))
                        break
                except:
                    pass

        if self.intents[0]['json']['service'] == 'dnc':
            try:
                template_file = 'l2-template.json'
                details = sense_utils.manifest_create(si_uuid=si_uuid, template_file=template_file)
                self.switch_ports = details.get("Switch Ports", [])
            except:
                pass

        if self.switch_ports:
            temp = [dict(id=sp["Port"], provider="sense", vlan=sp["Vlan"]) for sp in self.switch_ports]

            for iface in self.interface:
                for temp_iface in temp:
                    if iface['id'] == temp_iface["id"]:
                        self.interface = [temp_iface]
                        break

            for sp in self.switch_ports:
                if sp.get(SENSE_DTN):
                    dtn = sp.get(SENSE_DTN)[0].get(SENSE_DTN_IP)

                    if dtn.find('/'):
                        self.dtn = [dtn[0: dtn.find('/')]]
                    else:
                        self.dtn = [dtn]

    def delete(self):
        from . import sense_utils

        si_uuid = sense_utils.find_instance_by_alias(alias=self.name)

        logger.debug(f"Deleting {self.name} {si_uuid}")

        if si_uuid:
            sense_utils.delete_instance(si_uuid=si_uuid)
            logger.debug(f"Deleted {self.name} {si_uuid}")
