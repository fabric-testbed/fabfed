import json
from types import SimpleNamespace

from sense.client.discover_api import DiscoverApi
from sense.client.profile_api import ProfileApi
from sense.client.workflow_combined_api import WorkflowCombinedApi

from .sense_client import SENSE_CLIENT
from .sense_constants import *


def describe_profile(*, client, uuid: str):
    client = client or SENSE_CLIENT
    profile_api = ProfileApi(req_wrapper=client)
    profile_details = profile_api.profile_describe(uuid)
    profile_details = json.loads(profile_details, object_hook=lambda dct: SimpleNamespace(**dct))

    if hasattr(profile_details, "edit"):
        from requests import utils

        for ns in profile_details.edit:
            ns.path = utils.unquote(ns.path)
            ns.valid = utils.unquote(ns.valid)

    return profile_details


def populate_options_using_interfaces(options, interfaces, edit_uri_entries):
    if len(interfaces) > len(edit_uri_entries):
        raise Exception("invalid number of interfaces")

    index_used = False

    for interface in interfaces:
        if interface.get(Constants.RES_INDEX):
            index_used = True
            break

    if not index_used:
        for idx, interface in enumerate(interfaces):
            interface[Constants.RES_INDEX] = idx
    else:
        for interface in interfaces:
            if not interface.get(Constants.RES_INDEX):
                raise Exception(f"index missing {interface}")

    for interface in interfaces:
        idx = interface.get(Constants.RES_INDEX)

        if idx < 0 or idx >= len(edit_uri_entries):
            raise Exception("bad interface index")

        name = interface.get(Constants.RES_ID)
        path_prefix = f"data.connections[0].terminals[{idx}]."

        if name:
            path = path_prefix + SENSE_URI
            options.append({path: name})

        vlan_range = interface.get("vlan_range", None)

        if vlan_range:
            vlan_path = path_prefix + SENSE_VLAN_TAG
            vlan_range_str = str(vlan_range).replace(" ", "").replace(",", "-")
            options.append({vlan_path: vlan_range_str[1:-1]})


def create_instance(*, client=None, bandwidth, profile, alias, layer3, peering, interfaces):
    client = client or SENSE_CLIENT
    profiles = list_profiles(client=client)
    profile_uuid = profile

    for p in profiles:
        if p.name == profile:
            profile_uuid = p.uuid
            break

    workflow_api = WorkflowCombinedApi(req_wrapper=client)
    workflow_api.instance_new()
    intent = {SENSE_PROFILE_UID: profile_uuid, "alias": alias}

    profile_details = describe_profile(client=client, uuid=profile_uuid)
    edit_entries = []

    if hasattr(profile_details, "edit"):
        edit_entries = profile_details.edit
        temp_entries = [e.__dict__ for e in edit_entries]
        print("**************** BEGIN EDIT ENTRIES ******************")
        print(json.dumps(temp_entries, indent=2))
        print("**************** END EDIT ENTRIES ******************")

    edit_uri_entries = [e for e in edit_entries if e.path.endswith(SENSE_URI)]
    options = []

    if interfaces:
        populate_options_using_interfaces(options, interfaces, edit_uri_entries)

    if bandwidth:
        options.append({f"data.connections[{0}].bandwidth.capacity": bandwidth})

    if peering:
        for k, v in SENSE_AWS_PEERING_MAPPING.items():
            if peering.attributes.get(k):
                path = "data.gateways[0].connects[0]." + v
                options.append({path: peering.attributes.get(k)})

    if layer3:
        ip_start = layer3.attributes.get(Constants.RES_LAYER3_DHCP_START)

        if ip_start:
            options.append({f"data.connections[{0}].suggest_ip_range[0].start": ip_start})

        ip_end = layer3.attributes.get(Constants.RES_LAYER3_DHCP_END)

        if ip_end:
            options.append({f"data.connections[{0}].suggest_ip_range[0].end": ip_end})

        subnet = layer3.attributes.get(Constants.RES_SUBNET)

        if subnet:
            options.append({f"data.subnets[0].cidr": subnet})

    if options:
        query = dict([("ask", "edit"), ("options", options)])
        intent["queries"] = [query]

    print("**************** BEGIN INTENT ******************")
    print(json.dumps(intent, indent=2))
    print("**************** END INTENT ******************")

    intent = json.dumps(intent)

    # if True:
    #     import sys
    #
    #     sys.exit(1)

    response = workflow_api.instance_create(intent)  # service_uuid, intent_uuid, queries, model
    # TODO HTML BAD ERROR SOMETIMES
    # print(json.dumps(json.loads(response), indent=2))

    temp = json.loads(response)

    if True:
        # TODO Think about async  use max number of tries ...
        workflow_api.instance_operate('provision', sync='true')
        status = workflow_api.instance_get_status()
        print("Status=", status)

    return temp['service_uuid']


