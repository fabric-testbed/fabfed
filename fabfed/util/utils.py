import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from typing import List

from fabfed.model.state import ProviderState
from fabfed.util.constants import Constants


def create_parser(usage='%(prog)s [options]',
                  description='',
                  formatter_class=None):
    formatter_class = formatter_class or RawDescriptionHelpFormatter
    return ArgumentParser(usage=usage, description=description, formatter_class=formatter_class)


def build_parser(*, manage_workflow, manage_sessions):
    description = (
        'Fabfed'
        '\n'
        '\n'
        'Examples:'
        '\n'
        "      fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -validate"
        '\n'
        "      fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -validate"
        '\n'
    )

    parser = create_parser(description=description)
    subparsers = parser.add_subparsers()
    workflow_parser = subparsers.add_parser('workflow', help='Manage fabfed workflows')
    workflow_parser.add_argument('-c', '--config', type=str, default='', help='yaml config file', required=False)
    workflow_parser.add_argument('-v', '--var-file', type=str, default='', help='yaml variable file', required=False)
    workflow_parser.add_argument('-s', '--session', type=str, default='', help='friendly session name', required=False)
    workflow_parser.add_argument('-validate', action='store_true', default=False, help='validates config file ')
    workflow_parser.add_argument('-apply', action='store_true', default=False, help='create resources')
    workflow_parser.add_argument('-plan', action='store_true', default=False, help='shows plan')
    workflow_parser.add_argument('-show', action='store_true', default=False, help='display resources')
    workflow_parser.add_argument('-json', action='store_true', default=False, help='use json for show and plan')
    workflow_parser.add_argument('-destroy', action='store_true', default=False, help='delete resources')
    workflow_parser.set_defaults(dispatch_func=manage_workflow)

    sessions_parser = subparsers.add_parser('sessions', help='Manage fabfed sessions ')
    sessions_parser.add_argument('-show', action='store_true', default=False, help='display sessions')
    sessions_parser.add_argument('-json', action='store_true', default=False, help='use json format')
    sessions_parser.set_defaults(dispatch_func=manage_sessions)
    return parser


def init_looger(log_level=logging.INFO):
    from logging.handlers import RotatingFileHandler

    log_config = {'log-file': './fabfed.log',
                  'log-level': 'INFO',
                  'log-retain': 5,
                  'log-size': 5000000,
                  'logger': 'fabfed'}

    logger = logging.getLogger(str(log_config.get(Constants.PROPERTY_CONF_LOGGER, __name__)))

    log_level = log_config.get(Constants.PROPERTY_CONF_LOG_LEVEL, log_level)
    logger.setLevel(log_level)

    file_handler = RotatingFileHandler(log_config.get(Constants.PROPERTY_CONF_LOG_FILE),
                                       backupCount=int(log_config.get(Constants.PROPERTY_CONF_LOG_RETAIN)),
                                       maxBytes=int(log_config.get(Constants.PROPERTY_CONF_LOG_SIZE)))
    # noinspection PyArgumentList
    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(), file_handler], force=True)
    return logger


def load_yaml_from_file(file_name):
    import yaml
    from pathlib import Path

    path = Path(file_name).expanduser().absolute()

    with open(str(path), 'r') as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)


def load_vars(var_file):
    import yaml

    with open(var_file, 'r') as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)


def get_base_dir():
    from pathlib import Path
    import os

    base_dir = os.path.join(str(Path.home()), '.fabfed', 'sessions')
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def dump_sessions(to_json: bool):
    import os
    import sys

    base_dir = get_base_dir()
    sessions = [s[:-4] for s in os.listdir(base_dir) if s.endswith('.yml')]

    if to_json:
        import json

        sys.stdout.write(json.dumps(sessions, default=lambda o: o.__dict__, indent=3))
    else:
        import yaml

        sys.stdout.write(yaml.dump(sessions))

    return sessions


def dump_states(states: List[ProviderState], to_json: bool):
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

    file_path = os.path.join(get_base_dir(), friendly_name + '.yml')

    with open(file_path, 'r') as stream:
        return yaml.load(stream, Loader=get_loader())


def save_states(states: List[ProviderState], friendly_name):
    import yaml
    import os
    from fabfed.model.state import get_dumper

    file_path = os.path.join(get_base_dir(), friendly_name + '.yml')

    with open(file_path, "w") as stream:
        stream.write(yaml.dump(states, Dumper=get_dumper()))
