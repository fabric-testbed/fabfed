import json
from types import SimpleNamespace
from typing import List, Union, Tuple, Dict, Set

import yaml


class BaseConfig:
    def __init__(self, type: str, name: str, attrs: Dict):
        self.type = type.lower()
        self.name = name.lower()
        self.attributes = attrs

    def attribute(self, key: str):
        return self.attributes.get(key)

    def __str__(self) -> str:
        return self.name + '@' + self.type

    def __repr__(self) -> str:
        return self.__str__()


class ProviderConfig(BaseConfig):
    def __init__(self, type: str, name: str, attrs: Dict):
        super().__init__(type, name, attrs)

    def __eq__(self, other):
        return self.name == other.name and self.type == other.type

    def __hash__(self):
        return hash(str(self))


class SliceConfig(BaseConfig):
    def __init__(self, type: str, name: str, attrs: Dict, provider: ProviderConfig):
        super().__init__(type, name, attrs)
        self._provider = provider

    @property
    def provider(self) -> ProviderConfig:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def provider_type(self) -> str:
        return self._provider.type

    def __str__(self) -> str:
        return super().__str__() + '@' + self.provider.__str__()

    def __eq__(self, other):
        return (self.name, self.type, self.provider.type) == (other.name, other.type, other.provider.type)

    def __hash__(self):
        return hash(self.name + self.type + self.provider.type)


class ResourceConfig(BaseConfig):
    def __init__(self, type: str, name: str, attrs:  Dict, slize: SliceConfig):
        super().__init__(type, name, attrs)
        assert slize, f"slice is required for {name}"
        assert isinstance(slize, SliceConfig), f"expected SliceConfig for {name}"
        self._slice = slize
        self._resource_dependencies = set()

    @property
    def slice(self) -> SliceConfig:
        return self._slice

    @property
    def dependencies(self):
        return self._resource_dependencies

    def add_dependency(self, dependency):
        self._resource_dependencies.add(dependency)

    def has_dependencies(self):
        return len(self._resource_dependencies) > 0

    @property
    def is_node(self):
        return self.type == 'node'

    @property
    def is_network(self):
        return self.type == 'network'

    @property
    def provider(self):
        return self.slice.provider

    def __str__(self) -> str:
        return super().__str__() + ' using ' + self.slice.__str__()

    def __eq__(self, other):
        return (self.name, self.type, self.slice) == (other.name, other.type, other.slice)

    def __hash__(self):
        return hash(self.name + self.type + str(hash(self.slice)))


def slice_from_basic_config(basic_config) -> SliceConfig:
    attrs = basic_config.attributes.copy()  # TODO check before pop
    provider = attrs.pop('provider')  # TODO check presence of provider
    return SliceConfig(basic_config.type, basic_config.name, attrs, provider)


def resource_from_basic_config(basic_config, slices) -> ResourceConfig:
    attrs = basic_config.attributes.copy()
    temp = attrs.pop('slice')  # TODO check before pop
    temp_provider = temp.attributes.get('provider', None)

    if not temp_provider:
        raise Exception()

    index = slices.index(SliceConfig(temp.type, temp.name, {}, temp_provider))

    if index < 0:
        raise Exception("did not find a slice ")

    return ResourceConfig(basic_config.type, basic_config.name, attrs, slices[index])


class Evaluator:
    def __init__(self, providers: List[ProviderConfig], resources: List[BaseConfig]):
        self.providers = providers
        self.resources = resources

    def find_object(self, path: str) -> BaseConfig:
        parts = path.split('.')
        config_entries: List[BaseConfig] = []
        config_entries.extend(self.providers)
        config_entries.extend(self.resources)

        if len(parts) < 2:
            raise Exception(f"bad dependency {path}")

        for config_entry in config_entries:
            if config_entry.type == parts[0] and config_entry.name == parts[1]:
                ret = BaseConfig(config_entry.type, config_entry.name, config_entry.attributes)
                ret._hide = '.'.join(parts[2:])
                return ret

        raise Exception(f"config entry not found at {path}")

    def handle_substitution(self,  value: str) -> Union[str, BaseConfig]:
        value = value.strip()

        if value.startswith('{{') and value.endswith('}}'):
            path = value[2:-2].strip()
            return self.find_object(path)

        return value

    def evaluate(self) -> Tuple[List[ProviderConfig], List[BaseConfig]]:
        for config_resource_entry in self.resources:
            attrs = {}

            for key, value in config_resource_entry.attributes.items():
                attrs[key] = value

                if isinstance(value, str):
                    attrs[key] = self.handle_substitution(value)
                elif isinstance(value, list):
                    attrs[key] = [self.handle_substitution(val) for val in value if isinstance(val, str)]
                elif isinstance(value, dict):
                    raise Exception(f"evaluator encountered dict ....{key}")
                elif isinstance(value, SimpleNamespace):
                    attrs[key] = vars(value)
                    temp = []

                    for item in attrs[key].items():
                        val = item[1]

                        if isinstance(val, str):
                            val = self.handle_substitution(val)

                        temp.append((item[0], val))

                    attrs[key] = dict(temp)

            config_resource_entry.attributes = attrs

        return self.providers, self.resources


