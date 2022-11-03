class FabfedException(Exception):
    """Base class for other exceptions"""
    pass


class ParseConfigException(FabfedException):
    pass


class ResourceTypeNotSupported(FabfedException):
    pass


class StateException(FabfedException):
    pass


class ProviderTypeNotSupported(FabfedException):
    pass
