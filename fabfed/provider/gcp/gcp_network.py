from fabfed.model import Network
from fabfed.util.utils import get_logger, Constants
from . import gcp_utils
from .gcp_provider import GcpProvider

logger = get_logger()


class GcpNetwork(Network):
    def __init__(self, *, label, name: str, provider: GcpProvider, layer3, peering):
        super().__init__(label=label, name=name, site="")
        self._provider = provider
        self.layer3 = layer3
        self.peering = peering

    def create(self):
        project = self._provider.project
        service_key_path = self._provider.service_key_path
        region = self.peering.attributes.get(Constants.RES_CLOUD_REGION)

        router_name = f'{self.name}-router'
        router = gcp_utils.find_router(service_key_path=service_key_path,
                                       project=project,
                                       region=region,
                                       router_name=router_name)

        if not router:
            google_asn = self.peering.attributes.get(Constants.RES_REMOTE_ASN)
            vpc = self.peering.attributes.get(Constants.RES_CLOUD_VPC)
            gcp_utils.create_router(service_key_path=service_key_path,
                                    project=project,
                                    region=region,
                                    router_name=router_name,
                                    vpc=vpc,
                                    bgp_asn=google_asn)

        attachment_name = f'{self.name}-vlan-attachment'
        attachment = gcp_utils.find_interconnect_attachment(service_key_path=service_key_path,
                                                            project=project,
                                                            region=region,
                                                            attachment_name=attachment_name)

        if not attachment:
            gcp_utils.create_interconnect_attachment(service_key_path=service_key_path,
                                                     project=project,
                                                     region=region,
                                                     router_name=router_name,
                                                     attachment_name=attachment_name)

    def delete(self):
        project = self._provider.project
        service_key_path = self._provider.service_key_path
        region = self.peering.attributes.get(Constants.RES_CLOUD_REGION)

        attachment_name = f'{self.name}-vlan-attachment'
        attachment = gcp_utils.find_interconnect_attachment(service_key_path=service_key_path,
                                                            project=project,
                                                            region=region,
                                                            attachment_name=attachment_name)

        if attachment:
            gcp_utils.delete_interconnect_vlan_attachment(service_key_path=service_key_path,
                                                          project=project,
                                                          region=region,
                                                          attachment_name=attachment_name)

        router_name = f'{self.name}-router'
        router = gcp_utils.find_router(service_key_path=service_key_path,
                                       project=project,
                                       region=region,
                                       router_name=router_name)

        if router:
            gcp_utils.delete_router(service_key_path=service_key_path,
                                    project=project,
                                    region=region,
                                    router_name=router_name)
