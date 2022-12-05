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
        from fabrictestbed_extensions.fablib.fablib import fablib

        # noinspection PyBroadException
        try:
            self.slice_object = fablib.get_slice(name=self.provider.name)
            self.logger.info(f"Found slice {self.provider.name}:state={self.slice_object.get_state()}")
        except Exception:
            self.slice_object = None

        if self.slice_object:
            self.slice_created = True
        else:
            self.slice_created = False
            self.slice_object = fablib.new_slice(name=self.provider.name)

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
        network_builder = NetworkBuilder(label, self.slice_object, name_prefix, resource)
        network_builder.handle_facility_port()
        assert util.has_resolved_internal_dependencies(resource=resource, attribute='interface')
        interfaces = []
        temp = util.get_values_for_dependency(resource=resource, attribute='interface')

        for node in temp:
            interfaces.append(node.get_interfaces()[0])

        assert len(interfaces) > 0
        network_builder.handle_l2network(interfaces)
        if net_type == Constants.RES_NET_LAYER3:
            network_builder.handle_l3network(interfaces)
        net = network_builder.build()
        self.provider.networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self, resource=net)

    def _add_node(self, resource: dict):
        node_count = resource.get(Constants.RES_COUNT, 1)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        nic_model = resource.get(Constants.RES_NIC_MODEL, 'NIC_Basic')
        label = resource.get(Constants.LABEL)

        for i in range(node_count):
            name = f"{name_prefix}{i}"
            node_builder = NodeBuilder(label, self.slice_object, name, resource)
            node_builder.add_component(model=nic_model, name="nic1")
            node = node_builder.build()
            self.nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(source=self, provider=self, resource=node)

    def add_resource(self, *, resource: dict):
        # TODO we need to handle modified config after slice has been created. now exception will be thrown
        if self.slice_created:
            rtype = resource.get(Constants.RES_TYPE)
            label = resource.get(Constants.LABEL)

            if rtype == Constants.RES_TYPE_NODE.lower():
                node_count = resource.get(Constants.RES_COUNT, 1)
                name_prefix = resource.get(Constants.RES_NAME_PREFIX)

                for i in range(node_count):
                    name = f"{name_prefix}{i}"
                    delegate = self.slice_object.get_node(name)
                    node = FabricNode(label=label, delegate=delegate)
                    self.nodes.append(node)

                    if self.resource_listener:
                        self.resource_listener.on_added(source=self, provider=self, resource=node)
            elif rtype == Constants.RES_TYPE_NETWORK.lower():
                delegates = self.slice_object.get_network_services()
                # noinspection PyTypeChecker
                from ipaddress import IPv4Address, IPv4Network

                subnet = IPv4Network(resource.get(Constants.RES_SUBNET))
                pool_start = IPv4Address(resource.get(Constants.RES_NET_POOL_START))
                pool_end = IPv4Address(resource.get(Constants.RES_NET_POOL_END))
                net = FabricNetwork(label=label,
                                    delegate=delegates[0],
                                    subnet=subnet,
                                    pool_start=pool_start,
                                    pool_end=pool_end)
                self.provider.networks.append(net)

                if self.resource_listener:
                    self.resource_listener.on_added(source=self, provider=self, resource=net)
            else:
                raise Exception("Unknown resource ....")
            return

        rtype = resource.get(Constants.RES_TYPE)
        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self._add_network(resource)
        elif rtype == Constants.RES_TYPE_NODE.lower():
            self._add_node(resource)
        else:
            raise Exception("Unknown resource ....")

    def _submit_and_wait(self) -> str or None:
        try:
            # TODO Check if the slice has more than one site then add a layer2 network
            self.logger.info(f"Submitting request for slice {self.name}")
            slice_id = self.slice_object.submit(wait=False)
            self.logger.info(f"Waiting for slice {self.name} to be stable")
            self.slice_object.wait(progress=True)

            try:
                self.slice_object.update()
                self.slice_object.post_boot_config()
            except Exception as e:
                self.logger.warning(f"Exception occurred while update/post_boot_config: {e}")

            self.logger.info(f"Slice provisioning successful {self.slice_object.get_state()}")
            return slice_id
        except Exception as e:
            # self.logger.error(f"Exception occurred: {e}")
            raise e

    def _setup_networks(self, node):
        v4_net = self.slice_object.get_network(name=f"{node.name}-{FABRIC_IPV4_NET_NAME}")
        v4_net_available_ips = v4_net.get_available_ips()
        v6_net = self.slice_object.get_network(name=f"{node.name}-{FABRIC_IPV6_NET_NAME}")
        v6_net_available_ips = v6_net.get_available_ips()

        iface_v4 = node.get_interface(network_name=f"{node.name}-{FABRIC_IPV4_NET_NAME}")
        iface_v6 = node.get_interface(network_name=f"{node.name}-{FABRIC_IPV6_NET_NAME}")

        addr_v4 = v4_net_available_ips.pop(0)
        addr_v6 = v6_net_available_ips.pop(0)

        iface_v4.ip_addr_add(addr=addr_v4, subnet=v4_net.get_subnet())
        iface_v6.ip_addr_add(addr=addr_v6, subnet=v6_net.get_subnet())

        node.add_route(subnet=FABRIC_PRIVATE_IPV4_SUBNET, gateway=v4_net.get_gateway())
        node.add_route(subnet=FABRIC_PUBLIC_IPV6_SUBNET, gateway=v6_net.get_gateway())

    def create_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)

        if self.failed:
            raise Exception(f"fabric slice {self.name} has some failures. Refusing to create {label}")

        if self.slice_created:
            state = self.slice_object.get_state()

            if not self.notified_create:
                self.logger.info(f"already provisioned. {self.name}: state={state}")
            else:
                self.logger.debug(f"already provisioned. {self.name}: state={state}")

            if not self.notified_create and self.resource_listener:
                for node in self.nodes:
                    self.resource_listener.on_created(source=self, provider=self, resource=node)

                for net in self.networks:
                    self.resource_listener.on_created(source=self, provider=self, resource=net)

                self.notified_create = True

            return

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        self._submit_and_wait()
        self.slice_created = True

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
                break

            if attempt == self.retry:
                self.logger.warning(f"Giving up on checking node management ips ...slice "
                                    f"{self.provider.label} {self.nodes}:{mngmt_ips}:")
                break

            import time

            self.logger.info(
                f"Going to sleep. Will try checking node management ips ...slice {self.provider.label}")

            time.sleep(2)

        temp = []

        for node in self.nodes:
            delegate = self.slice_object.get_node(node.name)
            # Setup FABnetv4/v6 nets
            n = FabricNode(label=node.label, delegate=delegate)
            self._setup_networks(n)
            temp.append(n)

        self.provider._nodes = temp

        temp = []

        for net in self.provider.networks:
            delegate = self.slice_object.get_network(net.name)
            from ipaddress import IPv4Address, IPv4Network

            fabric_network = FabricNetwork(label=net.label,
                                           delegate=delegate,
                                           subnet=IPv4Network(net.subnet),
                                           pool_start=IPv4Address(net.pool_start),
                                           pool_end=IPv4Address(net.pool_end))
            temp.append(fabric_network)

        self.provider._networks = temp

        if self.networks:
            from ipaddress import IPv4Network
            available_ips = self.networks[0].available_ips()
            subnet = IPv4Network(self.networks[0].subnet)
            net_name = self.networks[0].name

            for node in self.nodes:
                iface = node.get_interface(network_name=net_name)
                node_addr = available_ips.pop(0)
                iface.ip_addr_add(addr=node_addr, subnet=subnet)

        if self.resource_listener:
            for node in self.nodes:
                self.resource_listener.on_created(source=self, provider=self, resource=node)

            for net in self.networks:
                self.resource_listener.on_created(source=self, provider=self, resource=net)

            self.notified_create = True

    def delete_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        self.logger.debug(f"Destroying resource {self.name}: {label}")

        if self.slice_created:
            self.slice_object.delete()
            self.slice_created = False
            self.logger.info(f"Destroyed slice {self.name}")  # TODO EMIT DELETE EVENT
