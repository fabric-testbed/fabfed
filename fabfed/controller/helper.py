from fabfed.provider.api.provider import Provider
from fabfed.provider.api.resource_event_listener import ResourceListener


class ControllerResourceListener(ResourceListener):
    def __init__(self,  providers):
        self.providers = providers

    def on_added(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_added(source=self, provider=provider, resource=resource)

    def on_created(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_created(source=self, provider=provider, resource=resource)

    def on_deleted(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_deleted(source=self, provider=provider, resource=resource)
