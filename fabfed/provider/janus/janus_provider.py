import os
import json
import logging

from fabfed.model import Service, Resource
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

    def _do_ansible(self, delete=False):
        friendly_name = self._provider.name
        label = self._node.label
        name = self._node.name
        host_file = os.path.join(get_base_dir(friendly_name), f"{friendly_name}-{label}-{name}-inventory.ini")
        script_dir = os.path.dirname(__file__)
        helper = AnsibleHelper(host_file, self.logger)
        janus_vars = self._provider.config
        if not delete:
            janus_vars.update({"node": self._node.get_dataplane_address(),
                               "name": f"{friendly_name}-{name}"})
        helper.set_extra_vars(janus_vars)
        if delete:
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["janus-del"])
        else:
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["docker", "janus"])
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["janus-add"])

    def create(self):
        self._do_ansible()
        self.logger.info(f" Service {self.name} created. service_node={self._node}")

    def delete(self):
        self._do_ansible(delete=True)
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

        for n in range(0, len(nodes)):
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

        image = resource.get(Constants.RES_IMAGE)
        nodes = [rd for rd in resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]
                 if rd.attr == 'node']
        label = resource.get(Constants.LABEL)
        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)

        for n in range(0, len(nodes)):
            service_name = f"{self.name}-{service_name_prefix}{n}"
            service = JanusService(label=label, name=service_name, image=image,
                                   node=nodes[n].value, provider=self, logger=self.logger)
            service.delete()