'''
Operate failed Returned code 500 with 
  error '{'message': 
  'WFLYJPA0060: Transaction is required to perform this operation 
  (either use a transaction or extended persistence context)', 
    'type': 'net.maxgigapop.mrs.exception.InstanceWorkflowException'}'
'''


def instance_operate(*, client=None, si_uuid):
    # print("OPERATE USING RETURNING:", si_uuid)
    workflow_api = WorkflowCombinedApi(req_wrapper=client)
    workflow_api.instance_operate('provision', si_uuid=si_uuid, sync='true')
    return workflow_api.instance_get_status(si_uuid=si_uuid)


def delete_instance(*, client=None, si_uuid):
    client = client or SENSE_CLIENT
    workflow_api = WorkflowCombinedApi(req_wrapper=client)

    status = workflow_api.instance_get_status(si_uuid=si_uuid)

    if 'error' in status:
        raise Exception("error deleting got " + status)

    if "CREATE - COMPILED" in status or "CREATE - FAILED" in status:
        workflow_api.instance_delete(si_uuid=si_uuid)
        return

    if 'CREATE' not in status and 'REINSTATE' not in status and 'MODIFY' not in status:
        raise ValueError(f"cannot cancel an instance in '{status}' status...")
    elif 'READY' not in status:
        workflow_api.instance_operate('cancel', si_uuid=si_uuid, sync='true', force='true')
    else:
        workflow_api.instance_operate('cancel', si_uuid=si_uuid, sync='true')
    status = workflow_api.instance_get_status(si_uuid=si_uuid)
    print(f'cancel status={status}')
    if 'CANCEL - READY' in status:
        workflow_api.instance_delete(si_uuid=si_uuid)
    else:
        print(f'cancel operation disrupted - instance not deleted - contact admin')


def service_instance_details(*, client=None, si_uuid):
    client = client or SENSE_CLIENT
    discover_api = DiscoverApi(req_wrapper=client)
    response = discover_api.discover_service_instances_get()
    # print(json.dumps(json.loads(response), indent=2))
    response = json.loads(response)
    instances = response['instances']

    for instance in instances:
        temp = SimpleNamespace(**instance)

        if temp.referenceUUID == si_uuid:
            instance['intents'] = []

            for intent in temp.intents:
                intent['json'] = json.loads(intent['json'])
                instance['intents'].append(intent)

            return instance

    raise Exception()


def discover_service_instances(*, client=None):
    client = client or SENSE_CLIENT
    discover_api = DiscoverApi(req_wrapper=client)
    response = discover_api.discover_service_instances_get()
    # print(json.dumps(json.loads(response), indent=2))
    response = json.loads(response)
    instances = response['instances']

    for instance in instances:
        temp = SimpleNamespace(**instance)
        instance['intents'] = []

        for intent in temp.intents:
            intent['json'] = json.loads(intent['json'])
            instance['intents'].append(intent)

    return instances


def list_profiles(*, client=None):
    client = client or SENSE_CLIENT
    profile_api = ProfileApi(req_wrapper=client)
    profiles = profile_api.profile_list()

    profiles = json.loads(profiles, object_hook=lambda dct: SimpleNamespace(**dct))

    for profile in profiles:
        profile.profile_details = describe_profile(client=client, uuid=profile.uuid)

    return profiles


def find_instance_by_alias(*, alias):
    instances = discover_service_instances()

    for instance in instances:
        if instance['alias'] == alias:
            return instance['referenceUUID']

    return None
