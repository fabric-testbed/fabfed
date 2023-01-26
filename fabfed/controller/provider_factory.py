from fabfed.provider.api.provider import Provider
from typing import List, Dict

from fabfed.util.constants import Constants


class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def init_provider(self, *, type: str, label: str, name: str, attributes, logger):
        if type not in Constants.PROVIDER_CLASSES:
            from fabfed.exceptions import ProviderTypeNotSupported
            raise ProviderTypeNotSupported(type)

        import importlib

        full_name = Constants.PROVIDER_CLASSES.get(type)
        idx = full_name.rindex('.')
        module_name = full_name[:idx]
        class_name = full_name[idx+1:]
        cls = getattr(importlib.import_module(module_name), class_name)
        try:
            provider = cls(type=type, label=label, name=name, logger=logger, config=attributes)
        except:
            provider = cls(type=type, label=label, name=name, config=attributes)

        provider.setup_environment()
        self._providers[label] = provider

    @property
    def providers(self) -> List[Provider]:
        return list(self._providers.values())

    def get_provider(self, *, label: str) -> Provider:
        return self._providers[label]


default_provider_factory = ProviderFactory()
