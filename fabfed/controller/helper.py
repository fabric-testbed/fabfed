from fabfed.provider.api.provider import Provider
from fabfed.provider.api.resource_event_listener import ResourceListener


class ControllerResourceListener(ResourceListener):
    def __init__(self, providers):
        self.providers = providers

    def on_added(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_added(source=self, provider=provider, resource=resource)

    def on_created(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_created(source=self, provider=provider, resource=resource)

    def on_deleted(self, *, source, provider: Provider, resource: object):
        for temp_provider in self.providers:
            temp_provider.on_deleted(source=self, provider=provider, resource=resource)


def partition_layer3_config(*, networks: list):
    from ipaddress import IPv4Address
    from ..util.constants import Constants
    from fabfed.util.config_models import Config

    if len(networks) <= 1:
        return

    layer3 = networks[0].attributes.get(Constants.RES_LAYER3)

    if not layer3.attributes.get(Constants.RES_LAYER3_DHCP_START):
        return

    if "/" in layer3.attributes.get(Constants.RES_LAYER3_DHCP_START):
        return

    if "/" in layer3.attributes.get(Constants.RES_LAYER3_DHCP_END):
        return

    layer3 = networks[0].attributes.get(Constants.RES_LAYER3)
    dhcp_start = int(IPv4Address(layer3.attributes.get(Constants.RES_LAYER3_DHCP_START)))
    last = dhcp_end = int(IPv4Address(layer3.attributes.get(Constants.RES_LAYER3_DHCP_END)))
    interval = int((dhcp_end - dhcp_start) / len(networks))

    for index, network in enumerate(networks):
        layer3_config = Config(layer3.type, f"{layer3.name}-{index}", layer3.attributes.copy())
        dhcp_end = dhcp_start + interval

        if dhcp_end > last:
            dhcp_end = last

        layer3_config.attributes[Constants.RES_LAYER3_DHCP_START] = str(IPv4Address(dhcp_start))
        layer3_config.attributes[Constants.RES_LAYER3_DHCP_END] = str(IPv4Address(dhcp_end))
        network.attributes[Constants.RES_LAYER3] = layer3_config
        dhcp_start = dhcp_end + 1
