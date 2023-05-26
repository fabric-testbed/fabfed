from types import SimpleNamespace
from typing import List

from fabfed.util.config_models import *
from fabfed.util.config_models import ResourceConfig


class ResourceDependencyEvaluator:
    def __init__(self, resources: List[ResourceConfig], providers: List[ProviderConfig]):
        self.resources = resources
        self.providers = providers
        self.dependency_map: Dict[ResourceConfig, Set[ResourceConfig]] = {}

    def _find_resource(self, basic_config):
        index = self.resources.index(resource_from_basic_config(basic_config, self.providers))
        assert index >= 0, "expected to find resource in list"
        return self.resources[index]

    def add_dependency(self, res: ResourceConfig, key: str, dependency_info: DependencyInfo):
        found = self._find_resource(dependency_info.resource)
        is_external = res.provider.label != found.provider.label
        temp = Dependency(key=key, resource=found, attribute=dependency_info.attribute, is_external=is_external)
        res.add_dependency(temp)
        self.dependency_map[res].add(found)

    def handle_dependency(self, resource: ResourceConfig, key: str, value):
        if isinstance(value, DependencyInfo):
            self.add_dependency(resource, key, value)
        elif isinstance(value, list):
            for val in value:
                self.handle_dependency(resource, key, val)
        elif isinstance(value, dict):
            prefix = key + '.'
            for k, val in value.items():
                self.handle_dependency(resource, prefix + k, val)
        elif isinstance(value, SimpleNamespace):
            raise Exception(key)

    def evaluate(self) -> Dict[ResourceConfig, Set[ResourceConfig]]:
        for resource in self.resources:
            self.dependency_map[resource] = set()

            for key, value in resource.attributes.items():
                self.handle_dependency(resource, key, value)

        return self.dependency_map


def order_resources(dependency_map:  Dict[ResourceConfig, Set[ResourceConfig]]) -> List[ResourceConfig]:
    ordered_resources: List[ResourceConfig] = []
    while len(dependency_map) > 0:
        found = None

        for key, value in dependency_map.items():
            if len(value) == 0:
                found = key
                break

        if not found:
            raise Exception("circular dependencies ...." + str(dependency_map))

        dependency_map.pop(found)
        ordered_resources.append(found)
        for value in dependency_map.values():
            if found in value:
                value.remove(found)

    return ordered_resources
