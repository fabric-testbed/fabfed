from sense.client.requestwrapper import RequestWrapper

SENSE_CLIENT = None


def init_client(config):
    global SENSE_CLIENT

    if not SENSE_CLIENT:
        SENSE_CLIENT = SenseClient(config)


# TODO Fix this and make sure the config is coming from fabfed credentials
class SenseClient(RequestWrapper):
    def __init__(self, config=None):
        self.temp_config = config
        super().__init__()

    def getConfig(self, config_file=None):
        if not self.temp_config:
            super().getConfig()
            return

        self.config = self.temp_config
        self._validateConfig()
        self._setDefaults()
