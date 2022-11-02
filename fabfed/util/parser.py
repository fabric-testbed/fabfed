from collections import namedtuple
from types import SimpleNamespace
from typing import List, Tuple, Dict, Set, Any

from fabfed.exceptions import ParseConfigException


class Variable:
    def __init__(self, name: str, value: Any):
        self._name = name.lower()
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return 'Variable[' + self.name + '=' + str(self.value) + ']'

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class BaseConfig:
    def __init__(self, type: str, name: str, attrs: Dict):
        self.type = type.lower()
        self._var_name = name.lower()
        self.attributes = attrs

    @property
    def label(self) -> str:
        return self._var_name + '@' + self.type

    @property
    def var_name(self) -> str:
        return self._var_name

    @property
    def name(self) -> str:
        return self.attributes['name'] if 'name' in self.attributes else self._var_name

    def attribute(self, key: str):
        return self.attributes.get(key)

    def __str__(self) -> str:
        return self.var_name + '@' + self.type

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other):
        return (self.var_name, self.type) == (other.var_name, other.type)

    def __hash__(self):
        return hash(str(self))


class ProviderConfig(BaseConfig):
    def __init__(self, type: str, name: str, attrs: Dict):
        super().__init__(type, name, attrs)


DependencyInfo = namedtuple("DependencyInfo", "resource  attribute")

Dependency = namedtuple("Dependency", "key resource  attribute, is_external")


class ResourceConfig(BaseConfig):
    def __init__(self, type: str, name: str, attrs:  Dict, provider: ProviderConfig):
        super().__init__(type, name, attrs)
        assert provider, f"provider is required for {name}"
        assert isinstance(provider, ProviderConfig), f"expected SliceConfig for {name}"
        self._provider = provider
        self._resource_dependencies = set()

    @property
    def provider(self) -> ProviderConfig:
        return self._provider

    @property
    def dependencies(self) -> Set[Dependency]:
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


def resource_from_basic_config(basic_config, providers) -> ResourceConfig:
    attrs = basic_config.attributes.copy()

    if 'provider' not in attrs:
        raise ParseConfigException(f"resource missing provider {basic_config.var_name}")

    provider = attrs.pop('provider')

    if not provider:
        raise ParseConfigException(f"missing provider while parsing {basic_config}")

    index = providers.index(ProviderConfig(provider.type, provider.var_name, {}))

    if index < 0:
        raise ParseConfigException(f"did not find provider {provider.var_name} for {basic_config}")

    return ResourceConfig(basic_config.type, basic_config.var_name, attrs, provider)


class VariableEvaluator:
    def __init__(self, variables: List[Variable], providers: List[ProviderConfig], resources: List[BaseConfig]):
        self.variables = variables
        self.providers = providers
        self.resources = resources

    def find_variable(self, path: str) -> BaseConfig or Dependency:
        parts = path.split('.')
        assert parts[0] == 'var'

        if len(parts) != 2:
            raise ParseConfigException(f"bad variable dependency {path}")

        for variable in self.variables:
            if variable.name == parts[1]:
                return variable.value

        raise ParseConfigException(f'variable not found at {path}')

    def handle_substitution(self, value):
        if isinstance(value, str):
            value = value.strip()

            if value.startswith('{{') and value.endswith('}}'):
                path = value[2:-2].strip()

                if path.startswith('var'):
                    return self.find_variable(path)

            return value
        elif isinstance(value, list):
            temp = []
            for val in value:
                temp.append(self.handle_substitution(val))
            return temp
        elif isinstance(value, dict):
            temp = {}

            for k, val in value.items():
                temp[k] = self.handle_substitution(val)

            return temp
        elif isinstance(value, SimpleNamespace):
            return self.handle_substitution(vars(value))
        else:
            return value

    def evaluate(self) -> Tuple[List[ProviderConfig], List[BaseConfig]]:
        config_entries: List[BaseConfig] = []
        config_entries.extend(self.providers)
        config_entries.extend(self.resources)

        for config_resource_entry in config_entries:
            attrs = {}

            for key, value in config_resource_entry.attributes.items():
                attrs[key] = self.handle_substitution(value)

            config_resource_entry.attributes = attrs

        return self.providers, self.resources


