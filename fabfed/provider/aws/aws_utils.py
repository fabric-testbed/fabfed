import time

import boto3

from fabfed.util.utils import get_logger
from .aws_constants import *
from .aws_exceptions import AwsException

logger = get_logger()


def create_ec2_client(*, region: str, access_key: str, secret_key: str):
    ec2_client = boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    return ec2_client


def is_vpc_available(*, ec2_client, vpc_id: str):
    response = ec2_client.describe_vpcs(VpcIds=[vpc_id])

    if response and isinstance(response, dict) and 'Vpcs' in response:
        vpc = next(iter(response['Vpcs']), None)

        if vpc:
            state = vpc['State']

            if state == 'available':
                return True

            logger.warning(f'found vpc {vpc_id} with state={state}')
        else:
            raise AwsException(f"Vpc not found {vpc_id}")

    return False


def find_attached_vpn_gateway(*, ec2_client, vpc_id: str):
    response = ec2_client.describe_vpn_gateways()

    if isinstance(response, dict) and 'VpnGateways' in response:
        for gw in response['VpnGateways']:
            attachments = gw['VpcAttachments']
            attachment = next(filter(lambda a: a['VpcId'] == vpc_id and a['State'] == 'attached', attachments), None)

            if attachment:
                return gw['VpnGatewayId']

    return None


def find_vpn_gateway(*, ec2_client, vpn_id: str):
    response = ec2_client.describe_vpn_gateways()

    if response and isinstance(response, dict) and 'VpnGateways' in response:
        for gw in response['VpnGateways']:
            if gw['VpnGatewayId'] == vpn_id:
                return gw

    return None


def attach_vpn_gateway(*, ec2_client, vpn_id: str, vpc_id: str):
    vpn_gateway = find_vpn_gateway(ec2_client=ec2_client, vpn_id=vpn_id)
    attachments = vpn_gateway['VpcAttachments']

    for attachment in attachments:
        if attachment['VpcId'] == vpc_id:
            raise Exception(f"Already attached ...{attachment['State']}")

    response = ec2_client.attach_vpn_gateway(
        VpcId=vpc_id,
        VpnGatewayId=vpn_id
    )

    attachment = response['VpcAttachment']
    state = attachment['State']

    if state == 'attached':
        return

    for i in range(RETRY):
        vpn_gateway = find_vpn_gateway(ec2_client=ec2_client, vpn_id=vpn_id)
        attachments = vpn_gateway['VpcAttachments']

        for attachment in attachments:
            if attachment['VpcId'] == vpc_id:
                state = attachment['State']
                break

        if state == 'attached':
            return

        time.sleep(20)

    raise AwsException(f"Timed out on attaching vpn_gateway: state={state}")


