
"""
    The sample script that attaches a given VPC to a direct connect gateway
    
    ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
    
    For credentials, create file ~/.aws/credentials, which is like
    [default]
    aws_access_key_id = xxx 
    aws_secret_access_key = xxxx 
    
    author: lzhang9@es.net    July 28, 2023
"""

import time
import boto3
from aws_constants import *

""" create directconnect client """
try:
    directconnect_client = boto3.client(
        'directconnect',
        region_name=REGION,
        #aws_access_key_id=ACCESS_KEY,
        #aws_secret_access_key=SECRET_KEY
        )
except Exception as e:
    print(e)

""" get the direct connect gateway with attached virtual interface """
try:
    response = directconnect_client.describe_direct_connect_gateways()
except Exception as e:
    print(e)
    exit(1)
    
if response['directConnectGateways']:
    direct_connect_gateway_id = response['directConnectGateways'][0]['directConnectGatewayId']
else:
    """ create a direct connetion gatway """
    gateway_name = 'fab-gateway'
    try:
        response = directconnect_client.create_direct_connect_gateway(
            directConnectGatewayName=gateway_name,
            amazonSideAsn=64512
        )
    except Exception as e:
        print(e)
        exit(1)
    
    direct_connect_gateway_id = response['directConnectGateway']['directConnectGatewayId']
    
    """ create virtual interfaces attached to this direct connect gateway """
    try:
        virtual_interface_name = 'fab-vif'
        response = directconnect_client.create_private_virtual_interface(
            connectionId='',
            newPrivateVirtualInterface={
                'virtualInterfaceName': virtual_interface_name,
                'vlan': 100,
                'asn': 53800,
                'mtu': 9001,
                'authKey': BGPKEY,
                'amazonAddress': '192.168.1.1/30',
                'customerAddress': '192.168.1.2/30',
                'addressFamily': 'ipv4',
                'virtualGatewayId': 'string',
                'directConnectGatewayId': direct_connect_gateway_id,
                'tags': [
                    {
                        'key': 'string',
                        'value': 'string'
                    },
                ],
                'enableSiteLink': False
            }
        )
    except Exception as e:
        print(e)
        exit(1)
            

""" provided a VPC and assicated VPN """
vpn_id = 'vgw-0eca5ca355af8a9dc'
try:
    response = directconnect_client.describe_virtual_gateways()
    if vpn_id in [ vpn['virtualGatewayId'] for vpn in response['virtualGateways'] ]:
        print(f'vpn {vpn_id} is found')
    else:
        print(f'vpn {vpn_id} is not found')
        raise
except Exception as e:
    print(e)
    exit(1)

""" associate direct connect gateway to virtual private gateway """
try:
    for i in range(RETRY):
        response = directconnect_client.create_direct_connect_gateway_association(
            directConnectGatewayId=direct_connect_gateway_id,
            virtualGatewayId=vpn_id
        )
        state = response['directConnectGatewayAssociation']['associationState']
        print(f'association state {state}')
        if state != 'associated':
            time.sleep(30) 
except Exception as e:
    print(e)
    exit(1)

assocication_id = response['directConnectGatewayAssociation']['associationId'] 
print(f"VPC associated with Direct Connect Connection: association_id={assocication_id}.")

""" take 1 min break """
time.sleep(60)

""" dissociate direct connect gateway to virtual private gateway """
try:
    for i in range(RETRY):
        response = directconnect_client.delete_direct_connect_gateway_association(
            associationId=assocication_id
        )
        print(response['associationState'])
        if response['associationState'] != 'associated':
            time.sleep(20) 
except Exception as e:
    print(e)

print(f"VPC dissociated with Direct Connect Connection: association_id={assocication_id}.")

