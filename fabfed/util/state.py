from fabfed.model.state import ProviderState
from fabfed.util.utils import get_base_dir
from typing import List


def dump_states(states, to_json: bool):
    import sys
    from fabfed.model.state import get_dumper

    if to_json:
        import json

        sys.stdout.write(json.dumps(states, default=lambda o: o.__dict__, indent=3))
    else:
        import yaml

        sys.stdout.write(yaml.dump(states, Dumper=get_dumper()))


def load_states(friendly_name) -> List[ProviderState]:
    import yaml
    import os
    from fabfed.model.state import get_loader

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '.yml')

    if os.path.exists(file_path):
        with open(file_path, 'r') as stream:
            try:
                return yaml.load(stream, Loader=get_loader())
            except Exception as e:
                from fabfed.exceptions import StateException

                raise StateException(f'Exception while loading state at {file_path}:{e}')

    return []


def save_states(states: List[ProviderState], friendly_name):
    import yaml
    import os
    from fabfed.model.state import get_dumper

    file_path = os.path.join(get_base_dir(friendly_name), friendly_name + '.yml')

    with open(file_path, "w") as stream:
        try:
            stream.write(yaml.dump(states, Dumper=get_dumper()))
        except Exception as e:
            from fabfed.exceptions import StateException

            raise StateException(f'Exception while saving state at {file_path}:{e}')
