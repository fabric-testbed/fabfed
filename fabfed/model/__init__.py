from abc import ABC, abstractmethod
from collections import namedtuple


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


ResolvedDependency = namedtuple("ResolvedDependency", "attr  value")
