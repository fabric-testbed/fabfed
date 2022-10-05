import logging

from fabfed.model import Slice
from ...util.constants import Constants
from .fabric_network import NetworkBuilder, FabricNetwork
from .fabric_node import FabricNode, NodeBuilder


class FabricSlice(Slice):
    def __init__(self, *, label, name: str, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.notified_create = False

        from fabrictestbed_extensions.fablib.fablib import fablib

        # noinspection PyBroadException
        try:
            self.slice_object = fablib.get_slice(name=name)
        except Exception:
            self.slice_object = None

        if self.slice_object:
            self.slice_created = True
        else:
            self.slice_created = False
            self.slice_object = fablib.new_slice(name)

    def add_network(self, resource: dict):
        label = resource.get(Constants.LABEL)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        network_builder = NetworkBuilder(label, self.slice_object, name_prefix, resource)
        network_builder.handle_facility_port()
        interfaces = []   # TODO handle this internal dependency properly

        for node in self._nodes:
            interfaces.append(node.get_interfaces()[0])

        assert len(interfaces) > 0
        network_builder.handle_l2network(interfaces)  # This throws an exception in network_service.py
        # network_builder.handle_l3network(interfaces)
        net = network_builder.build()
        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(self, self.name, vars(net))

    def add_node(self, resource: dict):
        node_count = resource.get(Constants.RES_COUNT, 1)
        name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        nic_model = resource.get(Constants.RES_NIC_MODEL, 'NIC_Basic')
        label = resource.get(Constants.LABEL)

        for i in range(node_count):
            name = f"{name_prefix}{i}"
            node_builder = NodeBuilder(label, self.slice_object, name, resource)
            node_builder.add_component(model=nic_model, name="nic1")
            node = node_builder.build()
            self._nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(self, self.name, vars(node))

    def do_add_resource(self, *, resource: dict):
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
                    fabric_node = FabricNode(label=label, delegate=delegate)
                    self._nodes.append(fabric_node)

                    if self.resource_listener:
                        self.resource_listener.on_added(self, self.name, vars(fabric_node))
            elif rtype == Constants.RES_TYPE_NETWORK.lower():
                delegates = self.slice_object.get_network_services()
                # noinspection PyTypeChecker
                from ipaddress import IPv4Address, IPv4Network

                subnet = IPv4Network(resource.get(Constants.RES_SUBNET))
                pool_start = IPv4Address(resource.get(Constants.RES_NET_POOL_START))
                pool_end = IPv4Address(resource.get(Constants.RES_NET_POOL_END))

                fabric_network = FabricNetwork(label=label,
                                               delegate=delegates[0],
                                               subnet=subnet,
                                               pool_start=pool_start,
                                               pool_end=pool_end)
                self._networks.append(fabric_network)

                if self.resource_listener:
                    self.resource_listener.on_added(self, self.name, vars(fabric_network))
            else:
                raise Exception("Unknown resource ....")
            return

        rtype = resource.get(Constants.RES_TYPE)
        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        elif rtype == Constants.RES_TYPE_NODE.lower():
            self.add_node(resource)
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
            self.logger.error(f"Exception occurred: {e}")
            raise e

    def do_create_resource(self, *, resource: dict):
        if self.failed:
            raise Exception(str(self.failed))

        if self.slice_created:
            state = self.slice_object.get_state()

            if not self.notified_create:
                self.logger.info(f"already provisioned. {self.name}: state={state}")
            else:
                self.logger.debug(f"already provisioned. {self.name}: state={state}")

            if not self.notified_create and self.resource_listener:
                for node in self.nodes:
                    self.resource_listener.on_created(self, self.name, vars(node))

                for net in self.networks:
                    self.resource_listener.on_created(self, self.name, vars(net))

                self.notified_create = True

            return

        if self.pending:
            self.logger.warning(f"still have pending {len(self.pending)} resources")
            return

        self._submit_and_wait()
        self.slice_created = True

        temp = []

        for node in self.nodes:
            delegate = self.slice_object.get_node(node.name)
            temp.append(FabricNode(label=node.label, delegate=delegate))

        self._nodes = temp

        temp = []

        for net in self._networks:
            delegate = self.slice_object.get_network(net.name)
            from ipaddress import IPv4Address, IPv4Network

            fabric_network = FabricNetwork(label=net.label,
                                           delegate=delegate,
                                           subnet=IPv4Network(net.subnet),
                                           pool_start=IPv4Address(net.pool_start),
                                           pool_end=IPv4Address(net.pool_end))
            temp.append(fabric_network)

        self._networks = temp

        if self.networks:
            from ipaddress import IPv4Network
            available_ips = self._networks[0].available_ips()
            subnet = IPv4Network(self._networks[0].subnet)
            net_name = self._networks[0].name

            for node in self._nodes:
                iface = node.get_interface(network_name=net_name)
                node_addr = available_ips.pop(0)
                iface.ip_addr_add(addr=node_addr, subnet=subnet)

        if self.resource_listener:
            for node in self.nodes:
                self.resource_listener.on_created(self, self.name, vars(node))

            for net in self.networks:
                self.resource_listener.on_created(self, self.name, vars(net))

            self.notified_create = True

    def do_delete_resource(self, *, resource: dict):
        if self.slice_created:
            self.slice_object.delete()
            self.slice_created = False
            self.logger.info(f"Destroyed slice  {self.name}")
