from abc import ABC, abstractmethod
from collections import namedtuple
from typing import List

from fabfed.util.constants import Constants


class Node(ABC):
    def __init__(self, *, label, name: str, image: str, site: str, flavor: str):
        self.label = label
        self.name = name
        self.image = image
        self.site = site
        self.flavor = flavor
        self.mgmt_ip = None

    def get_label(self) -> str:
        return self.label

    def get_name(self) -> str:
        return self.name

    def get_site(self) -> str:
        return self.site

    def get_flavor(self) -> dict or str:
        return self.flavor

    def get_image(self) -> str:
        return self.image

    def get_management_ip(self) -> str:
        return self.mgmt_ip

    @abstractmethod
    def get_reservation_state(self) -> str:
        pass

    @abstractmethod
    def get_reservation_id(self) -> str:
        pass


class Network(ABC):
    def __init__(self, *, label, name: str, site: str):
        self.label = label
        self.name = name
        self.site = site

    def get_label(self) -> str:
        return self.label

    def get_name(self) -> str:
        return self.name

    def get_site(self) -> str:
        return self.site

    def get_reservation_id(self):
        pass


class Service(ABC):
    pass


class ResourceListener(ABC):
    @abstractmethod
    def on_added(self, source, slice_name, resource: dict):
        pass

    @abstractmethod
    def on_created(self, source, slice_name, resource: dict):
        pass

    @abstractmethod
    def on_deleted(self, source, slice_name, resource: dict):
        pass


ResolvedDependency = namedtuple("ResolvedDependency", "attr  value")


class Slice(ABC):
    def __init__(self, *, label, name):
        self.label = label
        self._name = name
        self._nodes = list()
        self._networks = list()
        self._services = list()
        self.resource_listener = None
        self.slice_created = False
        self.pending = []
        self.failed = {}
        self.added = []

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, source, slice_name, resource: dict):
        assert self != source
        assert slice_name
        assert resource

    def on_deleted(self, source, slice_name, resource):
        assert self != source
        assert slice_name
        assert resource

    def on_created(self, source, slice_name, resource):
        assert self != source
        assert slice_name

        for pending_resource in self.pending.copy():
            for dependency in pending_resource[Constants.EXTERNAL_DEPENDENCIES]:
                if dependency.resource.label == resource[Constants.LABEL]:
                    value = resource[dependency.attribute]

                    if value:
                        resolved_dependencies = pending_resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]

                        if isinstance(value, list):
                            resolved_dependency = ResolvedDependency(attr=dependency.key, value=tuple(value))
                        else:
                            resolved_dependency = ResolvedDependency(attr=dependency.key, value=value)

                        resolved_dependencies.append(resolved_dependency)

                        if len(pending_resource[Constants.EXTERNAL_DEPENDENCIES]) == len(
                                pending_resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]):
                            self.pending.remove(pending_resource)
                            self.add_resource(resource=pending_resource)

    def add_resource(self, *, resource: dict):
        count = resource.get(Constants.RES_COUNT, 1)
        label = resource.get(Constants.LABEL)

        if count < 1:
            self.logger.info(f"Skipping {label}. slices_name={self.name}: count={count}")
            return
        elif len(resource[Constants.EXTERNAL_DEPENDENCIES]) > len(resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]):
            self.logger.info(f"Adding  {label} to pending. slice_name={self.name}")
            assert resource not in self.pending, f"Did not expect {label} to be in pending list"
            self.pending.append(resource)
            return

        try:
            self.do_add_resource(resource=resource)
            self.added.append(label)
        except Exception as e:
            label = resource.get(Constants.LABEL)

            self.failed[label] = 'ADD'
            raise e

    def create_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)

        if label in self.added:
            try:
                self.do_create_resource(resource=resource)
            except Exception as e:
                self.failed[label] = 'CREATE'
                raise e

    def delete_resource(self, *, resource: dict):
        try:
            self.do_delete_resource(resource=resource)
        except Exception as e:
            label = resource.get(Constants.LABEL)

            self.failed[label] = 'DELETE'
            raise e

    @abstractmethod
    def do_add_resource(self, *, resource: dict):
        pass

    @abstractmethod
    def do_create_resource(self, *, resource: dict):
        pass

    @abstractmethod
    def do_delete_resource(self, *, resource: dict):
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def nodes(self) -> List[Node]:
        return self._nodes

    @property
    def networks(self) -> List[Network]:
        return self._networks

    @property
    def services(self) -> List[Service]:
        return self._services

    def __str__(self):
        from tabulate import tabulate
        table = [["Slice Name", self.name],
                 ]

        return tabulate(table)

    def list_networks(self) -> list:
        from tabulate import tabulate

        table = []
        for network in self.networks:
            table.append([network.get_reservation_id(),
                          network.get_name(),
                          network.get_site()
                          ])

        return tabulate(table, headers=["ID", "Name", "Site"])

    def list_nodes(self) -> list:
        from tabulate import tabulate

        table = []
        for node in self._nodes:
            table.append([node.get_reservation_id(),
                          node.get_name(),
                          node.get_site(),
                          node.get_flavor(),
                          node.get_image(),
                          node.get_management_ip(),
                          node.get_reservation_state()
                          ])

        return tabulate(table, headers=["ID", "Name", "Site", "Flavor", "Image",
                                        "Management IP", "State"])

    def get_state(self):
        from fabfed.model.state import SliceState, NetworkState, NodeState

        net_states = []

        for net in self.networks:
            attributes = vars(net).copy()
            attributes.pop('logger', None)
            attributes.pop('label')
            attributes = {key: value for key, value in attributes.items() if not key.startswith('_')}
            net_state = NetworkState(label=net.label, attributes=attributes)
            net_states.append(net_state)

        node_states = []

        for node in self.nodes:
            attributes = vars(node).copy()
            attributes.pop('logger', None)
            attributes.pop('label')
            attributes = {key: value for key, value in attributes.items() if not key.startswith('_')}
            node_state = NodeState(label=node.label, attributes=attributes)
            node_states.append(node_state)

        pending = []
        from fabfed.util.parser import DependencyInfo

        for resource in self.pending:
            copy = {}

            for key, value in resource.items():
                if key in [Constants.EXTERNAL_DEPENDENCIES, Constants.RESOLVED_EXTERNAL_DEPENDENCIES]:
                    continue

                if isinstance(value, DependencyInfo):  # TODO Add Yaml dumper/loader to parser.DependencyInfo
                    value = str(value)

                copy[key] = value

            pending.append(copy)

        return SliceState(self.label, dict(name=self.name), net_states, node_states, pending, self.failed)
