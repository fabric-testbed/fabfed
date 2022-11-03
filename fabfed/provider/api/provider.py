import logging
from abc import ABC, abstractmethod
from typing import List, Dict

from fabfed.model import Node, Network, Service, ResolvedDependency
from fabfed.model.state import ProviderState
from fabfed.util.constants import Constants


class Provider(ABC):
    def __init__(self, *, type, label, name, logger: logging.Logger, config: dict):
        self.label = label
        self.type = type
        self.name = name
        self.logger = logger
        self.config = config
        self.resource_listener = None

        self._nodes = list()
        self._networks = list()
        self._services = list()

        self._pending = []
        self._failed = {}
        self._added = []

    @property
    def nodes(self) -> List[Node]:
        return self._nodes

    @property
    def networks(self) -> List[Network]:
        return self._networks

    @property
    def services(self) -> List[Service]:
        return self._services

    @property
    def pending(self) -> List:
        return self._pending

    @property
    def failed(self) -> Dict:
        return self._failed

    def set_resource_listener(self, resource_listener):
        self.resource_listener = resource_listener

    def on_added(self, *, source, provider, resource: object):
        assert self != source
        assert provider
        assert resource
        pass

    def on_deleted(self, *, source, provider, resource: object):
        assert self != source
        assert provider
        assert resource
        pass

    def on_created(self, *, source, provider, resource: object):
        assert self != source
        assert provider

        resource_dict = vars(resource)

        for pending_resource in self.pending.copy():
            for dependency in pending_resource[Constants.EXTERNAL_DEPENDENCIES]:
                if dependency.resource.label == resource_dict[Constants.LABEL]:
                    try:
                        value = resource if not dependency.attribute else resource_dict.get(dependency.attribute)
                        label = pending_resource[Constants.LABEL]
                        self.logger.info(
                            f"Resolving: {dependency} for {label}: value={value} using {self.label}")

                        if value:
                            resolved_dependencies = pending_resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]

                            if isinstance(value, list):
                                resolved_dependency = ResolvedDependency(attr=dependency.key, value=tuple(value))
                            else:
                                resolved_dependency = ResolvedDependency(attr=dependency.key, value=value)

                            resolved_dependencies.append(resolved_dependency)
                            self.logger.info(
                                f"Resolved dependency {dependency} for {label} using {self.label}")

                            if len(pending_resource[Constants.EXTERNAL_DEPENDENCIES]) == len(
                                    pending_resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]):
                                self.pending.remove(pending_resource)
                                self.logger.info(f"Removing {label} from pending using {self.label}")
                                self.add_resource(resource=pending_resource)
                        else:
                            self.logger.warning(
                                f"Could not resolve {dependency} for {label} using {self.label}")
                    except Exception as e:
                        self.logger.warning(
                            f"Exception occurred while resolving dependency: {e} using {self.label}")
                        self.logger.warning(e, exc_info=True)

    def add_resource(self, *, resource: dict):
        count = resource.get(Constants.RES_COUNT, 1)
        label = resource.get(Constants.LABEL)

        if count < 1:
            self.logger.info(f"Skipping {label}. using {self.label}: count={count}")
            return
        elif len(resource[Constants.EXTERNAL_DEPENDENCIES]) > len(resource[Constants.RESOLVED_EXTERNAL_DEPENDENCIES]):
            self.logger.info(f"Adding  {label} to pending using {self.label}")
            assert resource not in self.pending, f"Did not expect {label} to be in pending list using {self.label}"
            self.pending.append(resource)
            return

        try:
            self.do_add_resource(resource=resource)
            self._added.append(label)
        except Exception as e:
            label = resource.get(Constants.LABEL)

            self.failed[label] = 'ADD'
            raise e

    def create_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)

        if label in self._added:
            try:
                self.do_create_resource(resource=resource)
            except Exception as e:
                self.failed[label] = 'CREATE'
                raise e

    def delete_resource(self, *, resource: dict):
        try:
            self.do_delete_resource(resource=resource)
        except Exception as e:
            label = resource.get(Constants.LABEL)

            self.failed[label] = 'DELETE'
            raise e

    def get_state(self) -> ProviderState:
        from fabfed.model.state import NetworkState, NodeState, ServiceState

        net_states = []

        def cleanup_attrs(attrs):
            attributes = attrs.copy()
            attributes.pop('logger', None)
            attributes.pop('label')
            attributes = {k: v for k, v in attributes.items() if not k.startswith('_')}
            return attributes

        for net in self.networks:
            net_state = NetworkState(label=net.label, attributes=cleanup_attrs(vars(net)))
            net_states.append(net_state)

        node_states = []

        for node in self.nodes:
            node_state = NodeState(label=node.label, attributes=cleanup_attrs(vars(node)))
            node_states.append(node_state)

        service_states = []

        for service in self.services:
            service_state = ServiceState(label=service.label, attributes=cleanup_attrs(vars(service)))
            service_states.append(service_state)

        pending = []
        from fabfed.util.parser import DependencyInfo

        for resource in self.pending:
            copy = {}

            for key, value in resource.items():
                if key in [Constants.EXTERNAL_DEPENDENCIES, Constants.RESOLVED_EXTERNAL_DEPENDENCIES]:
                    continue

                if isinstance(value, DependencyInfo):  # TODO Add Yaml dumper/loader to parser.DependencyInfo
                    value = str(value)

                copy[key] = value

            pending.append(copy)

        return ProviderState(self.label, dict(name=self.name), net_states, node_states, service_states,
                             pending, self.failed)

    def list_networks(self) -> list:
        from tabulate import tabulate

        table = []
        for network in self.networks:
            table.append([network.get_reservation_id(),
                          network.get_name(),
                          network.get_site()
                          ])

        return tabulate(table, headers=["ID", "Name", "Site"])

    def list_nodes(self) -> list:
        from tabulate import tabulate

        table = []
        for node in self._nodes:
            table.append([node.get_reservation_id(),
                          node.get_name(),
                          node.get_site(),
                          node.get_flavor(),
                          node.get_image(),
                          node.get_management_ip(),
                          node.get_reservation_state()
                          ])

        return tabulate(table, headers=["ID", "Name", "Site", "Flavor", "Image",
                                        "Management IP", "State"])

    @abstractmethod
    def setup_environment(self):
        pass

    @abstractmethod
    def do_add_resource(self, *, resource: dict):
        pass

    @abstractmethod
    def do_create_resource(self, *, resource: dict):
        pass

    @abstractmethod
    def do_delete_resource(self, *, resource: dict):
        pass
