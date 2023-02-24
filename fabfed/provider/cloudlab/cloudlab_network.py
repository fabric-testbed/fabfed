import json

from fabfed.model import Network
from fabfed.util.utils import get_logger
from .cloudlab_constants import *
from .cloudlab_exceptions import CloudlabException
from .cloudlab_provider import CloudlabProvider

logger = get_logger()


class CloudNetwork(Network):
    def __init__(self, *, label, name: str, provider: CloudlabProvider, profile: str, interfaces):
        super().__init__(label=label, name=name, site="")
        self.profile = profile
        self._provider = provider
        self.interface = interfaces or []

    @property
    def provider(self):
        return self._provider

    @property
    def project(self):
        return self.provider.config[CLOUDLAB_PROJECT]

    def params(self):
        params = {
            "profile": f"{self.project},{self.profile}",
            "proj": self.project,
            "name": self.name,
            "asjson": True,
        }

        return params

    def create(self):
        import time
        import emulab_sslxmlrpc.client.api as api
        import emulab_sslxmlrpc.xmlrpc as xmlrpc

        server = self.provider.rpc_server()
        exp_params = self.provider.experiment_params(self.name)
        exitval, response = api.experimentStatus(server, exp_params).apply()

        if exitval == xmlrpc.RESPONSE_SEARCHFAILED:
            logger.info(f"Network {self.name} not found, creating...")
            params = self.params()

            if self.interface:
                vlan = self.interface[0]['vlan']
                params['bindings'] = json.dumps(dict(vlan=str(vlan)))

            exitval, response = api.startExperiment(server, params).apply()

            if exitval:
                raise CloudlabException(exitval=exitval, response=response)

        elif exitval == xmlrpc.RESPONSE_SUCCESS or exitval == xmlrpc.RESPONSE_ALREADYEXISTS:
            logger.info("Network already exists, checking status")
        else:
            raise CloudlabException(exitval=exitval, response=response)

        while True:
            exitval, response = api.experimentStatus(server, exp_params).apply()

            if exitval:
                code = response.value

                if code == api.GENIRESPONSE_REFUSED or code == api.GENIRESPONSE_NETWORK_ERROR:
                    logger.debug("Server is offline, waiting for a bit")
                    continue
                elif code == api.GENIRESPONSE_BUSY:
                    logger.debug("Experiment is busy, waiting for a bit")
                    continue
                elif code == api.GENIRESPONSE_SEARCHFAILED:
                    raise CloudlabException(message="Experiment is gone", exitval=exitval, response=response)
                else:
                    raise CloudlabException(exitval=exitval, response=response)

            status = json.loads(response.value)
            logger.info(json.dumps(status, indent=2))

            if status["status"] == "failed":
                raise CloudlabException(exitval=exitval, response=response, message="Experiment failed to instantiate")
            elif status["status"] == "ready":
                if "execute_status" not in status:
                    logger.info("No execute service to wait for!")
                    break

                total = status["execute_status"]["total"]
                finished = status["execute_status"]["finished"]

                if total != finished:
                    logger.info("Still waiting for execute service to finish")
                    continue

                logger.info("Execute services have finished")
                break

            logger.info("Still waiting for experiment to be ready")
            time.sleep(CLOUDLAB_SLEEP_TIME)

        exitval, response = api.experimentManifests(server, exp_params).apply()

        if exitval:
            raise CloudlabException(exitval=exitval, response=response)

        status = json.loads(response.value)
        logger.debug(json.dumps(status, indent=2))

        import xmltodict

        data_dict = xmltodict.parse(status['urn:publicid:IDN+stitch.geniracks.net+authority+cm'])  # TODO
        logger.info(f"RSPEC: {json.dumps(data_dict['rspec'], indent=2)}")
        link = data_dict['rspec']['link']
        # logger.info(f"LINK: {json.dumps(link, indent=2)}")
        self.interface = [dict(id='', provider=self.provider.type, vlan=link['@vlantag'])]

        nodes = data_dict['rspec']['node']

        for n in nodes:
            if n['@component_manager_id'] != NODE_URI:
                self.dtn = n['interface']['ip']['@address']
                self.dtn_site = n['jacks:site']['@id']
                break

    def delete(self):
        import emulab_sslxmlrpc.client.api as api
        import emulab_sslxmlrpc.xmlrpc as xmlrpc
        import time

        server = self.provider.rpc_server()
        exp_params = self.provider.experiment_params(self.name)
        exitval, response = api.terminateExperiment(server, exp_params).apply()

        if exitval == xmlrpc.RESPONSE_SUCCESS:
            while True:
                exitval, response = api.experimentStatus(server, exp_params).apply()

                if exitval == xmlrpc.RESPONSE_SEARCHFAILED:
                    break

                logger.info("Still waiting for experiment to be terminated")
                time.sleep(CLOUDLAB_SLEEP_TIME)

        if exitval != xmlrpc.RESPONSE_SEARCHFAILED:
            raise CloudlabException(exitval=exitval, response=response)