class ResourceDependencyEvaluator:
    def __init__(self, resources: List[ResourceConfig], slices: List[SliceConfig]):
        self.resources = resources
        self.slices = slices

    def _find_resource(self, basic_config):
        index = self.resources.index(resource_from_basic_config(basic_config, self.slices))
        assert index >= 0, "expected to find resource in list"
        return self.resources[index]

    def evaluate(self) -> Dict[ResourceConfig, Set[ResourceConfig]]:
        dependency_map: Dict[ResourceConfig, Set[ResourceConfig]] = {}

        def add_dependency(res, name, obj):
            value = obj._hide if hasattr(obj, '_hide') else None
            found = self._find_resource(obj)
            dependency = (name, found, value)
            res.add_dependency(dependency)
            dependency_map[resource].add(found)

        for resource in self.resources:
            dependency_map[resource] = set()

            for key, value in resource.attributes.items():
                if isinstance(value, BaseConfig):
                    add_dependency(resource, key, value)
                elif isinstance(value, list):
                    for val in value:
                        if isinstance(val, BaseConfig):
                            add_dependency(resource, key, val)
                elif isinstance(value, dict):
                    for val in value.values():
                        if isinstance(val, BaseConfig):
                            add_dependency(resource, key, val)
                elif isinstance(value, SimpleNamespace):
                    raise Exception(key)

        return dependency_map


def order_resources(dependency_map:  Dict[ResourceConfig, Set[ResourceConfig]]) -> List[ResourceConfig]:
    ordered_resources: List[ResourceConfig] = []
    while len(dependency_map) > 0:
        found = None

        for key, value in dependency_map.items():
            if len(value) == 0:
                found = key
                break

        if not found:
            raise Exception("circular dependencies ....")

        dependency_map.pop(found)
        ordered_resources.append(found)
        for value in dependency_map.values():
            if found in value:
                value.remove(found)

    return ordered_resources


def normalize(objs):  # TODO looks like we need this  for chameleon provider
    for obj in objs:
        attrs = {}

        for key, value in obj.attributes.items():
            if isinstance(value, SimpleNamespace):
                attrs[key] = vars(value)
            else:
                attrs[key] = value

        obj.attributes = attrs


class Parser:
    def __init__(self):
        pass

    @staticmethod
    def _parse_object(obj) -> Tuple[str, str, Dict]:
        def extract_label(lst):
            return next(label for label in lst if not label.startswith("__"))

        type = extract_label(dir(obj))

        try:
            def extract_label(lst):
                return next(label for label in lst if not label.startswith("__"))

            type = extract_label(dir(obj))
            value = obj.__getattribute__(type)[0]
            name = extract_label(dir(value))
            value = value.__getattribute__(name)[0]
            attrs = value.__dict__
            return type, name, attrs
        except Exception:
            raise Exception(f"need to supply as a triplet {type}")

    @staticmethod
    def _parse_resource(obj) -> BaseConfig:
        type, name, attributes = Parser._parse_object(obj)
        return BaseConfig(type, name, attributes)

    @staticmethod
    def _parse_provider(obj) -> ProviderConfig:
        type, name, attributes = Parser._parse_object(obj)
        return ProviderConfig(type, name, attributes)

    @staticmethod
    def _filter_slices(base_configs) -> List[SliceConfig]:
        slices = []

        for base_config in filter(lambda r: r.type == 'slice', base_configs):
            slices.append(slice_from_basic_config(base_config))

        return slices

    @staticmethod
    def _filter_resources(base_configs, slices) -> List[ResourceConfig]:
        resources = []

        for basic_config in filter(lambda r: r.type != 'slice', base_configs):
            resources.append(resource_from_basic_config(basic_config, slices))

        return resources

    @staticmethod
    def validate_providers(providers:  List[ProviderConfig]):
        if len(providers) == 0:
            raise Exception("no providers found ...")

        if len(providers) != len(set(providers)):
            raise Exception(f'detected duplicate providers')

    @staticmethod
    def validate_slices(slices:  List[SliceConfig]):
        if len(slices) == 0:
            raise Exception("no slices found ...")

        if len(slices) != len(set(slices)):
            raise Exception(f'detected duplicate slices')

    @staticmethod
    def validate_resources(resources:  List[ResourceConfig]):
        if len(resources) == 0:
            raise Exception("no resources found ...")

        if len(resources) != len(set(resources)):
            raise Exception(f'detected duplicate  resources')

    @staticmethod
    def parse(file_name) -> Tuple[List[ProviderConfig], List[SliceConfig], List[ResourceConfig]]:
        def load_object(dct):
            return SimpleNamespace(**dct)

        with open(file_name, 'r') as stream:
            obj = yaml.safe_load(stream)
            obj = json.loads(json.dumps(obj), object_hook=load_object)

        if not hasattr(obj, 'provider') or obj.provider is None:
            raise Exception("no providers found")

        providers = [Parser._parse_provider(provider) for provider in obj.provider]
        Parser.validate_providers(providers)
        normalize(providers)

        if not hasattr(obj, 'resource') or obj.resource is None:
            raise Exception("no resources found ...")

        resource_base_configs = [Parser._parse_resource(resource) for resource in obj.resource]

        evaluator = Evaluator(providers, resource_base_configs)
        providers, resource_configs = evaluator.evaluate()

        slices = Parser._filter_slices(resource_configs)
        Parser.validate_slices(slices)

        resources = Parser._filter_resources(resource_configs, slices)
        Parser.validate_resources(resources)

        dependency_evaluator = ResourceDependencyEvaluator(resources, slices)
        dependency_map = dependency_evaluator.evaluate()
        ordered_resources = order_resources(dependency_map)
        return providers, slices, ordered_resources
