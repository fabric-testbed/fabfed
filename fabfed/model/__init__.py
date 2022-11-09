from abc import ABC, abstractmethod
from collections import namedtuple


class SSHInfo():
    def __init__(self, user: str, host: str, keyfile: str,
                 jump_user: str = None, jump_host: str = None, jump_keyfile=None):
        self._user = user
        self._host = host
        self._keyfile = keyfile
        self._jump_user = jump_user
        self._jump_host = jump_host

    def __str__(self) -> str:
        if self.jump_host and self.jump_user:
            return f"{self.user}@{self.host} -J {self.jump_user}@{self.jump_host}"
        else:
            return f"{self.user}@{self.host} -i {self.keyfile}"
    @property
    def proxy_str(self) -> str:
        if self.jump_host and self.jump_user and self.jump_keyfile:
            return "-o ProxyCommand=\"ssh -W %h:%p -q {self.jump_user}@{self.jump_host}\""

    @property
    def user(self)-> str:
        return self._user

    @property
    def host(self) -> str:
        return self._host

    @property
    def keyfile(self) -> str:
        return self._keyfile

    @property
    def jump_user(self) -> str:
        return self._jump_user

    @property
    def jump_host(self) -> str:
        return self._jump_host


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
    def get_ssh_info(self) -> SSHInfo:
        pass

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
    def __init__(self, *, label, name: str):
        self.label = label
        self.name = name


ResolvedDependency = namedtuple("ResolvedDependency", "attr  value")
