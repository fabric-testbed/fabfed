from abc import ABC, abstractmethod
from typing import List


class Node(ABC):
    def __init__(self, *, name: str, image: str, site: str, flavor: str):
        self.name = name
        self.image = image
        self.site = site
        self.flavor = flavor
        self.mgmt_ip = None

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


class Slice(ABC):
    def __init__(self, *, name):
        self._name = name
        self._nodes = list()
        self._networks = list()
        self._services = list()

    @abstractmethod
    def set_resource_listener(self, resource_listener):
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def destroy(self, *, slice_state):
        pass

    @abstractmethod
    def add_resource(self, resource: dict):
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
            attributes = vars(net)
            attributes.pop('logger', None)
            attributes = {key: value for key, value in attributes.items() if not key.startswith('_')}
            net_state = NetworkState(net.name, attributes)
            net_states.append(net_state)

        node_states = []

        for node in self.nodes:
            attributes = vars(node)
            attributes.pop('logger', None)
            attributes = {key: value for key, value in attributes.items() if not key.startswith('_')}
            node_state = NodeState(node.name, attributes)
            node_states.append(node_state)

        return SliceState(self.name, dict(), net_states, node_states)
