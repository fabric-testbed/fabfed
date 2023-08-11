from fabfed.model import Network
from fabfed.util.utils import get_logger, Constants
from . import aws_utils
from .aws_provider import AwsProvider
from .aws_exceptions import AwsException

logger = get_logger()


class AwsNetwork(Network):
    def __init__(self, *, label, name: str, provider: AwsProvider, layer3, peering):
        super().__init__(label=label, name=name, site="")
        self._provider = provider
        self.layer3 = layer3
        self.peering = peering
        self.association_id = None
        self.vpc_id = None
        self.vpn_id = None
        self.direct_connect_gateway_id = None

    @property
    def gateway_name(self):
        return 'fab-gateway'

    @property
    def vif_name(self):
        return 'fab-vif'

    def create(self):
        region = self.peering.attributes.get(Constants.RES_CLOUD_REGION)
        ec2_client = aws_utils.create_ec2_client(region=region,
                                                 access_key=self._provider.access_key,
                                                 secret_key=self._provider.secret_key)

        self.vpc_id = self.peering.attributes.get(Constants.RES_CLOUD_VPC)
        self.vpn_id = aws_utils.find_vpn_gateway_id(ec2_client=ec2_client, vpc_id=self.vpc_id)

        if not self.vpn_id:
            raise AwsException(f'No Virtual Gateway found for vpc {self.vpc_id}.')

        direct_connect_client = aws_utils.create_direct_connect_client(
            region=region,
            access_key=self._provider.access_key,
            secret_key=self._provider.secret_key)

        gateway_name = self.gateway_name
        vif_name = self.vif_name

        self.direct_connect_gateway_id = aws_utils.create_direct_connect_gateway_id(
            direct_connect_client=direct_connect_client,
            gateway_name=gateway_name,
            vif_name=vif_name)

        self.association_id = aws_utils.associate_dxgw_vpn(
            direct_connect_client=direct_connect_client,
            direct_connect_gateway_id=self.direct_connect_gateway_id,
            vpn_id=self.vpn_id)

    def delete(self):
        region = self.peering.attributes.get(Constants.RES_CLOUD_REGION)
        ec2_client = aws_utils.create_ec2_client(region=region,
                                                 access_key=self._provider.access_key,
                                                 secret_key=self._provider.secret_key)

        vpc_id = self.peering.attributes.get(Constants.RES_CLOUD_VPC)
        vpn_id = aws_utils.find_vpn_gateway_id(ec2_client=ec2_client, vpc_id=vpc_id)

        if not vpn_id:
            return

        direct_connect_client = aws_utils.create_direct_connect_client(
            region=region,
            access_key=self._provider.access_key,
            secret_key=self._provider.secret_key)
        gateway_name = self.gateway_name
        direct_connect_gateway_id = aws_utils.find_direct_connect_gateway_id(
            direct_connect_client=direct_connect_client,
            gateway_name=gateway_name)

        if not direct_connect_gateway_id:
            return

        association_id = aws_utils.find_association_dxgw_vpn_id(
            direct_connect_client=direct_connect_client,
            direct_connect_gateway_id=direct_connect_gateway_id,
            vpn_id=vpn_id
        )

        if not association_id:
            return

        aws_utils.dissociate_dxgw_vpn(direct_connect_client=direct_connect_client, association_id=association_id)
