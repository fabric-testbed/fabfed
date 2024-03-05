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
        self.slice_modified = False

        from fabrictestbed_extensions.fablib.slice import Slice

        self.slice_object: Slice = None
        self.retry = 10
        self.existing_nodes = []
        self.existing_networks = []
        self._resource_state_map = {}

    def init(self, destroy_phase):
        from . import fabric_slice_helper

        self.slice_object = fabric_slice_helper.init_slice(self.provider.name, destroy_phase)

        if not destroy_phase:
            self.slice_created = self.slice_object.get_state() == "StableOK"
            self.existing_nodes = [node.get_name() for node in self.slice_object.get_nodes()]
            self.existing_networks = [net.get_name() for net in self.slice_object.get_networks()]

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
        label = resource[Constants.LABEL]
        name_prefix = resource[Constants.RES_NAME_PREFIX]

        if name_prefix in self.existing_networks:
            delegate = self.slice_object.get_network(name_prefix)
            assert delegate is not None, "expected to find network {name_prefix} in slice {self.name}"
            layer3 = resource.get(Constants.RES_LAYER3)
            peer_layer3 = resource.get(Constants.RES_PEER_LAYER3)
            peering = resource.get(Constants.RES_PEERING)
            net = FabricNetwork(label=label, delegate=delegate, layer3=layer3,
                                peering=peering, peer_layer3=peer_layer3)

            if util.has_resolved_internal_dependencies(resource=resource, attribute='interface'):
                temp = util.get_values_for_dependency(resource=resource, attribute='interface')

                for node in temp:
                    node.set_network_label(label)

            self.provider.networks.append(net)

            if self.resource_listener:
                self.resource_listener.on_added(source=self, provider=self.provider, resource=net)

            return

        network_builder = NetworkBuilder(label, self.provider, self.slice_object, name_prefix, resource)
        network_builder.handle_facility_port()
        temp = []
        if util.has_resolved_internal_dependencies(resource=resource, attribute='interface'):
            temp = util.get_values_for_dependency(resource=resource, attribute='interface')

            for node in temp:
                node.delegate.add_component(model=node.nic_model, name=FABRIC_STITCH_NET_IFACE_NAME)
                node.set_network_label(label)
                self.logger.info(f"Added {FABRIC_STITCH_NET_IFACE_NAME} interface to node {node.name}")

        network_builder.handle_network(temp)
        net = network_builder.build()
        self.provider.networks.append(net)
        self.slice_modified = self.slice_created

        if self.resource_listener:
            self.resource_listener.on_added(source=self, provider=self.provider, resource=net)

    def _add_node(self, resource: dict):
        node_count = resource[Constants.RES_COUNT]
        name_prefix = resource[Constants.RES_NAME_PREFIX]
        label = resource[Constants.LABEL]
        states = resource[Constants.SAVED_STATES]
        state_map = {}

        for state in states:
            state_map[state.attributes['name']] = state.attributes

        for i in range(node_count):
            name = f"{name_prefix}{i}"

            if name in self.existing_nodes:
                delegate = self.slice_object.get_node(name)
                assert delegate is not None, "expected to find node {name} in slice {self.name}"
                node = FabricNode(label=label, delegate=delegate, network_label="")

                if name in state_map:
                    from ipaddress import IPv4Address

                    attributes = state_map[name]
                    assert 'dataplane_ipv4' in attributes

                    if attributes['dataplane_ipv4']:
                        node.set_used_dataplane_ipv4(IPv4Address(attributes['dataplane_ipv4']))
            else:
                node_builder = NodeBuilder(label, self.slice_object, name, resource)
                node = node_builder.build()
                self.slice_modified = True

            self.nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(source=self, provider=self.provider, resource=node)

    def add_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)

        for state in resource[Constants.SAVED_STATES]:
            self._resource_state_map[state.attributes['name']] = state

        creation_details = resource[Constants.RES_CREATION_DETAILS]

        if not creation_details['in_config_file']:
            return

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self._add_network(resource)
        elif rtype == Constants.RES_TYPE_NODE.lower():
            self._add_node(resource)
        else:
            raise Exception("Unknown resource ....")

    def _submit_and_wait(self) -> str or None:
        self.logger.info(f"Submitting request for slice {self.name}")
        slice_id = self.slice_object.submit(wait=False)
        self.logger.info(f"Waiting for slice {self.name} to be stable")

        # TODO Timeout exceeded(360 sec).Slice: aes - chi - tacc - seq - 3(Configuring)

        try:
            self.slice_object.wait(timeout=24 * 60, progress=True)
        except Exception as e:
            state = self.slice_object.get_state()
            self.logger.warning(f"Exception occurred while waiting state={state}:{e}")
            raise e

        # try:
        #     self.slice_object.update()
        #     self.slice_object.post_boot_config()
        # except Exception as e:
        #     self.logger.warning(f"Exception occurred while update/post_boot_config: {e}")

        self.logger.info(f"Slice provisioning successful {self.slice_object.get_state()}")

        days = DEFAULT_RENEWAL_IN_DAYS

        # try:
        #     import datetime
        #     end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S %z")
        #     self.slice_object.renew(end_date)
        # except Exception as e:
        #     self.logger.warning(f"Exception occurred while renewing for {days}: {e}")

        return slice_id

    def _reload_nodes(self):
        from fabrictestbed_extensions.fablib.fablib import fablib

        temp = []
        self.slice_object = fablib.get_slice(name=self.provider.name)

        for node in self.nodes:
            delegate = self.slice_object.get_node(node.name)
            n = FabricNode(label=node.label, delegate=delegate, network_label=node.network_label)
            n.set_network_label(node.network_label)
            n.set_used_dataplane_ipv4(node.used_dataplane_ipv4())
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

    def _do_handle_node_networking(self):
        from fabrictestbed_extensions.fablib.fablib import fablib
        from . import fabric_slice_helper

        self._ensure_management_ips()

        for node in self.nodes:
            for attempt in range(self.retry):
                try:
                    self.slice_object = fablib.get_slice(name=self.provider.name)
                    delegate = self.slice_object.get_node(node.name)
                    delegate.network_manager_stop()
                    break
                except Exception as e:
                    if attempt == self.retry:
                        raise e

                    import time

                    self.logger.info(
                        f"Going to sleep. Will try stop network manager  ... slice {self.provider.label}")

                    time.sleep(2)

        if INCLUDE_FABNETS:
            self.slice_object = fablib.get_slice(name=self.provider.name)
            for node in self.nodes:
                fabric_slice_helper.setup_fabric_networks(self.slice_object, node, node.v4net_name, node.v6net_name)

        for network in self.networks:
            from ipaddress import IPv4Network

            available_ips: list = network.available_ips()

            if available_ips and network.subnet:
                net_name = network.name
                subnet = IPv4Network(network.subnet)
                temp = [n for n in self.nodes if n.network_label == network.label]

                for node in temp:
                    if node.used_dataplane_ipv4():
                        available_ips.remove(node.used_dataplane_ipv4())

                for node in temp:
                    node_addr = node.used_dataplane_ipv4() if node.used_dataplane_ipv4() else available_ips.pop(0)
                    fabric_slice_helper.add_ip_address_to_network(self.slice_object,
                                                                  node, net_name, node_addr, subnet, self.retry)
                    node.set_used_dataplane_ipv4(node_addr)

            if network.gateway and network.peer_layer3:
                for peer_layer3 in network.peer_layer3:
                    subnet = peer_layer3.attributes.get(Constants.RES_SUBNET)

                    if subnet:
                        vpc_subnet = fabric_slice_helper.to_vpc_subnet(subnet)

                        for node in self.nodes:
                            fabric_slice_helper.add_route(self.slice_object, node, vpc_subnet, network.gateway,
                                                          self.retry)

        self._reload_nodes()
        self._reload_networks()

    def _handle_node_networking(self):
        try:
            self._do_handle_node_networking()
        except Exception as e:
            raise Exception(
                f"Please Apply again. Fabric slice {self.name} has exception during post networking setup: {e}")

    def create_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)

        if self.failed:
            raise Exception(f"fabric slice {self.name} has some failures. Refusing to create {label}")

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        if self.slice_created:
            aset = set(self.existing_nodes)
            bset = {n.name for n in self.nodes}
            diff = aset - bset

            if diff:
                network_labels = {}
                for name, state in self._resource_state_map.items():
                    if state.type == Constants.RES_NODES:
                        network_labels[name] = state.attributes['network_label']

                for n in diff:
                    self.logger.info(f"removing node {n} from slice {self.name}")

                    if INCLUDE_FABNETS:
                        self.logger.info(f"removing node's fabnets: {n} from slice {self.name}")
                        self.slice_object.get_fim_topology().remove_network_service(f"{n}-{FABRIC_IPV4_NET_NAME}")
                        self.slice_object.get_fim_topology().remove_network_service(f"{n}-{FABRIC_IPV6_NET_NAME}")

                    node = self.slice_object.get_node(name=n)
                    temp = [net for net in self.networks if net.label == network_labels[n]]

                    for network in temp:
                        self.logger.info(f"removing node's interface: {n} from network {network.name}")
                        from fabrictestbed_extensions.fablib.network_service import NetworkService

                        delegate: NetworkService = network.delegate
                        node_interfaces = [i for i in node.get_interfaces()]
                        itf = node_interfaces[0]
                        delegate.remove_interface(itf)

                    self.slice_object.get_fim_topology().remove_node(name=n)
                    self.slice_modified = True
                    self.logger.info(f"Done  emoving node {n} from slice {self.name}")

            for network in [net for net in self.networks if net.name in self.existing_networks]:
                temp = (bset - aset)
                node_map = {}

                for node in self.nodes:
                    node_map[node.name] = node

                temp = [n for n in temp if node_map[n].network_label == network.label]

                for n in temp:
                    node = self.slice_object.get_node(name=n)
                    itf = node.add_component(model="NIC_Basic", name=FABRIC_STITCH_NET_IFACE_NAME).get_interfaces()[0]
                    self.logger.info(f"Added interface {itf.get_name()} to node {node.get_name()}")

                    from fabrictestbed_extensions.fablib.network_service import NetworkService

                    delegate: NetworkService = network.delegate
                    self.logger.info(f"adding interface {itf.get_name()} to {delegate.get_name()}")
                    delegate.add_interface(itf)
                    self.slice_modified = True

        if self.slice_created and not self.slice_modified:
            state = self.slice_object.get_state()

            if not self.notified_create:
                self.logger.info(f"already provisioned. {self.name}: state={state}")
            else:
                self.logger.debug(f"already provisioned. {self.name}: state={state}")

            if not self.notified_create and self.resource_listener:
                self._handle_node_networking()

                for node in self.nodes:
                    self.resource_listener.on_created(source=self, provider=self.provider, resource=node)

                for net in self.networks:
                    self.resource_listener.on_created(source=self, provider=self.provider, resource=net)

                self.notified_create = True
            return

        self._submit_and_wait()
        self.slice_created = True
        self.slice_modified = False
        self.existing_nodes = [n.name for n in self.nodes]
        self.existing_networks = [n.get_name() for n in self.networks]

        if self.nodes:
            self._handle_node_networking()

        if self.resource_listener:
            for node in self.nodes:
                self.resource_listener.on_created(source=self, provider=self.provider, resource=node)

            for net in self.networks:
                self.resource_listener.on_created(source=self, provider=self.provider, resource=net)

            self.notified_create = True

    def delete_resource(self, *, resource: dict):
        label = resource.get(Constants.LABEL)
        self.logger.debug(f"Destroying resource {self.name}: {label}")

        if self.slice_object:
            self.slice_object.delete()
            self.slice_created = False
            self.logger.info(f"Destroyed slice {self.name}")  # TODO EMIT DELETE EVENT

