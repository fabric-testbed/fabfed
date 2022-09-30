import logging

from fabfed.model import Slice
from fabfed.provider.chi.chi_network import ChiNetwork
from fabfed.provider.chi.chi_node import ChiNode
from fabfed.util.constants import Constants
from .chi_constants import DEFAULT_NETWORK, DEFAULT_FLAVOR


class ChiSlice(Slice):
    def __init__(self, *, label, name: str, logger: logging.Logger, key_pair: str, project_name: str):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.key_pair = key_pair
        self.project_name = project_name
        self.resource_listener = None
        self.slice_created = False

    def add_network(self, resource: dict):
        site = resource.get(Constants.RES_SITE)
        label = resource.get(Constants.LABEL)
        subnet = resource.get(Constants.RES_SUBNET)
        pool_start = resource.get(Constants.RES_NET_POOL_START, None)
        pool_end = resource.get(Constants.RES_NET_POOL_END, None)
        gateway = resource.get(Constants.RES_NET_GATEWAY, None)
        stitch_providers = resource.get(Constants.RES_NET_STITCH_PROVS, list())
        assert stitch_providers

        net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
        net = ChiNetwork(label=label, name=net_name, site=site, logger=self.logger,
                         slice_name=self.name, subnet=subnet, pool_start=pool_start, pool_end=pool_end,
                         gateway=gateway, stitch_provider=stitch_providers[0],
                         project_name=self.project_name)
        self._networks.append(net)

        if self.resource_listener:
            self.resource_listener.on_added(self, self.name, vars(net))

    def add_node(self, resource: dict):
        site = resource.get(Constants.RES_SITE)
        network = resource.get(Constants.RES_NETWORK, DEFAULT_NETWORK)

        if not isinstance(network, str):
            found = False

            for net in self._networks:
                if net.label == network.resource.label:
                    net_vars = vars(net)
                    network = net_vars[network.attribute]
                    found = True
                    break

            if not found:
                raise Exception(f"could not resolve internal network dependency {network}")

        node_count = resource.get(Constants.RES_COUNT, 1)
        image = resource.get(Constants.RES_IMAGE)
        node_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
        flavor = resource.get(Constants.RES_FLAVOR, DEFAULT_FLAVOR)
        label = resource.get(Constants.LABEL)

        for n in range(0, node_count):
            node_name = f"{node_name_prefix}{n}"
            node = ChiNode(label=label, name=node_name, image=image, site=site, flavor=flavor, logger=self.logger,
                           key_pair=self.key_pair, slice_name=self.name, network=network,
                           project_name=self.project_name)
            self._nodes.append(node)

            if self.resource_listener:
                self.resource_listener.on_added(self, self.name, vars(node))

    def add_resource(self, *, resource: dict):
        rtype = resource.get(Constants.RES_TYPE)
        if rtype == Constants.RES_TYPE_NETWORK.lower():
            self.add_network(resource)
        else:
            self.add_node(resource)

    def create(self):
        if self.slice_created:
            self.logger.debug(f"already provisioned. Will not bother to create any resource to {self.name}")
            return

        for n in self._networks:
            n.create()

            if self.resource_listener:
                self.resource_listener.on_created(self, self.name, vars(n))

        for n in self._nodes:
            n.create()

        for n in self._nodes:
            n.wait_for_active()

            if self.resource_listener:
                self.resource_listener.on_created(self, self.name, vars(n))

        self.slice_created = True

    # noinspection PyTypeChecker
    def delete_resource(self, *, resource: dict):
        # name = resource['name']
        site = resource[Constants.RES_SITE]
        label = resource.get(Constants.LABEL)
        rtype = resource.get(Constants.RES_TYPE)

        if rtype == Constants.RES_TYPE_NETWORK.lower():
            net_name = f'{self.name}-{resource.get(Constants.RES_NAME_PREFIX)}'
            self.logger.debug(f"Deleting network: {net_name} at site {site}")
            net = ChiNetwork(label=label, name=net_name, site=site, logger=self.logger,
                             slice_name=self.name, subnet=None, pool_start=None, pool_end=None,
                             gateway=None, stitch_provider=None,
                             project_name=self.project_name)
            net.delete()
            self.logger.info(f"Deleted network: {net_name} at site {site}")
        else:
            node_count = resource.get(Constants.RES_COUNT, 1)

            for n in range(0, node_count):
                node_name_prefix = resource.get(Constants.RES_NAME_PREFIX)
                node_name = f"{node_name_prefix}{n}"
                self.logger.debug(f"Deleting node: {node_name} at site {site}")

                node = ChiNode(label=label, name=node_name, image=None, site=site, flavor=None, logger=self.logger,
                               key_pair=None, slice_name=self.name, network=None,
                               project_name=self.project_name)
                node.delete()
                self.logger.info(f"Deleted node: {node_name} at site {site}")
