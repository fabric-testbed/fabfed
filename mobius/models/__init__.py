from abc import ABC, abstractmethod
from typing import List, Dict, Callable


class AbstractNode(ABC):
    pass

class AbstractNetwork(ABC):
    pass

class AbstractService(ABC):
    pass

class AbstractSlice(ABC):
    @abstractmethod
    def create(self, rtype: str = None):
        pass

    @abstractmethod
    def delete(self, rtpe: str = None):
        pass

    @abstractmethod
    def add_resource(self, resource: dict):
        pass

    @property
    def nodes(self) -> List[AbstractNode]:
        return self._nodes

    @property
    def networks(self) -> List[AbstractNetwork]:
        return self._networks

    @property
    def services(self) -> List[AbstractService]:
        return self._services

    @property
    def callbacks(self) -> Dict[str, Callable]:
        return self._callbacks

    def register_callback(self, cb_key: str, cb: Callable):
        self._callbacks.update({cb_key: cb})
