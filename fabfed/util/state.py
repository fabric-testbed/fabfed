from fabfed.model.state import ProviderState
from fabfed.util.utils import get_base_dir
from typing import List

import json


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        else:
            return obj.__dict__


def dump_resources(*, resources, to_json: bool, summary: bool = False):
    import sys

    if summary:
        summaries = []
        from collections import namedtuple
        from fabfed.util.constants import Constants

        ResourceSummary = namedtuple("ResourceSummary", "label attributes")

        for resource in resources:
            resource_dict = resource.attributes.copy()
            del_attrs = [Constants.EXTERNAL_DEPENDENCIES,
                         Constants.RESOLVED_EXTERNAL_DEPENDENCIES,
                         Constants.INTERNAL_DEPENDENCIES,
                         Constants.RESOLVED_INTERNAL_DEPENDENCIES,
                         Constants.SAVED_STATES]

            for attr in del_attrs:
                del resource_dict[attr]

            stringify_attrs = [Constants.PROVIDER,
                               Constants.RES_INTERFACES,
                               Constants.RES_NODES,
                               Constants.RES_NETWORK,
                               Constants.RES_STITCH_INTERFACE,
                               Constants.NETWORK_STITCH_WITH,
                               Constants.RES_LAYER3,
                               Constants.RES_PEER_LAYER3,
                               Constants.RES_PEERING
                               ]

            for attr in stringify_attrs:
                if attr in resource_dict:
                    resource_dict[attr] = str(resource_dict[attr])

            label = resource_dict.pop(Constants.LABEL)
            summaries.append(ResourceSummary(label=label, attributes=resource_dict))

        resources = summaries

    if to_json:
        import json

        sys.stdout.write(json.dumps(resources, cls=SetEncoder, indent=3))
    else:
        import yaml
        from fabfed.model.state import get_dumper

        sys.stdout.write(yaml.dump(resources, Dumper=get_dumper(), default_flow_style=False, sort_keys=False))


def dump_states(states, to_json: bool, summary: bool = False):
    import sys
    from fabfed.model.state import get_dumper

    temp = []
    if summary:
        for provider_state in states:
            for node_state in provider_state.node_states:
                attributes = dict()
                props = ['mgmt_ip', 'user', 'site', 'state', 'id', "dataplane_ipv4", "dataplane_ipv6", 'keyfile', 'jump_keyfile']

                for prop in props:
                    if prop in node_state.attributes:
                        attributes[prop] = node_state.attributes[prop]

                node_state.attributes = attributes
                temp.append(node_state)

            for network_state in provider_state.network_states:
                attributes = dict()
                props = ['id', 'name', 'interface', 'site', 'state', 'profile', "dtn", 'layer3']

                for prop in props:
                    if prop in network_state.attributes:
                        attributes[prop] = network_state.attributes[prop]

                network_state.attributes = attributes
                temp.append(network_state)

            for service_state in provider_state.service_states:
                attributes = dict()
                props = ['name', 'image', 'controller_host', 'controller_web', 'controller_ssh_tunnel_cmd']

                for prop in props:
                    if prop in service_state.attributes:
                        attributes[prop] = service_state.attributes[prop]

                service_state.attributes = attributes
                temp.append(service_state)

        states = temp

    if to_json:
        import json

        sys.stdout.write(json.dumps(states, cls=SetEncoder, indent=3))
    else:
        import yaml

        sys.stdout.write(
            yaml.dump(states, Dumper=get_dumper(), width=float("inf"), default_flow_style=False, sort_keys=False))


def load_meta_data(friendly_name: str, attr=None):
    import yaml
    import os
    from fabfed.model.state import get_loader

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '_meta.yml')

    if os.path.exists(file_path):
        with open(file_path, 'r') as stream:
            try:
                ret = yaml.load(stream, Loader=get_loader())

                if ret is not None:
                    return ret.get(attr) if attr else ret
            except Exception as e:
                from fabfed.exceptions import StateException

                raise StateException(f'Exception while loading state at {file_path}:{e}')

    return None if attr else dict()


def load_states(friendly_name) -> List[ProviderState]:
    import yaml
    import os
    from fabfed.model.state import get_loader

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '.yml')

    if os.path.exists(file_path):
        with open(file_path, 'r') as stream:
            try:
                ret = yaml.load(stream, Loader=get_loader())

                if ret is not None:
                    return ret
            except Exception as e:
                from fabfed.exceptions import StateException

                raise StateException(f'Exception while loading state at {file_path}:{e}')

    return []


def save_meta_data(meta_data: dict, friendly_name: str):
    import yaml
    import os
    from fabfed.model.state import get_dumper

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '_meta.yml')

    with open(file_path, "w") as stream:
        try:
            stream.write(yaml.dump(meta_data, Dumper=get_dumper()))
        except Exception as e:
            from fabfed.exceptions import StateException

            raise StateException(f'Exception while saving state at temp file {file_path}:{e}')


def save_states(states: List[ProviderState], friendly_name):
    import yaml
    import os
    from fabfed.model.state import get_dumper

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '.yml')
    temp_file_path = file_path + ".temp"

    with open(temp_file_path, "w") as stream:
        try:
            stream.write(yaml.dump(states, Dumper=get_dumper(), default_flow_style=False, sort_keys=False))
        except Exception as e:
            from fabfed.exceptions import StateException

            raise StateException(f'Exception while saving state at temp file {temp_file_path}:{e}')

    import shutil

    shutil.move(temp_file_path, file_path)


def load_sessions():
    from pathlib import Path
    import os

    base_dir = os.path.join(str(Path.home()), '.fabfed', 'sessions')
    os.makedirs(base_dir, exist_ok=True)
    sessions = os.listdir(base_dir)
    return sessions


def destroy_session(friendly_name: str):
    import shutil

    dir_path = get_base_dir(friendly_name)
    shutil.rmtree(dir_path)
