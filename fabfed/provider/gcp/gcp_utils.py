
"""
    The sample script that attaches a given VPC to an interconnect vlan attachment
    
    ref: https://cloud.google.com/python/docs/reference/compute/latest
    
    For credentials, create service account within the console and download to
    the file ~/.gcp/service-account-file.json
    
    For details,
    https://cloud.google.com/docs/authentication/provide-credentials-adc
    
    
    author: lzhang9@es.net    July 28, 2023
"""
import sys
import time
from google.cloud import compute_v1
from google.cloud.compute_v1.types import (
    Router, 
    RouterBgp, 
    InsertRouterRequest,
    InterconnectAttachment,
    RouterStatus
    )
from google.oauth2 import service_account
from gcp_constants import *

def check_operation_result(project, region, operation_name):
    # Check the result
    # operation_name = response.name
    client = compute_v1.RegionOperationsClient()
    request = compute_v1.GetRegionOperationRequest(
        operation=operation_name,
        project=project,
        region=region,
    )

    while True:
        # Make the request
        response = client.get(request=request)
        if str(response.status) == 'Status.DONE':
            break    
        time.sleep(5)  # Wait for 5 seconds before checking the status again.
    
def create_router(project, region, router_name, network, bgp_asn):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    compute_client = compute_v1.RoutersClient(
        credentials=credentials
        )

    router_resource = Router(
        name=router_name,
        network=f'projects/{project}/global/networks/{network}',
        bgp=RouterBgp(asn=bgp_asn)  # Replace bgp_asn with your desired BGP ASN.
    )
    
    # Initialize request argument(s)        
    request = InsertRouterRequest(
        project=project,
        region=region,
        router_resource=router_resource
    )

    try:
        response = compute_client.insert(request=request)
        check_operation_result(project, region, response.name)
        
        print(f"Router '{router_name}' created successfully.")
        
    except Exception as e:
        print(e)
        
def delete_router(project, region, router_name):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    client = compute_v1.RoutersClient(credentials=credentials)

    # Initialize request argument(s)
    request = compute_v1.DeleteRouterRequest(
        project=project,
        region=region,
        router=router_name,
    )

    # Make the request
    response = client.delete(request=request)
    check_operation_result(project, region, response.name)

    # Handle the response
    print(f"Router '{router_name}' deleted successfully.")

def create_interconnect_vlan_attachment(project, region, router_name, interconnect_attachment_name):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    compute_client = compute_v1.InterconnectAttachmentsClient(
        credentials=credentials
        )

    interconnect_attachment_resource = InterconnectAttachment(
        name=f'{interconnect_attachment_name}',
        admin_enabled=True,
        encryption=None,
        router=f'projects/{project}/regions/{region}/routers/{router_name}',
        type_= 'PARTNER'
    )
    
    # Initialize request argument(s)    
    request = compute_v1.InsertInterconnectAttachmentRequest(
        project=project,
        region=region,
        interconnect_attachment_resource=interconnect_attachment_resource
    )

    response = compute_client.insert(request=request)
    check_operation_result(project, region, response.name)

    print(f"Interconnect VLAN Attachment '{interconnect_attachment_name}' created successfully.")
    

def delete_interconnect_vlan_attachment(project, region, interconnect_attachment_name):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    client = compute_v1.InterconnectAttachmentsClient(credentials=credentials)

    # Initialize request argument(s)
    request = compute_v1.DeleteInterconnectAttachmentRequest(
        interconnect_attachment=interconnect_attachment_name,
        project=project,
        region=region,
    )

    # Make the request
    response = client.delete(request=request)
    check_operation_result(project, region, response.name)

    # Handle the response
    print(f"Interconnect VLAN Attachment '{interconnect_attachment_name}' deleted successfully.")
    
def list_interconnect_vlan_attachment(project, region):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    client = compute_v1.InterconnectAttachmentsClient(credentials=credentials)

    # Initialize request argument(s)
    request = compute_v1.ListInterconnectAttachmentsRequest(
        project=project,
        region=region,
    )

    # Make the request
    page_result = client.list(request=request)

    # Handle the response
    for response in page_result:
        print(response)

def list_interconnect(project):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_KEY_PATH)
    
    # Create a client
    client = compute_v1.InterconnectsClient(credentials=credentials)

    # Initialize request argument(s)
    request = compute_v1.ListInterconnectsRequest(
        project=project,
    )

    # Make the request
    page_result = client.list(request=request)

    # Handle the response
    for response in page_result:
        print(response)

"""

    Sample script

"""
def sample():
    project = 'fabfed'
    region = 'us-east4'
    vpc='vpc-69acc1d9-8c24-47cd-90b8-33be57167dbf'
    
    # list_interconnect(project)
    # list_interconnect_vlan_attachment(project=project, region=region)
    
    """ create router """    
    router_name = 'fab-router'
    google_asn = 16550
    
    try:
        create_router(
            project=project,
            region=region,
            router_name=router_name,
            network=vpc,
            bgp_asn=google_asn)
    except Exception as e:
        print(e)
    
    """ create an interconnect client """
    interconnect_attachment_name = 'fab-vlan-attach'
    try:
        create_interconnect_vlan_attachment(
            project=project,
            region=region,
            router_name=router_name,
            interconnect_attachment_name=interconnect_attachment_name,
            )
    except Exception as e:
        print(e)
    
    """ take 1 min break """
    time.sleep(10)
    
    """ delete the interconnect vlan attachment """
    try:
        delete_interconnect_vlan_attachment(
            project=project,
            region=region,
            interconnect_attachment_name=interconnect_attachment_name
            )
    except Exception as e:
        print(e)
    
    """delete the router """
    try:
        delete_router(
            project=project,
            region=region,
            router_name=router_name
            )
    except Exception as e:
        print(e)
        
    print("Program terminated successfully.")
    
if __name__ == "__main__":
    sys.exit(sample())