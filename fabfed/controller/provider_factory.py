from fabfed.provider.api.api_client import Provider
from typing import List, Dict


class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def init_provider(self, kind: str, name: str, attributes, logger):
        if kind == 'fabric':
            from fabfed.provider.fabric.fabric_provider import FabricProvider

            provider = FabricProvider(type=kind, name=name, logger=logger, config=attributes)
            provider.setup_environment()
            self._providers[name + '@' + kind] = provider
        elif kind == 'chi':
            from fabfed.provider.chi.chi_provider import ChiProvider

            provider = ChiProvider(type=kind, name=name, logger=logger, config=attributes)
            self._providers[name + '@' + kind] = provider
        else:
            raise Exception(f"no provider for type {kind}")

    @property
    def providers(self) -> List[Provider]:
        return list(self._providers.values())

    def get_provider(self, kind: str, name: str) -> Provider:
        return self._providers[name + '@' + kind]


provider_factory = ProviderFactory()
