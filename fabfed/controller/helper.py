from fabfed.model import ResourceListener


class ControllerResourceListener(ResourceListener):
    def __init__(self,  providers):
        self.providers = providers

    def on_added(self, source, slice_name, resource: dict):
        for provider in self.providers:
            if provider != source:
                provider.on_added(self, slice_name, resource)

    def on_created(self, source, slice_name, resource):
        for provider in self.providers:
            if provider != source:
                provider.on_created(self, slice_name, resource)

    def on_deleted(self, source, slice_name, resource):
        pass