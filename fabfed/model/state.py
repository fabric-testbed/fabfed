from typing import Dict, List

import yaml


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


class ProviderState(BaseState):
    def __init__(self, label, attributes, network_states: List[NetworkState],
                 node_states: List[NodeState], pending, failed: Dict[str, str]):
        super().__init__("provider", label, attributes)
        self.network_states = network_states
        self.node_states = node_states
        self.pending = pending
        self.failed = failed


def provider_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> ProviderState:
    return ProviderState(**loader.construct_mapping(node))


def provider_representer(dumper: yaml.SafeDumper, slice_state: ProviderState) -> yaml.nodes.MappingNode:
    return dumper.represent_mapping("!ProviderState", {
        "label": slice_state.label,
        "attributes": slice_state.attributes,
        "network_states": slice_state.network_states,
        "node_states": slice_state.node_states,
        "pending": slice_state.pending,
        "failed": slice_state.failed
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


def get_loader():
    loader = yaml.SafeLoader
    loader.add_constructor("!NetworkState", network_constructor)
    loader.add_constructor("!ProviderState", provider_constructor)
    loader.add_constructor("!NodeState", node_constructor)
    return loader


def get_dumper():
    safe_dumper = yaml.SafeDumper
    safe_dumper.add_representer(NetworkState, network_representer)
    safe_dumper.add_representer(ProviderState, provider_representer)
    safe_dumper.add_representer(NodeState, node_representer)
    return safe_dumper
