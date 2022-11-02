from fabfed.provider.api.provider import Provider
from typing import List, Dict


class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def init_provider(self, *, type: str, label: str, name: str, attributes, logger):
        if type == 'fabric':
            from fabfed.provider.fabric.fabric_provider import FabricProvider

            provider = FabricProvider(type=type, label=label, name=name, logger=logger, config=attributes)
            provider.setup_environment()
            self._providers[label] = provider
        elif type == 'chi':
            from fabfed.provider.chi.chi_provider import ChiProvider

            provider = ChiProvider(type=type, label=label, name=name, logger=logger, config=attributes)
            self._providers[label] = provider
        elif type == 'sense':
            from fabfed.provider.sense.sense_provider import SenseProvider

            provider = SenseProvider(type=type, label=label, name=name, logger=logger, config=attributes)
            provider.setup_environment()
            self._providers[label] = provider
        else:
            raise Exception(f"no provider for type {type}")

    @property
    def providers(self) -> List[Provider]:
        return list(self._providers.values())

    def get_provider(self, *, label: str) -> Provider:
        return self._providers[label]


default_provider_factory = ProviderFactory()
