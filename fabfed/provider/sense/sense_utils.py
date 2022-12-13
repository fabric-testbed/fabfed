import json
from types import SimpleNamespace

from sense.client.discover_api import DiscoverApi
from sense.client.profile_api import ProfileApi
from sense.client.workflow_combined_api import WorkflowCombinedApi

from .sense_client import SENSE_CLIENT
from .sense_constants import SENSE_PROFILE_UID
import sys


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


# data.connections[0].terminals[0].uri
# data.connections[0].terminals[1].uri
# data.connections[0].terminals[0].vlan_tag
# data.connections[0].terminals[1].vlan_tag
# data.connections[0].bandwidth.capacity
def create_instance(*, client=None, profile_uuid, alias, edit: dict):
    client = client or SENSE_CLIENT
    workflow_api = WorkflowCombinedApi(req_wrapper=client)
    workflow_api.instance_new()
    intent = {SENSE_PROFILE_UID: profile_uuid, "alias": alias}
    profile_details = describe_profile(client=client, uuid=profile_uuid)

    print(edit, type(edit))

    # sys.exit(1)
    if edit and hasattr(profile_details, "edit"):
        paths = [ns.path for ns in profile_details.edit]

        # data.connections[0].bandwidth.capacity: "500"
        for path in paths:
            print("PATH:", path)

        options = []

        print(edit, type(edit))
        print(edit['connections'])

        # sys.exit(1)
        for i, con in enumerate(edit['connections']):
            print(i, "KKKK:", con, type(con))

            for key, value in con.items():
                if key == "bandwidth":
                    options.append({f"data.connections[{i}].bandwidth.capacity": value})
                elif key == "ip_start":
                    options.append({f"data.connections[{i}].suggest_ip_range[0].start": value})
                elif key == "ip_end":
                    options.append({f"data.connections[{i}].suggest_ip_range[0].end": value})

        # options = []
        #
        # for key, value in edit.items():
        #     if key not in paths:
        #         raise Exception(f"Trying to edit a path that is not editable {key} ")
        #
        #     options.append({key: value})
        #
        query = dict([("ask", "edit"), ("options", options)])
        intent["queries"] = [query]

    print("CREATE INTENT=", json.dumps(intent))


    sys.exit(1)
    response = workflow_api.instance_create(json.dumps(intent))  # service_uuid, intent_uuid, queries, model
    # print(json.dumps(json.loads(response), indent=2))

    temp = json.loads(response)

    if True:
        workflow_api.instance_operate('provision', sync='true')
        status = workflow_api.instance_get_status()
        # print("Status=", status)

    return temp['service_uuid']


# data.connections[0].terminals[0].uri
# data.connections[0].terminals[1].uri
# data.connections[0].terminals[0].vlan_tag
# data.connections[0].terminals[1].vlan_tag
# data.connections[0].bandwidth.capacity
# This complains about transactions
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
    workflow_api.instance_delete(si_uuid=si_uuid)


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
