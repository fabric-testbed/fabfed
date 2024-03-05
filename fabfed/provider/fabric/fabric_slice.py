import logging
from typing import List

import fabfed.provider.api.dependency_util as util
from fabfed.model import Node, Network
from .fabric_network import NetworkBuilder, FabricNetwork
from .fabric_node import FabricNode, NodeBuilder
from .fabric_provider import FabricProvider
from ...util.constants import Constants
from .fabric_constants import *


# noinspection PyUnresolvedReferences
class FabricSlice:
    def __init__(self, *, provider: FabricProvider, logger: logging.Logger):
        self.provider = provider
        self.logger = logger
        self.notified_create = False
        self.slice_created = False
        self.slice_object = None
        self.retry = 10

    def init(self):
        from . import fabric_slice_helper

        self.slice_object = fabric_slice_helper.init_slice(self.provider.name)
        self.slice_created = self.slice_object.get_state() == "StableOK"

    @property
    def name(self) -> str:
        return self.provider.name

    @property
    def failed(self):
        return self.provider.failed

    @property
    def resource_listener(self):
        return self.provider.resource_listener

    @property
    def nodes(self) -> List[Node]:
        return self.provider.nodes

    @property
    def networks(self) -> List[Network]:
        return self.provider.networks

    @property
    def pending(self):
        return self.provider.pending

    def _add_network(self, resource: dict):
        label = resource.get(Constants.LABEL)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        net_type = resource.get(Constants.RES_TYPE)
        net_count = resource.get(Constants.RES_COUNT, 1)

        if net_count > 1:
            raise Exception(f"Count {net_count} > 1 is not supported for {net_type} {name_prefix}")

        network_builder = NetworkBuilder(label, self.provider, self.slice_object, name_prefix, resource)
        network_builder.handle_facility_port()

        temp = []

        if util.has_resolved_internal_dependencies(resource=resource, attribute='interface'):
            temp = util.get_values_for_dependency(resource=resource, attribute='interface')

        for node in temp:
            node.delegate.add_component(model=node.nic_model, name=FABRIC_STITCH_NET_IFACE_NAME)
            self.logger.info(f"Added {FABRIC_STITCH_NET_IFACE_NAME} interface to node {node.name}")

        network_builder.handle_network(temp)
        net = network_builder.build()
        self.provider.networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self, resource=net)

    def _add_node(self, resource: dict):
        node_count = resource.get(Constants.RES_COUNT, 1)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        label = resource.get(Constants.LABEL)

        for i in range(node_count):
            name = f"{name_prefix}{i}"
            node_builder = NodeBuilder(label, self.slice_object, name, resource)
            node = node_builder.build()
            self.nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(source=self, provider=self, resource=node)

    def add_resource(self, *, resource: dict):
        # TODO we need to handle modified config after slice has been created
        rtype = resource.get(Constants.RES_TYPE)

        if self.slice_created:
            label = resource.get(Constants.LABEL)

            if rtype == Constants.RES_TYPE_NODE.lower():
                node_count = resource.get(Constants.RES_COUNT, 1)
                name_prefix = resource.get(Constants.RES_NAME_PREFIX)

                for i in range(node_count):
                    name = f"{name_prefix}{i}"
                    delegate = self.slice_object.get_node(name)

                    if delegate is None:
                        raise Exception(f"Did not find node named {name}")

                    node = FabricNode(label=label, delegate=delegate)
                    self.nodes.append(node)

                    if self.resource_listener:
                        self.resource_listener.on_added(source=self, provider=self, resource=node)
            elif rtype == Constants.RES_TYPE_NETWORK.lower():
                name_prefix = resource.get(Constants.RES_NAME_PREFIX)
                delegate = self.slice_object.get_network(name_prefix)

                if delegate is None:
                    raise Exception(f"Did not find network named {name_prefix}")

                layer3 = resource.get(Constants.RES_LAYER3)
                peer_layer3 = resource.get(Constants.RES_PEER_LAYER3)
                peering = resource.get(Constants.RES_PEERING)
                net = FabricNetwork(label=label, delegate=delegate, layer3=layer3,
                                    peering=peering, peer_layer3=peer_layer3)

                self.provider.networks.append(net)

                if self.resource_listener:
                    self.resource_listener.on_added(source=self, provider=self, resource=net)
            else:
                raise Exception("Unknown resource ....")
            return

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self._add_network(resource)
        elif rtype == Constants.RES_TYPE_NODE.lower():
            self._add_node(resource)
        else:
            raise Exception("Unknown resource ....")

    def _submit_and_wait(self) -> str or None:
        try:
            self.logger.info(f"Submitting request for slice {self.name}")
            slice_id = self.slice_object.submit(wait=False)
            self.logger.info(f"Waiting for slice {self.name} to be stable")
            self.slice_object.wait(timeout=24 * 60, progress=True)

            try:
                self.slice_object.update()
                self.slice_object.post_boot_config()
            except Exception as e:
                self.logger.warning(f"Exception occurred while update/post_boot_config: {e}")

            self.logger.info(f"Slice provisioning successful {self.slice_object.get_state()}")

            # try:
            #     import datetime
            #     days = DEFAULT_RENEWAL_IN_DAYS
            #     end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S %z")
            #     self.slice_object.renew(end_date)
            # except Exception as e:
            #     self.logger.warning(f"Exception occurred while renewing for {days}: {e}")

            return slice_id
        except Exception as e:
            # self.logger.error(f"Exception occurred: {e}")
            raise e

    def _reload_nodes(self):
        from fabrictestbed_extensions.fablib.fablib import fablib

        temp = []
        self.slice_object = fablib.get_slice(name=self.provider.name)

        for node in self.nodes:
            delegate = self.slice_object.get_node(node.name)
            n = FabricNode(label=node.label, delegate=delegate)
            temp.append(n)

        self.provider._nodes = temp

    def _reload_networks(self):
        from fabrictestbed_extensions.fablib.fablib import fablib

        self.slice_object = fablib.get_slice(name=self.provider.name)

        temp = []

        for net in self.provider.networks:
            delegate = self.slice_object.get_network(net.name)
            fabric_network = FabricNetwork(label=net.label,
                                           delegate=delegate,
                                           layer3=net.layer3,
                                           peering=net.peering,
                                           peer_layer3=net.peer_layer3)

            temp.append(fabric_network)

        self.provider._networks = temp

    def _ensure_management_ips(self):
        for attempt in range(self.retry):
            mngmt_ips = []
            from fabrictestbed_extensions.fablib.fablib import fablib

            self.slice_object = fablib.get_slice(name=self.provider.name)

            for node in self.nodes:
                delegate = self.slice_object.get_node(node.name)
                mgmt_ip = delegate.get_management_ip()

                if mgmt_ip:
                    mngmt_ips.append(mgmt_ip)

            if len(self.nodes) == len(mngmt_ips):
                self.logger.info(f"Got All management ips for slice {self.provider.label}:{mngmt_ips}")
                break

            if attempt == self.retry:
                self.logger.warning(f"Giving up on checking node management ips ...slice "
                                    f"{self.provider.label} {self.nodes}:{mngmt_ips}:")
                break

            import time

            self.logger.info(
                f"Going to sleep. Will try checking node management ips ... slice {self.provider.label}")

            time.sleep(2)

    def _handle_node_networking(self):
        from fabrictestbed_extensions.fablib.fablib import fablib
        from . import fabric_slice_helper

        self._ensure_management_ips()

        for node in self.nodes:
            self.slice_object = fablib.get_slice(name=self.provider.name)
            delegate = self.slice_object.get_node(node.name)
            delegate.network_manager_stop()

        if INCLUDE_FABNETS:
            self.slice_object = fablib.get_slice(name=self.provider.name)
            for node in self.nodes:
                fabric_slice_helper.setup_fabric_networks(self.slice_object, node, node.v4net_name, node.v6net_name)

        if self.networks:
            from ipaddress import IPv4Network
            # self.slice_object = fablib.get_slice(name=self.provider.name)
            available_ips = self.networks[0].available_ips()

            if available_ips and self.networks[0].subnet:
                net_name = self.networks[0].name
                subnet = IPv4Network(self.networks[0].subnet)

                for node in self.nodes:
                    node_addr = available_ips.pop(0)
                    fabric_slice_helper.add_ip_address_to_network(self.slice_object,
                                                                  node, net_name, node_addr, subnet, self.retry)

            gateway = self.networks[0].gateway
            # self.slice_object = fablib.get_slice(name=self.provider.name)

            if gateway and self.networks[0].peer_layer3:
                for peer_layer3 in self.networks[0].peer_layer3:
                    subnet = peer_layer3.attributes.get(Constants.RES_SUBNET)

                    if subnet:
                        vpc_subnet = fabric_slice_helper.to_vpc_subnet(subnet)

                        for node in self.nodes:
                            fabric_slice_helper.add_route(self.slice_object, node, vpc_subnet, gateway, self.retry)

        self._reload_nodes()
        self._reload_networks()

    def create_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)

        if self.failed:
            raise Exception(f"fabric slice {self.name} has some failures. Refusing to create {label}")

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        if self.slice_created:
            state = self.slice_object.get_state()

            if not self.notified_create:
                self.logger.info(f"already provisioned. {self.name}: state={state}")
            else:
                self.logger.debug(f"already provisioned. {self.name}: state={state}")

            if not self.notified_create and self.resource_listener:
                self._handle_node_networking()

                for node in self.nodes:
                    self.resource_listener.on_created(source=self, provider=self, resource=node)

                for net in self.networks:
                    self.resource_listener.on_created(source=self, provider=self, resource=net)

                self.notified_create = True
            return

        self._submit_and_wait()
        self.slice_created = True

        self.logger.info(f"Going to sleep {FABRIC_SLEEP_AFTER_SUBMIT_OK} seconds:slice {self.provider.label}")
        import time
        # time.sleep(FABRIC_SLEEP_AFTER_SUBMIT_OK)
        # self.logger.info(f"Back from sleeping ... slice {self.provider.label}")

        self._handle_node_networking()

        if self.resource_listener:
            for node in self.nodes:
                self.resource_listener.on_created(source=self, provider=self, resource=node)

            for net in self.networks:
                self.resource_listener.on_created(source=self, provider=self, resource=net)

            self.notified_create = True

    def delete_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        self.logger.debug(f"Destroying resource {self.name}: {label}")

        if self.slice_object:
            self.slice_object.delete()
            self.slice_object = None
            self.slice_created = False
            self.logger.info(f"Destroyed slice {self.name}")  # TODO EMIT DELETE EVENT
