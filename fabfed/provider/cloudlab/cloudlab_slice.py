import json
import logging
import time
from typing import List

import fabfed.provider.api.dependency_util as util
from fabfed.model import Node, Network
from .cloudlab_provider import CloudlabProvider
from .cloudlab_constants import *


class CloudlabSlice:
    def __init__(self, *, provider: CloudlabProvider, logger: logging.Logger):
        self.provider = provider
        self.logger = logger
        self.notified_create = False
        self.slice_created = False
        self.slice_object = None
        self.retry = 10
        self.project = self.provider.config.get(CLOUDLAB_PROJECT)
        self.cert = self.provider.config.get(CLOUDLAB_CERTIFICATE)

    def init(self):
        import emulab_sslxmlrpc.client.api as api
        import emulab_sslxmlrpc.xmlrpc as xmlrpc

        # Create the RPC server object.
        config = {
            "debug"       : 0,
            "impotent"    : 0,
            "verify"      : 0,
            "certificate" : self.cert
        }

        server = xmlrpc.EmulabXMLRPC(config)
        exp_params = {
            "experiment" : f"{self.project},{self.name}",
            "asjson": True
        }

        (exitval,response) = api.experimentStatus(server, exp_params).apply()
        if exitval == xmlrpc.RESPONSE_SEARCHFAILED:
            self.logger.info(f"Slice \"{self.name}\" not found, creating...")
            params = {
                "profile" : "fabfed,fabfed-stitch",
                "proj"    : self.project,
                "name"    : self.name,
                "asjson"  : True
            }
            (exitval,response) = api.startExperiment(server, params).apply()
            if exitval:
                self.logger.error(response.output)
                return
            self.logger.info("Slice is starting up, checking status periodically")
        elif exitval == xmlrpc.RESPONSE_SUCCESS or exitval == xmlrpc.RESPONSE_ALREADYEXISTS:
            self.logger.info("Slice already exists, checking status")
        else:
            self.logger.error(f"Unhandled slice status response: {response.output}")
            return

        while True:
            (exitval,response) = api.experimentStatus(server, exp_params).apply();
            if exitval:
                code = response.value
                if (code == api.GENIRESPONSE_REFUSED or code == api.GENIRESPONSE_NETWORK_ERROR):
                    self.logger.info("Server is offline, waiting for a bit")
                    continue
                elif code == api.GENIRESPONSE_BUSY:
                    self.logger.info("Experiment is busy, waiting for a bit")
                    continue
                elif code == api.GENIRESPONSE_SEARCHFAILED:
                    self.logger.error("Experiment is gone")
                    return
                else:
		    # Everything else is bad news. A positive error code
		    # typically means we could not get to the cluster. But
		    # the experiment it marked for cancel, and eventually
		    # it is going to happen.
                    self.logger.error(response.output)
                    return
            status = json.loads(response.value)
            self.logger.info(status)
            #
            # Waiting to go ready or failed.
            #
            if status["status"] == "failed":
                self.logger.info("Experiment failed to instantiate")
                break
            #
            # Once we hit ready, waiting for the execute service to exit.
            #
            if status["status"] == "ready":
                #
                # If there is no execute service, then no point in waiting
                #
                if not "execute_status" in status:
                    self.logger.info("No execute service to wait for!")
                    break
                total    = status["execute_status"]["total"]
                finished = status["execute_status"]["finished"]
                if total == finished:
                    self.logger.info("Execute services have finished")
                    break
                else:
                    self.logger.info("Still waiting for execute service to finish")
                    continue
                pass
            self.logger.info("Still waiting for experiment to go ready")
            time.sleep(5)

        (exitval,response) = api.experimentManifests(server, exp_params).apply();
        if exitval:
            self.logger.error(response.output)
            return
        else:
            status = json.loads(response.value)
            self.logger.info(status)

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
        pass

    def _add_node(self, resource: dict):
        pass

    def add_resource(self, *, resource: dict):
        pass

    def create_resource(self, *, resource: dict):
        pass

    def delete_resource(self, *, resource: dict):
        pass
