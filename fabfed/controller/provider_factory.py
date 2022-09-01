from fabfed.controller.api.api_client import ApiClient
from typing import List, Dict


class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, ApiClient] = {}

    def init_provider(self, kind: str, name: str, config, logger):
        if kind == 'fabric':
            from fabfed.controller.fabric.fabric_client import FabricClient

            provider = FabricClient(logger=logger, fabric_config=config)

            provider.setup_environment()
            self._providers[name + '@' + kind] = provider
        elif kind == 'chi':
            from fabfed.controller.chi.chi_client import ChiClient

            provider = ChiClient(logger=logger, chi_config=config)
            self._providers[name + '@' + kind] = provider
        else:
            raise Exception(f"no provider for {name}")

    @property
    def providers(self) -> List[ApiClient]:
        return list(self._providers.values())

    def get_provider(self, kind: str, name: str) -> ApiClient:
        return self._providers[name + '@' + kind]


provider_factory = ProviderFactory()