def create_vpn_gateway(*, ec2_client, name: str, amazon_asn: int):
    response = ec2_client.create_vpn_gateway(
        Type='ipsec.1',
        TagSpecifications=[
            {
                'ResourceType': 'vpn-gateway',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ],
        AmazonSideAsn=amazon_asn
    )

    vpn_gateway = response['VpnGateway']
    vpn_id = vpn_gateway['VpnGatewayId']
    state = vpn_gateway['State']

    if state == 'available':
        return vpn_id

    for i in range(RETRY):
        vpn_gateway = find_vpn_gateway(ec2_client=ec2_client, vpn_id=vpn_id)
        state = vpn_gateway['State']

        if state == 'available':
            return vpn_id

        time.sleep(20)

    raise AwsException(f"Timed out on creating vpn_gateway: state={state}")


def create_direct_connect_client(*, region: str, access_key: str, secret_key: str):
    direct_connect_client = boto3.client(
        'directconnect',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    return direct_connect_client


def find_direct_connect_gateway_id(*, direct_connect_client, gateway_name: str):
    response = direct_connect_client.describe_direct_connect_gateways()

    if response and isinstance(response, dict) and 'directConnectGateways' in response:
        for gw in response['directConnectGateways']:
            if gw['directConnectGatewayName'] == gateway_name:
                return gw['directConnectGatewayId']

    return None


def create_direct_connect_gateway(*, direct_connect_client, gateway_name: str, amazon_asn: int):
    response = direct_connect_client.describe_direct_connect_gateways()
    direct_connect_gateway_id = None

    if response and isinstance(response, dict) and 'directConnectGateways' in response:
        for gw in response['directConnectGateways']:
            if gw['directConnectGatewayName'] == gateway_name:
                logger.info(f"Found directConnectGateway {gw}")
                direct_connect_gateway_id = gw['directConnectGatewayId']
                break

    if not direct_connect_gateway_id:
        response = direct_connect_client.create_direct_connect_gateway(
            directConnectGatewayName=gateway_name,
            amazonSideAsn=amazon_asn
        )

        logger.info(f"Created directConnectGateway {response}")
        direct_connect_gateway_id = response['directConnectGateway']['directConnectGatewayId']

    return direct_connect_gateway_id


def create_private_virtual_interface(*, direct_connect_client, direct_connect_gateway_id: str, vif_name: str):
    response = direct_connect_client.describe_virtual_interfaces()
    details = {}

    if isinstance(response, dict) and 'virtualInterfaces' in response:
        for vif in response['virtualInterfaces']:
            if vif['directConnectGatewayId'] == direct_connect_gateway_id and vif['virtualInterfaceName'] == vif_name:
                logger.info(f"Found existing private virtual interface {vif_name}")

                for k in VIF_DETAILS:
                    details[k] = vif[k]

                break

    if not details:
        logger.info(f"Creating private virtual interface {vif_name}")
        vif = direct_connect_client.create_private_virtual_interface(
            connectionId='dxcon-fgz7lrnh',
            newPrivateVirtualInterface={
                'virtualInterfaceName': vif_name,
                'vlan': 2,
                'asn': 53800,
                'mtu': 9001,
                'authKey': BGPKEY,
                'amazonAddress': '192.168.1.1/30',
                'customerAddress': '192.168.1.2/30',
                'addressFamily': 'ipv4',
                'directConnectGatewayId': direct_connect_gateway_id,
                'enableSiteLink': False
            }
        )

        for k in VIF_DETAILS:
            details[k] = vif[k]

    for i in range(RETRY):
        response = direct_connect_client.describe_virtual_interfaces()
        vif = next(filter(lambda v: v[VIF_ID] == details[VIF_ID], response['virtualInterfaces']))
        state = vif[VIF_STATE]

        if state == 'down' or state == 'available':
            logger.info(f"TODO: Breaking private virtual interface {vif_name}:state={state}")  # TODO fix the down state
            break

        time.sleep(20)

    return details


def find_association_dxgw_vpn(*, direct_connect_client, direct_connect_gateway_id: str, vpn_id: str):
    response = direct_connect_client.describe_direct_connect_gateway_associations(
        virtualGatewayId=vpn_id,
        directConnectGatewayId=direct_connect_gateway_id,
    )

    if response and isinstance(response, dict) and 'directConnectGatewayAssociations' in response:
        associations = response['directConnectGatewayAssociations']

        if associations:
            return associations[0]

    return None


def find_association_dxgw_vpn_id(*, direct_connect_client, direct_connect_gateway_id: str, vpn_id: str):
    association = find_association_dxgw_vpn(
        direct_connect_client=direct_connect_client,
        direct_connect_gateway_id=direct_connect_gateway_id,
        vpn_id=vpn_id
    )

    if association:
        return association['associationId']

    return None


def associate_dxgw_vpn(direct_connect_client, direct_connect_gateway_id, vpn_id: str):
    association = find_association_dxgw_vpn(
        direct_connect_client=direct_connect_client,
        direct_connect_gateway_id=direct_connect_gateway_id,
        vpn_id=vpn_id
    )

    if association and association['associationState'] == 'associated':
        return association['associationId']

    response = direct_connect_client.create_direct_connect_gateway_association(
        directConnectGatewayId=direct_connect_gateway_id,
        virtualGatewayId=vpn_id
    )

    association = response['directConnectGatewayAssociation']
    state = association['associationState']

    if state == 'associated':
        return association['associationId']

    for i in range(RETRY):
        association = find_association_dxgw_vpn(
            direct_connect_client=direct_connect_client,
            direct_connect_gateway_id=direct_connect_gateway_id,
            vpn_id=vpn_id
        )

        logger.info(f'checking if association state is associated:{association}')
        state = association['associationState']

        if state == 'associated':
            return association['associationId']

        time.sleep(20)

    raise AwsException(f"Timed out on creating direct_connect_gateway_association: state={state}")


def dissociate_dxgw_vpn(*, direct_connect_client, association_id: str):
    response = direct_connect_client.delete_direct_connect_gateway_association(
        associationId=association_id
    )

    association = response['directConnectGatewayAssociation']

    if not association or not isinstance(association, dict) or 'associationState' not in association:
        return

    state = association['associationState']

    if state == 'disassociated':
        return

    direct_connect_gateway_id = association['directConnectGatewayId']
    vpn_id = association['virtualGatewayId']

    for i in range(RETRY):
        association = find_association_dxgw_vpn(
            direct_connect_client=direct_connect_client,
            direct_connect_gateway_id=direct_connect_gateway_id,
            vpn_id=vpn_id
        )

        if not association or not isinstance(association, dict) or 'associationState' not in association:
            return

        logger.info(f'checking if association state is disassociated: {association}')
        state = association['associationState']

        if state == 'disassociated':
            return

        time.sleep(20)

    raise AwsException(f"Timed out on deleting direct_connect_gateway_association:id={association_id}:state={state}")
