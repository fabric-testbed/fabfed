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
        self.vif_details = {}

    @property
    def gateway_name(self):
        return f'{self._provider.name}-fab-direct-connect-gateway'

    @property
    def vpn_gateway_name(self):
        return f'{self._provider.name}-fab-vpn-gateway'

    @property
    def vif_name(self):
        return f'{self._provider.name}-fab-vif'

    @property
    def connection_name(self):
        return f'{self._provider.name}-{self.peering.attributes.get(Constants.RES_CLOUD_ACCOUNT)}'

    def create(self):
        region = self.peering.attributes.get(Constants.RES_CLOUD_REGION)
        ec2_client = aws_utils.create_ec2_client(region=region,
                                                 access_key=self._provider.access_key,
                                                 secret_key=self._provider.secret_key)
        self.vpc_id = self.peering.attributes.get(Constants.RES_CLOUD_VPC)

        if not self.vpc_id:
            raise AwsException(f"must supply vpc id using peering attribute: {Constants.RES_CLOUD_VPC}")

        if not aws_utils.is_vpc_available(ec2_client=ec2_client, vpc_id=self.vpc_id):
            raise AwsException(f"Vpc is not available:{self.vpc_id}")

        logger.info(f'Vpc {self.vpc_id} is available')

        direct_connect_client = aws_utils.create_direct_connect_client(
            region=region,
            access_key=self._provider.access_key,
            secret_key=self._provider.secret_key)

        connection_id, vlan = aws_utils.find_available_dx_connection(
            direct_connect_client=direct_connect_client,
            name=self.connection_name)

        logger.info(f'connection {self.connection_name} is available:connection_id={connection_id}')
        self.vpn_id = aws_utils.find_attached_vpn_gateway(ec2_client=ec2_client, vpc_id=self.vpc_id)
        amazon_asn = self.peering.attributes.get(Constants.RES_REMOTE_ASN)

        if not self.vpn_id:
            logger.info(f'Creating and attaching vpn gateway: name={self.vpn_gateway_name}:vpc={self.vpc_id}')
            logger.info(f'Creating and attaching vpn gateway: name={self.vpn_gateway_name}:vpc={self.vpc_id}')
            self.vpn_id = aws_utils.create_vpn_gateway(
                ec2_client=ec2_client,
                name=self.vpn_gateway_name,
                amazon_asn=amazon_asn)
            aws_utils.attach_vpn_gateway(ec2_client=ec2_client, vpn_id=self.vpn_id, vpc_id=self.vpc_id)
        else:
            logger.info(f'Found attached vpn gateway {self.vpn_id}')

        self.direct_connect_gateway_id = aws_utils.create_direct_connect_gateway(
            direct_connect_client=direct_connect_client,
            gateway_name=self.gateway_name,
            amazon_asn=amazon_asn)

        self.vif_details = aws_utils.create_private_virtual_interface(
            direct_connect_client=direct_connect_client,
            direct_connect_gateway_id=self.direct_connect_gateway_id,
            connection_id=connection_id,
            vlan=vlan,
            peering=self.peering,
            vif_name=f"{self.vif_name}")

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
        vpn_id = aws_utils.find_attached_vpn_gateway(ec2_client=ec2_client, vpc_id=vpc_id)

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
