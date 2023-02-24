import json

from fabfed.model import Node
from fabfed.util.utils import get_logger
from .cloudlab_constants import *
from .cloudlab_exceptions import CloudlabException
from .cloudlab_provider import CloudlabProvider

logger = get_logger()


class CloudlabNode(Node):
    def __init__(self, *, label, name: str, provider: CloudlabProvider, network):
        super().__init__(label=label, name=name, image="", site="", flavor="")
        self._provider = provider
        self._net = network
        self.dataplane_ipv4 = None
        self.dataplane_ipv6 = None

    @property
    def provider(self):
        return self._provider

    @property
    def net(self):
        return self._net

    def create(self):
        import emulab_sslxmlrpc.client.api as api

        server = self.provider.rpc_server()
        exp_params = self.provider.experiment_params(self.net.name)
        exitval, response = api.experimentStatus(server, exp_params).apply()

        if exitval:
            raise CloudlabException(exitval=exitval, response=response)

        status = json.loads(response.value)
        logger.debug(json.dumps(status, indent=2))
        assert status['status'] == 'ready', f"status={status['status']}"

        node_info = status[AGGREGATE_STATUS][NODE_URI][NODES][NODE]
        self.mgmt_ip = node_info[IPV4]
        self.host = node_info[HOSTNAME]
        exitval, response = api.experimentManifests(server, exp_params).apply()

        if exitval:
            raise CloudlabException(exitval=exitval, response=response)

        status = json.loads(response.value)
        logger.debug(json.dumps(status, indent=2))

        import xmltodict

        data_dict = xmltodict.parse(status['urn:publicid:IDN+stitch.geniracks.net+authority+cm'])  # TODO
        logger.debug(f"RSPEC: {json.dumps(data_dict['rspec'], indent=2)}")

        nodes = data_dict['rspec']['node']

        for n in nodes:
            if n['@component_manager_id'] == NODE_URI:
                if n['interface']['ip']['@type'] == 'ipv4':
                    self.dataplane_ipv4 = n['interface']['ip']['@address']
                else:
                    self.dataplane_ipv6 = n['interface']['ip']['@address']

                self.site = n['jacks:site']['@id']
                break

    def delete(self):
        pass

    def get_reservation_state(self) -> str:
        pass

    def get_reservation_id(self) -> str:
        pass

    def add_route(self, subnet, gateway):
        pass

    def get_dataplane_address(self, network=None, interface=None, af=None):
        pass
