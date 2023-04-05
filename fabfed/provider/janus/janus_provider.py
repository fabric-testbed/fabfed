import os
import json
import logging

from fabfed.model import Service, Resource, Node
from fabfed.provider.api.provider import Provider
from fabfed.util.constants import Constants
from fabfed.util.utils import get_inventory_dir
from fabfed.util import state
from fabfed.provider.janus.util.ansible_helper import AnsibleHelper


class JanusService(Service):
    def __init__(self, *, label, name: str, image, nodes, provider, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.image = image
        self.created = False
        self._nodes = nodes
        self._provider = provider

    def _do_ansible(self, delete=False):
        friendly_name = self._provider.name
        host_file = get_inventory_dir(friendly_name)
        script_dir = os.path.dirname(__file__)
        helper = AnsibleHelper(host_file, self.logger)
        janus_vars = self._provider.config
        helper.set_extra_vars(janus_vars)
        if delete:
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["janus-del"])
        else:
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["docker", "janus"])
            helper.run_playbook(os.path.join(script_dir, "ansible/janus.yml"), tags=["janus-add"])
            self.created = True

    def create(self):
        self._do_ansible()
        self.logger.info(f" Service {self.name} created. service_nodes={[n.name for n in self._nodes]}")

    def delete(self):
        self._do_ansible(delete=True)
        self.logger.info(f" Service {self.name} deleted. service_nodes={self._nodes}")


class JanusProvider(Provider):
    def setup_environment(self):
        pass

    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, label=label, name=name, logger=logger, config=config)
        credential_file = self.config.get(Constants.CREDENTIAL_FILE)

        if credential_file:
            from fabfed.util import utils

            profile = self.config.get(Constants.PROFILE)
            config = utils.load_yaml_from_file(credential_file)
            self.config = config[profile]

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

        label = resource.get(Constants.LABEL)
        image = resource.get(Constants.RES_IMAGE)
        nodes = [rd for rd in resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]
                 if rd.attr == 'node']
        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)

        service_nodes = [n for i in nodes for n in i.value]
        service_name = f"{self.name}-{service_name_prefix}"
        service = JanusService(label=label, name=service_name, image=image,
                               nodes=service_nodes, provider=self, logger=self.logger)
        self._services.append(service)
        self.resource_listener.on_added(source=self, provider=self, resource=service)

    def do_create_resource(self, *, resource: dict):
        """
        Called by add_resource(self, *, resource: dict) if resource has no external dependencies
        @param resource: resource attributes
        """
        label = resource.get(Constants.LABEL)
        states = resource.get(Constants.SAVED_STATES)
        created = True
        for s in states:
            if s.attributes.get('created', False) == True:
                created = True

        self.logger.info(f"Creating resource={resource} using {self.label}")

        temp = [service for service in self.services if service.label == label]

        for service in temp:
            if created:
                self.logger.info(f"Service {label} is already in created state, skipping create task")
            else:
                service.create()
            self.resource_listener.on_created(source=self, provider=self, resource=service)

    def do_delete_resource(self, *, resource: dict):
        self.logger.info(f"Deleting resource={resource} using {self.label}")

        image = resource.get(Constants.RES_IMAGE)
        nodes = [rd for rd in resource[Constants.EXTERNAL_DEPENDENCY_STATES]]
        service_nodes = [n.attributes.get('name') for n in nodes]
        label = resource.get(Constants.LABEL)
        service_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        service_name = f"{self.name}-{service_name_prefix}"
        service = JanusService(label=label, name=service_name, image=image,
                               nodes=service_nodes, provider=self, logger=self.logger)
        service.delete()
        self.resource_listener.on_deleted(source=self, provider=self, resource=service)
