import logging

from fabfed.model import Service
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants

'''

To add a provider, all you should need is to add its classpath to fabfed.util.constants.Constants.PROVIDER_CLASSES

Useful Commands:
cd tests/examples/dummy-service
fabfed workflow --session <session> -validate
fabfed workflow --session <session> -plan
fabfed workflow --session <session> -apply
fabfed workflow --session <session> -show
fabfed workflow --session <session> -destroy
'''


class DummyService(Service):
    def __init__(self, *, label, name: str, image, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.image = image

    def create(self):
        self.logger.info(f" Service {self.name} created")

    def delete(self):
        self.logger.info(f" Service {self.name} deleted")


class DummyProvider(Provider):

    def setup_environment(self):
        pass

    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)

    def do_add_resource(self, *, resource: dict):
        """
        Called by add_resource(self, *, resource: dict) if resource has no external dependencies.
        The add_resource(self, *, resource: dict) puts resources in the pending dictionary when
        they have external dependencies.

        When the external dependencies are satisfied following a resource creation event, this method
        would be called automatically. See on_created(self, *, source, provider, resource: object)

        Note that external dependencies are respurce dependencies across different providers.
        @param resource: resource attributes
        """
        rtype = resource.get(Constants.RES_TYPE)
        label = resource.get(Constants.LABEL)
        assert rtype
        assert label
        assert rtype in Constants.RES_SUPPORTED_TYPES
        self.logger.info(f"Adding resource={resource} using {self.label}")

        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        service_count = resource.get(Constants.RES_COUNT, 1)
        image = resource.get(Constants.RES_IMAGE)

        for n in range(0, service_count):
            service_name = f"{self.name}-{service_name_prefix}{n}"
            service = DummyService(label=label, name=service_name, image=image, logger=self.logger)

            self._services.append(service)
            self.resource_listener.on_added(source=self, provider=self, resource=service)

    def do_create_resource(self, *, resource: dict):
        """
        Called by add_resource(self, *, resource: dict) if resource has no external dependencies
        @param resource: resource attributes
        """
        rtype = resource.get(Constants.RES_TYPE)
        label = resource.get(Constants.LABEL)
        assert rtype
        assert label
        assert rtype in Constants.RES_SUPPORTED_TYPES
        self.logger.info(f"Creating resource={resource} using {self.label}")

        temp = [service for service in self.services if service.label == label]

        for service in temp:
            service.create()
            self.resource_listener.on_created(source=self, provider=self, resource=service)

    def do_delete_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        label = resource.get(Constants.LABEL)
        assert rtype
        assert label
        assert rtype in Constants.RES_SUPPORTED_TYPES
        self.logger.info(f"Deleting resource={resource} using {self.label}")

        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        service_count = resource.get(Constants.RES_COUNT, 1)
        image = resource.get(Constants.RES_IMAGE)

        for n in range(0, service_count):
            service_name = f"{self.name}-{service_name_prefix}{n}"
            service = DummyService(label=label, name=service_name, image=image, logger=self.logger)
            service.delete()
            self.resource_listener.on_added(source=self, provider=self, resource=service)
