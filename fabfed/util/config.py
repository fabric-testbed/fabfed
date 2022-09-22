from .parser import Parser, ResourceConfig, ProviderConfig, SliceConfig
from typing import List


class Config:
    def __init__(self, *, file_name=None, content=None, var_dict=None):
        self.providers, self.slices, self.resources = Parser.parse(file_name=file_name,
                                                                   content=content,
                                                                   var_dict=var_dict)

    def get_slice_config(self) -> List[SliceConfig]:
        return self.slices

    def get_provider_config(self) -> List[ProviderConfig]:
        return self.providers

    def get_resource_config(self) -> List[ResourceConfig]:
        return self.resources
