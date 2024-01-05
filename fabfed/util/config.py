from .parser import Parser
from .config_models import ResourceConfig, ProviderConfig
from typing import List


class WorkflowConfig:
    def __init__(self, *, dir_path=None, content=None, var_dict=None):
        import time

        start = time.time()
        self.providers, self.resources = Parser.parse(dir_path=dir_path, content=content, var_dict=var_dict)
        end = time.time()
        self.parse_and_validate_config_duration = end - start

    def get_provider_config(self) -> List[ProviderConfig]:
        return self.providers

    def get_resource_configs(self) -> List[ResourceConfig]:
        return self.resources
