from sense.client.requestwrapper import RequestWrapper

SENSE_CLIENT = None


def init_client(config):
    global SENSE_CLIENT

    if not SENSE_CLIENT:
        SENSE_CLIENT = SenseClient(config)


class SenseClient(RequestWrapper):
    def __init__(self, config=None):
        self.config = config
        super().__init__()

    def getConfig(self, config_file=None):
        if not self.config:
            super().getConfig()
            return

        self._validateConfig()
        self._setDefaults()
