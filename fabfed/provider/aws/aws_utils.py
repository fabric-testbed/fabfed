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


def find_vpn_gateway_id(*, ec2_client, vpc_id: str):
    response = ec2_client.describe_vpn_gateways()

    if response and isinstance(response, dict) and 'VpnGateways' in response:
        for gw in response['VpnGateways']:
            attachments = gw['VpcAttachments']

            for attachment in attachments:
                if attachment['VpcId'] == vpc_id:
                    return gw['VpnGatewayId']

    return None


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


def create_direct_connect_gateway_id(*, direct_connect_client, gateway_name: str, vif_name: str):
    response = direct_connect_client.describe_direct_connect_gateways()

    direct_connect_gateway_id = None

    if response and isinstance(response, dict) and 'directConnectGateways' in response:
        for gw in response['directConnectGateways']:
            if gw['directConnectGatewayName'] == gateway_name:
                direct_connect_gateway_id = gw['directConnectGatewayId']
                break

    if not direct_connect_gateway_id:
        response = direct_connect_client.create_direct_connect_gateway(
            directConnectGatewayName=gateway_name,
            amazonSideAsn=64512
        )

        direct_connect_gateway_id = response['directConnectGateway']['directConnectGatewayId']

    response = direct_connect_client.describe_virtual_interfaces()
    found = False

    if response and isinstance(response, dict) and 'virtualInterfaces' in response:
        for vif in response['virtualInterfaces']:
            if vif['directConnectGatewayId'] == direct_connect_gateway_id and vif['virtualInterfaceName'] == vif_name:
                found = True

    if not found:
        direct_connect_client.create_private_virtual_interface(
            connectionId='',
            newPrivateVirtualInterface={
                'virtualInterfaceName': vif_name,
                'vlan': 100,
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

    return direct_connect_gateway_id


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