class Evaluator:
    def __init__(self, providers: List[ProviderConfig], resources: List[BaseConfig]):
        self.providers = providers
        self.resources = resources

    def find_object(self, path: str) -> BaseConfig or Dependency:
        parts = path.split('.')
        config_entries: List[BaseConfig] = []
        config_entries.extend(self.providers)
        config_entries.extend(self.resources)

        if len(parts) < 2:
            raise ParseConfigException(f"bad dependency {path}")

        for config_entry in config_entries:
            # TODO CHECK IF THIS IS A PROVIDER CONFIG INSTEAD ...
            if config_entry.type == parts[0] and config_entry.var_name == parts[1]:
                if config_entry.type == 'node' or config_entry.type == 'network':
                    return DependencyInfo(resource=config_entry, attribute='.'.join(parts[2:]))

                return config_entry

        raise ParseConfigException(f'config entry not found at {path}')

    def handle_substitution(self, value):
        if isinstance(value, str):
            value = value.strip()

            if value.startswith('{{') and value.endswith('}}'):
                path = value[2:-2].strip()
                return self.find_object(path)

            return value
        elif isinstance(value, list):
            temp = []
            for val in value:
                temp.append(self.handle_substitution(val))
            return temp
        elif isinstance(value, dict):
            temp = {}

            for k, val in value.items():
                temp[k] = self.handle_substitution(val)

            return temp
        elif isinstance(value, SimpleNamespace):
            return self.handle_substitution(vars(value))
        else:
            return value

    def evaluate(self) -> Tuple[List[ProviderConfig], List[BaseConfig]]:
        for config_resource_entry in self.resources:
            attrs = {}

            for key, value in config_resource_entry.attributes.items():
                attrs[key] = self.handle_substitution(value)

            config_resource_entry.attributes = attrs

        return self.providers, self.resources


class ResourceDependencyEvaluator:
    # AES
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


def parse_pair(obj: SimpleNamespace) -> Tuple[str, Dict]:
    def extract_label(lst):
        return next(label for label in lst if not label.startswith("__"))

    if not isinstance(obj, SimpleNamespace):
        raise ParseConfigException(f"expecting a pair {obj}")

    try:
        name = extract_label(dir(obj))

        if not obj.__getattribute__(name):
            return name, {}

        attrs = obj.__getattribute__(name)[0].__dict__

        if len(obj.__getattribute__(name)) > 1:
            raise ParseConfigException(f"did not expect a block after{attrs} under {name}")

        return name, attrs
    except ParseConfigException as e:
        raise e
    except Exception as e:
        raise ParseConfigException(f" exception occurred while parsing pair {obj}") from e


def parse_triplet(obj: SimpleNamespace) -> Tuple[str, str, Dict]:
    def extract_label(lst):
        return next(label for label in lst if not label.startswith("__"))

    if not isinstance(obj, SimpleNamespace):
        raise ParseConfigException(f"expecting a triplet {obj}")

    try:
        type = extract_label(dir(obj))
        value = obj.__getattribute__(type)[0]
        name = extract_label(dir(value))

        if len(obj.__getattribute__(type)) > 1:
            raise ParseConfigException(f"did not expect a block after {name} of type {type}")

        attrs = value.__getattribute__(name)[0].__dict__

        if len(value.__getattribute__(name)) > 1:
            raise ParseConfigException(f"did not expect a block after {attrs} under {name} of type {type}")

        return type, name, attrs
    except ParseConfigException as e:
        raise e
    except Exception as e:
        raise ParseConfigException(f" exception occurred while parsing triplet {obj}") from e


