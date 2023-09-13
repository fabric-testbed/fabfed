import time

from google.cloud import compute_v1
from google.cloud.compute_v1.types import (
    Router,
    RouterBgp,
    InsertRouterRequest,
    InterconnectAttachment,
)
from google.oauth2 import service_account

from fabfed.util.utils import get_logger

logger = get_logger()


def find_vpc(*, service_key_path, project, vpc):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    network_client = compute_v1.NetworksClient(credentials=credentials)
    request = compute_v1.GetNetworkRequest(project=project, network=vpc)

    from google.api_core.exceptions import NotFound

    try:
        return network_client.get(request=request)
    except NotFound:
        return None


def check_operation_result(*, credentials, project, region, operation_name):
    client = compute_v1.RegionOperationsClient(credentials=credentials)
    request = compute_v1.GetRegionOperationRequest(
        operation=operation_name,
        project=project,
        region=region,
    )

    while True:
        response = client.get(request=request)

        if str(response.status) == 'Status.DONE':
            break

        logger.info(f"Status={str(response.status)}")
        time.sleep(5)


def find_router(*, service_key_path, project, region, router_name):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    compute_client = compute_v1.RoutersClient(credentials=credentials)
    request = compute_v1.GetRouterRequest(
                    project=project,
                    region=region,
                    router=router_name
    )

    from google.api_core.exceptions import NotFound

    try:
        return compute_client.get(request=request)
    except NotFound:
        return None


def create_router(*, service_key_path, project, region, router_name, vpc, bgp_asn):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    compute_client = compute_v1.RoutersClient(credentials=credentials)
    router_resource = Router(
        name=router_name,
        network=f'projects/{project}/global/networks/{vpc}',
        bgp=RouterBgp(asn=bgp_asn)
    )
    request = InsertRouterRequest(
        project=project,
        region=region,
        router_resource=router_resource
    )
    response = compute_client.insert(request=request)
    logger.info(f'Response={response}')
    check_operation_result(credentials=credentials, project=project, region=region, operation_name=response.name)
    logger.info(f'Router {router_name} created successfully.')


def delete_router(*, service_key_path, project, region, router_name):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    client = compute_v1.RoutersClient(credentials=credentials)
    request = compute_v1.DeleteRouterRequest(
        project=project,
        region=region,
        router=router_name,
    )
    
    response = client.delete(request=request)
    check_operation_result(credentials=credentials, project=project,
                           region=region, operation_name=response.name)
    logger.info(f"Router '{router_name}' deleted successfully.")


def find_interconnect_attachment(*, service_key_path, project, region, attachment_name):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    compute_client = compute_v1.InterconnectAttachmentsClient(credentials=credentials)

    request = compute_v1.GetInterconnectAttachmentRequest(
                    project=project,
                    region=region,
                    interconnect_attachment=attachment_name
    )

    from google.api_core.exceptions import NotFound

    try:
        return compute_client.get(request=request)
    except NotFound:
        return None


def create_interconnect_attachment(*, service_key_path, project, region, router_name, attachment_name):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    compute_client = compute_v1.InterconnectAttachmentsClient(credentials=credentials)
    interconnect_attachment_resource = InterconnectAttachment(
        name=f'{attachment_name}',
        admin_enabled=True,
        encryption=None,
        router=f'projects/{project}/regions/{region}/routers/{router_name}',
        type_='PARTNER'
    )
    
    request = compute_v1.InsertInterconnectAttachmentRequest(
        project=project,
        region=region,
        interconnect_attachment_resource=interconnect_attachment_resource
    )
    response = compute_client.insert(request=request)
    check_operation_result(credentials=credentials, project=project, region=region, operation_name=response.name)
    logger.info(f"Interconnect VLAN Attachment '{attachment_name}' created successfully.")


def delete_interconnect_vlan_attachment(*, service_key_path, project, region, attachment_name):
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    client = compute_v1.InterconnectAttachmentsClient(credentials=credentials)
    request = compute_v1.DeleteInterconnectAttachmentRequest(
        project=project,
        region=region,
        interconnect_attachment=attachment_name,
    )

    response = client.delete(request=request)
    check_operation_result(credentials=credentials, project=project, region=region, operation_name=response.name)
    logger.info(f"Interconnect VLAN Attachment '{attachment_name}' deleted successfully.")
