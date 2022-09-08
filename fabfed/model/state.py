import yaml
from typing import Dict


class BaseState:
    def __init__(self, type: str, name: str, attributes: Dict):
        self.type = type.lower()
        self.name = name.lower()
        self.attributes = attributes


class ProviderState(BaseState):
    def __init__(self, type, name, attributes, slice_states):
        super().__init__(type, name, attributes)
        self.slice_states = slice_states


class SliceState(BaseState):
    def __init__(self, name, attributes, network_states, node_states):
        super().__init__("slice",  name, attributes)
        self.network_states = network_states
        self.node_states = node_states


class NetworkState(BaseState):
    def __init__(self, name, attributes):
        super().__init__("network", name, attributes)


class NodeState(BaseState):
    def __init__(self, name, attributes):
        super().__init__("node", name, attributes)


def provider_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ProviderState:
    return ProviderState(**loader.construct_mapping(node))


def provider_representer(dumper: yaml.SafeDumper, provider_state: ProviderState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ProviderState", {
        "type": provider_state.type,
        "name": provider_state.name,
        "attributes": provider_state.attributes,
        "slice_states": provider_state.slice_states
    })


def slice_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> SliceState:
    return SliceState(**loader.construct_mapping(node))


def slice_representer(dumper: yaml.SafeDumper, slice_state: SliceState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!SliceState", {
        "name": slice_state.name,
        "attributes": slice_state.attributes,
        "network_states": slice_state.network_states,
        "node_states": slice_state.node_states
    })


def network_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> NetworkState:
    return NetworkState(**loader.construct_mapping(node))


def network_representer(dumper: yaml.SafeDumper, network_state: NetworkState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!NetworkState", {
        "name": network_state.name,
        "attributes": network_state.attributes
    })


def node_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> NodeState:
    return NodeState(**loader.construct_mapping(node))


def node_representer(dumper: yaml.SafeDumper, node_state: NodeState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!NodeState", {
        "name": node_state.name,
        "attributes": node_state.attributes
    })


def get_loader():
    loader = yaml.SafeLoader
    loader.add_constructor("!SliceState", slice_constructor)
    loader.add_constructor("!NetworkState", network_constructor)
    loader.add_constructor("!ProviderState", provider_constructor)
    loader.add_constructor("!NodeState", node_constructor)
    return loader


def get_dumper():
    safe_dumper = yaml.SafeDumper
    safe_dumper.add_representer(SliceState, slice_representer)
    safe_dumper.add_representer(NetworkState, network_representer)
    safe_dumper.add_representer(ProviderState, provider_representer)
    safe_dumper.add_representer(NodeState, node_representer)
    return safe_dumper
