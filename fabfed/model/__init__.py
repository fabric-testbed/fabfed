from abc import ABC, abstractmethod
from collections import namedtuple


class SSHNode():
    def __init__(self, user: str, host: str, keyfile: str,
                 jump_user: str = None, jump_host: str = None, jump_keyfile=None):
        self.user = user
        self.host = host
        self.keyfile = keyfile
        self.jump_user = jump_user
        self.jump_host = jump_host
        self.jump_keyfile = jump_keyfile

    @property
    def sshcmd_str(self) -> str:
        if self.jump_host and self.jump_user:
            return f"ssh {self.user}@{self.host} -J {self.jump_user}@{self.jump_host}"
        else:
            return f"ssh {self.user}@{self.host} -i {self.keyfile}"
    @property
    def proxyjump_str(self) -> str:
        if self.jump_host and self.jump_user and self.jump_keyfile:
            return f"-o ProxyJump=\"{self.jump_user}@{self.jump_host}\""


class Node(ABC,SSHNode):
    def __init__(self, *, label, name: str, image: str, site: str, flavor: str):
        self.label = label
        self.name = name
        self.image = image
        self.site = site
        self.flavor = flavor
        self.mgmt_ip = None
        self.keyfile = None
        self.jump_user = None
        self.jump_host = None
        self.jump_keyfile = None

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
    def __init__(self, *, label, name: str):
        self.label = label
        self.name = name


ResolvedDependency = namedtuple("ResolvedDependency", "resource_label attr value")