class Parser:
    def __init__(self):
        pass

    @staticmethod
    def _parse_variable(obj) -> Variable:
        name, attributes = parse_pair(obj)
        return Variable(name, attributes.get('default', None))

    @staticmethod
    def _parse_resource(obj) -> BaseConfig:
        type, name, attributes = parse_triplet(obj)
        return BaseConfig(type, name, attributes)

    @staticmethod
    def _parse_provider(obj) -> ProviderConfig:
        type, name, attributes = parse_triplet(obj)
        return ProviderConfig(type, name, attributes)

    @staticmethod
    def _filter_resources(base_configs, providers) -> List[ResourceConfig]:
        resources = []

        for base_config in base_configs:
            resources.append(resource_from_basic_config(base_config, providers))

        return resources

    @staticmethod
    def _validate_variables(variables: List[Variable]):
        if len(variables) != len(set(variables)):
            raise ParseConfigException(f'detected duplicate variables')

        for variable in variables:
            if not variable.value:
                raise ParseConfigException(f'variable {variable .name} is not bound')

    @staticmethod
    def _validate_providers(providers: List[ProviderConfig]):
        if len(providers) == 0:
            raise ParseConfigException("no providers found ...")

        if len(providers) != len(set(providers)):
            raise ParseConfigException(f'detected duplicate providers')

    @staticmethod
    def _validate_resources(resources: List[ResourceConfig]):
        if len(resources) == 0:
            raise ParseConfigException("no resources found ...")

        if len(resources) != len(set(resources)):
            raise ParseConfigException(f'detected duplicate  resources')

        for resource in resources:
            if resource.type not in ['node', 'network']:
                raise ParseConfigException(f'not expecting a resource type {resource.type}')

    @staticmethod
    def parse_variables(ns_list: list, var_dict: dict) -> List[Variable]:
        variables = []

        for ns in ns_list:
            if hasattr(ns, 'variable') and ns.variable:
                temp_variables = [Parser._parse_variable(variable) for variable in ns.variable]
                variables.extend(temp_variables)

        if var_dict:
            variable_map = {v.name: v for v in variables}

            for key, value in var_dict.items():
                variable_map[key] = Variable(key, value)

            variables = list(variable_map.values())

        Parser._validate_variables(variables)
        return variables

    @staticmethod
    def parse_providers(ns_list: list) -> List[ProviderConfig]:
        providers = []

        for ns in ns_list:
            if hasattr(ns, 'provider') and ns.provider:
                temp_providers = [Parser._parse_provider(provider) for provider in ns.provider]
                providers.extend(temp_providers)

        Parser._validate_providers(providers)
        normalize(providers)
        return providers

    @staticmethod
    def parse_resource_base_configs(ns_list: List[SimpleNamespace]) -> List[BaseConfig]:
        resource_base_configs = []

        for ns in ns_list:
            if hasattr(ns, 'resource') and ns.resource:
                temp_resource_base_configs = [Parser._parse_resource(resource) for resource in ns.resource]
                resource_base_configs.extend(temp_resource_base_configs)

        return resource_base_configs

    @staticmethod
    def parse(*, dir_path=None,
              content=None,
              var_dict=None) -> Tuple[List[ProviderConfig], List[ResourceConfig]]:

        from .utils import load_as_ns_from_yaml

        ns_list = load_as_ns_from_yaml(dir_path=dir_path, content=content)
        variables = Parser.parse_variables(ns_list, var_dict)
        providers = Parser.parse_providers(ns_list)

        resource_base_configs = Parser.parse_resource_base_configs(ns_list)

        variable_evaluator = VariableEvaluator(variables, providers, resource_base_configs)
        providers, resource_configs = variable_evaluator.evaluate()

        evaluator = Evaluator(providers, resource_base_configs)
        providers, resource_configs = evaluator.evaluate()
        resources = Parser._filter_resources(resource_configs, providers)
        Parser._validate_resources(resources)

        dependency_evaluator = ResourceDependencyEvaluator(resources, providers)
        dependency_map = dependency_evaluator.evaluate()
        ordered_resources = order_resources(dependency_map)
        return providers, ordered_resources
