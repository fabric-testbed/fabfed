from typing import Dict, List

import yaml

from fabfed.util.config_models import Config, ResourceConfig, BaseConfig, ProviderConfig, Dependency, DependencyInfo
from fabfed.model import ResolvedDependency


class BaseState:
    def __init__(self, type: str, label: str, attributes: Dict):
        self.type = type
        self.label = label
        self.attributes = attributes


class NetworkState(BaseState):
    def __init__(self, *, label, attributes):
        super().__init__("network", label, attributes)


class NodeState(BaseState):
    def __init__(self, *, label, attributes):
        super().__init__("node", label, attributes)


class ServiceState(BaseState):
    def __init__(self, *, label, attributes):
        super().__init__("service", label, attributes)


class ProviderState(BaseState):
    def __init__(self, label, attributes, network_states: List[NetworkState],
                 node_states: List[NodeState], service_states: List[ServiceState], pending, pending_internal, failed: Dict[str, str]):
        super().__init__("provider", label, attributes)
        self.network_states = network_states
        self.node_states = node_states
        self.service_states = service_states
        self.pending = pending
        self.pending_internal = pending_internal
        self.failed = failed

    def states(self):
        return self.network_states + self.node_states + self.service_states


def provider_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ProviderState:
    return ProviderState(**loader.construct_mapping(node))


def provider_representer(dumper: yaml.SafeDumper, provider_state: ProviderState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ProviderState", {
        "label": provider_state.label,
        "attributes": provider_state.attributes,
        "network_states": provider_state.network_states,
        "node_states": provider_state.node_states,
        "service_states": provider_state.service_states,
        "pending": provider_state.pending,
        "pending_internal": provider_state.pending_internal,
        "failed": provider_state.failed
    })


def network_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> NetworkState:
    return NetworkState(**loader.construct_mapping(node))


def network_representer(dumper: yaml.SafeDumper, network_state: NetworkState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!NetworkState", {
        "label": network_state.label,
        "attributes": network_state.attributes
    })


def node_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> NodeState:
    return NodeState(**loader.construct_mapping(node))


def node_representer(dumper: yaml.SafeDumper, node_state: NodeState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!NodeState", {
        "label": node_state.label,
        "attributes": node_state.attributes
    })


def base_config_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> BaseConfig:
    return BaseConfig(**loader.construct_mapping(node))


def base_config_representer(dumper: yaml.SafeDumper, base_config: BaseConfig) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!BaseConfig", {
        "type": base_config.type,
        "name": base_config.name,
        "attrs": base_config.attributes
    })


def config_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> Config:
    return Config(**loader.construct_mapping(node))


def config_representer(dumper: yaml.SafeDumper, config: Config) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!Config", {
        "type": config.type,
        "name": config.name,
        "attrs": config.attributes
    })


def provider_config_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ProviderConfig:
    return ProviderConfig(**loader.construct_mapping(node))


def provider_config_representer(dumper: yaml.SafeDumper, provider_config: ProviderConfig) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ProviderConfig", {
        "type": provider_config.type,
        "name": provider_config.var_name,
        "attrs": provider_config.attributes
    })


def resource_config_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ResourceConfig:
    return ResourceConfig(**loader.construct_mapping(node))


def resource_config_representer(dumper: yaml.SafeDumper, resource_config: ResourceConfig) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ResourceConfig", {
        "type": resource_config.type,
        "name": resource_config.var_name,
        "attrs": resource_config.attributes,
        "provider": resource_config.provider
    })


def service_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ServiceState:
    return ServiceState(**loader.construct_mapping(node))


def service_representer(dumper: yaml.SafeDumper, service_state: ServiceState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ServiceState", {
        "label": service_state.label,
        "attributes": service_state.attributes
    })


def named_tuple(self, data):
    if hasattr(data, '_asdict'):
        if isinstance(data, DependencyInfo):
            data = dict(dependency_info=dict(resource=str(data.resource),
                                             attribute=data.attribute))
        elif isinstance(data, Dependency):
            data = dict(dependency=dict(resource=str(data.resource),
                                        key=data.key,
                                        is_external=data.is_external,
                                        attribute=data.attribute))
        elif isinstance(data, ResolvedDependency):
            data = dict(resolved_dependency=dict(resource_label=data.resource_label,
                                                 attribute=data.attr,
                                                 value=str(data.value)))
        else:
            data = data._asdict()

        return self.represent_dict(data)

    return self.represent_list(data)


def get_loader():
    loader = yaml.SafeLoader
    loader.add_constructor("!NetworkState", network_constructor)
    loader.add_constructor("!ProviderState", provider_constructor)
    loader.add_constructor("!NodeState", node_constructor)
    loader.add_constructor("!ServiceState", service_constructor)
    loader.add_constructor("!ResourceConfig", resource_config_constructor)
    loader.add_constructor("!ProviderConfig", provider_config_constructor)
    loader.add_constructor("!BaseConfig", base_config_constructor)
    loader.add_constructor("!Config", config_constructor)
    return loader


def get_dumper():
    safe_dumper = yaml.SafeDumper
    safe_dumper.add_representer(NetworkState, network_representer)
    safe_dumper.add_representer(ProviderState, provider_representer)
    safe_dumper.add_representer(NodeState, node_representer)
    safe_dumper.add_representer(ServiceState, service_representer)
    safe_dumper.add_representer(ResourceConfig, resource_config_representer)
    safe_dumper.add_representer(ProviderConfig, provider_config_representer)
    safe_dumper.add_representer(Config, config_representer)
    safe_dumper.add_representer(BaseConfig, base_config_representer)
    safe_dumper.yaml_multi_representers[tuple] = named_tuple
    return safe_dumper
