import os
import json
import logging

from fabfed.model import Service
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from fabfed.util.utils import get_base_dir
from fabfed.provider.janus.util.ansible_helper import AnsibleHelper


class JanusService(Service):
    def __init__(self, *, label, name: str, image, node=None, provider=None, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.image = image
        self._node = node[0] if isinstance(node, tuple) else node
        self._provider = provider

    def create(self):
        friendly_name = self._provider.name
        label = self._node.label
        name = self._node.name
        host_file = os.path.join(get_base_dir(), f"{friendly_name}-{label}-{name}-inventory.ini")
        helper = AnsibleHelper(host_file, self.logger)
        script_dir = os.path.dirname(__file__)
        helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"))
        self.logger.info(f" Service {self.name} created. service_node={self._node}")

    def delete(self):
        self.logger.info(f" Service {self.name} deleted")


class JanusProvider(Provider):
    def setup_environment(self):
        pass

    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)

    def _validate_resource(self, resource: dict):
        assert resource.get(Constants.LABEL)
        assert resource.get(Constants.RES_TYPE) in Constants.RES_SUPPORTED_TYPES
        assert resource.get(Constants.RES_NAME_PREFIX)
        assert resource.get(Constants.RES_COUNT, 1)
        assert resource.get(Constants.RES_IMAGE)

        self.logger.info(f"Validated:OK Resource={resource} using {self.label}")

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
        self.logger.info(f"Adding resource={resource} using {self.label}")
        self._validate_resource(resource)

        image = resource.get(Constants.RES_IMAGE)
        nodes = [rd for rd in resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]
                 if rd.attr == 'node']
        label = resource.get(Constants.LABEL)
        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        service_count = resource.get(Constants.RES_COUNT, 1)

        assert (len(nodes) == service_count)

        for n in range(0, service_count):
            service_name = f"{self.name}-{service_name_prefix}{n}"
            service = JanusService(label=label, name=service_name, image=image,
                                   node=nodes[n].value, provider=self, logger=self.logger)

            self._services.append(service)
            self.resource_listener.on_added(source=self, provider=self, resource=service)

    def do_create_resource(self, *, resource: dict):
        """
        Called by add_resource(self, *, resource: dict) if resource has no external dependencies
        @param resource: resource attributes
        """
        label = resource.get(Constants.LABEL)

        self.logger.info(f"Creating resource={resource} using {self.label}")

        temp = [service for service in self.services if service.label == label]

        for service in temp:
            service.create()
            self.resource_listener.on_created(source=self, provider=self, resource=service)

    def do_delete_resource(self, *, resource: dict):
        self.logger.info(f"Deleting resource={resource} using {self.label}")

        label = resource.get(Constants.LABEL)
        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        service_count = resource.get(Constants.RES_COUNT, 1)
        image = resource.get(Constants.RES_IMAGE)

        for n in range(0, service_count):
            service_name = f"{self.name}-{service_name_prefix}{n}"
            service = JanusService(label=label, name=service_name, image=image, logger=self.logger)
            service.delete()
            self.resource_listener.on_added(source=self, provider=self, resource=service)
