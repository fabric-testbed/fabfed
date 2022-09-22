from fabfed.provider.api.api_client import Provider
from fabfed.controller.provider_factory import ProviderFactory
import logging
from fabfed.controller.controller import Controller
from fabfed.util.config import Config
from fabfed.util.constants import Constants
from fabfed.model import Slice
from fabfed.model import Node

config_str = """
provider:
  - fabric:
    - test_fabric_provider:
       - name: "provider1"
         
  - chi:
    - test_chi_provider:
       - name: "provider2"
       
resource:
  - slice:
      - test_fabric_slice:
          - provider: '{{ fabric.test_fabric_provider }}'
            name: super_slice
  - slice:
      - test_chi_slice:
          - provider: '{{ chi.test_chi_provider }}'
            name: super_slice

  - node:
      - test_fabric_node:
          - slice:  '{{ slice.test_fabric_slice }}'
            type: VM
            site: 'STAR'
            image: default_rocky_8
            nic_model: NIC_ConnectX_5
  - node:
      - test_chi_node:
          - slice:  '{{ slice.test_chi_slice }}'
            type: Baremetal
            site: CHI@UC
            image: CC-Ubuntu20.04
            flavor:
              name: m1.medium

  - network:
      - test_chi_network:
          - slice:  '{{ slice.test_chi_slice }}'
            name: super_net
            site: CHI@UC
            stitch_provider: fabric

  - network:
      - test_fabric_network:
          - slice: '{{ slice.test_fabric_slice }}'
            site: 'STAR'
            vlan: '{{ network.test_chi_network.vlans}}'
"""


class SimpleNode(Node):
    def __init__(self, *, label, name: str, image: str, site: str, flavor: str,):
        super().__init__(label=label, name=name, image=image, site=site, flavor=flavor)

    def get_reservation_id(self) -> str:
        return "NO_RESERVATION_ID"

    def get_reservation_state(self) -> str:
        return "NO_SATE"


class SimpleSlice(Slice):
    def __init__(self, *, label, name: str, logger: logging.Logger):
        super().__init__(label=label, name=name)
        self.logger = logger
        self.notified_create = False
        self.resources = []
        self.pending_resources = 0

    def add_resource(self, *, resource: dict):
        if resource['has_dependencies']:
            if not resource['resolved_dependencies']:
                if resource not in self.pending:
                    self.logger.info(f"Adding to pending: {resource['name_prefix']}")
                    self.pending.append(resource)
                    self.pending_resources += 1

        self.resources.append(resource)
        rtype = resource.get(Constants.RES_TYPE)
        if rtype == Constants.RES_TYPE_NETWORK.lower():
            pass
        elif rtype == Constants.RES_TYPE_NODE.lower():
            node_count = resource.get(Constants.RES_COUNT, 1)
            name_prefix = resource.get(Constants.RES_NAME_PREFIX)
            flavor = str(resource.get(Constants.RES_FLAVOR))
            label = resource.get(Constants.LABEL)
            image = resource.get(Constants.RES_IMAGE)
            site = resource.get(Constants.RES_SITE)

            for i in range(node_count):
                name = f"{name_prefix}{i}"
                node = SimpleNode(label=label, name=name, image=image, site=site, flavor=flavor)
                self._nodes.append(node)
        else:
            raise Exception("Unknown resource ....")

    def create(self,):
        for resource in self.resources:
            if resource[Constants.RES_NAME_PREFIX] == 'super_net':
                resource['vlans'] = [2]

            self.resource_listener.on_created(self, self.name, resource)

    def destroy(self, *, slice_state):
        pass


class SimpleProvider(Provider):
    def __init__(self, *, type, name, logger: logging.Logger, config: dict):
        super().__init__(type=type, name=name, logger=logger, config=config)

    def setup_environment(self):
        pass

    def init_slice(self, *, slice_config: dict, slice_name: str):
        self.logger.debug(f"initializing  slice {slice_name}: slice_attributes={slice_config}")

        if slice_name in self.slices:
            raise Exception("provider cannot have more than one slice with same name")

        label = slice_config.get(Constants.LABEL)
        fabric_slice = SimpleSlice(label=label, name=slice_name, logger=self.logger)
        self.slices[slice_name] = fabric_slice
        fabric_slice.set_resource_listener(self)

    def add_resource(self, *, resource: dict, slice_name: str):
        self.logger.info(f"Adding {resource['name_prefix']} to {slice_name}")
        self.logger.debug(f"Adding {resource} to {slice_name}")

        if resource.get(Constants.RES_COUNT, 1) < 1:
            self.logger.debug(f"will not add {resource['name_prefix']} to {slice_name}: Count is zero")
            return

        fabric_slice = self.slices[slice_name]
        fabric_slice.add_resource(resource=resource)


class SimpleProviderFactory(ProviderFactory):
    def __init__(self):
        super().__init__()

    def init_provider(self, *, type: str, label: str, attributes, logger):
        if type == 'fabric':
            provider = SimpleProvider(type=type, name=label, logger=logger, config=attributes)
            self._providers[label] = provider
        elif type == 'chi':
            provider = SimpleProvider(type=type, name=label, logger=logger, config=attributes)
            self._providers[label] = provider
        else:
            raise Exception(f"no provider for type {type}")


def test_controller():
    config = Config(content=config_str)
    logger = logging.getLogger(__name__)
    controller = Controller(config=config, logger=logger)
    provider_factory = SimpleProviderFactory()
    controller.init(provider_factory=provider_factory)
    assert len(provider_factory.providers) == 2
    controller.plan()
    resources_with_resolved_dependencies = []
    pending_reources = []

    for provider in provider_factory.providers:
        assert provider.resource_listener
        assert len(provider.slices) == 1

        for slice_object in provider.slices.values():
            assert len(slice_object.resources) == 2
            for resource in slice_object.resources:
                if 'resolved_dependencies' in resource and resource['resolved_dependencies']:
                    resources_with_resolved_dependencies.append(resource)

            pending_reources.extend(slice_object.pending)

    assert len(pending_reources) == 1
    assert len(resources_with_resolved_dependencies) == 0

    states = controller.get_states()
    assert len(states) == 2

    for state in states:
        provider_label = state.label
        assert len(state.slice_states) == 1

        for slice_state in state.slice_states:
            assert len(slice_state.node_states) == 1

            if provider_label == 'test_fabric_provider@fabric':
                assert len(slice_state.pending) == 1, provider_label
            else:
                assert len(slice_state.pending) == 0, provider_label
    import yaml
    from fabfed.model.state import get_dumper, get_loader

    dump = yaml.dump(states, Dumper=get_dumper())
    loaded_states = yaml.load(dump, Loader=get_loader())
    assert len(loaded_states) == 2

    for loaded_state in loaded_states:
        provider_label = loaded_state.label
        assert len(loaded_state.slice_states) == 1

        for loaded_slice_state in loaded_state.slice_states:
            assert len(loaded_slice_state.node_states) == 1

            if provider_label == 'test_fabric_provider@fabric':
                assert len(loaded_slice_state.pending) == 1, provider_label
            else:
                assert len(loaded_slice_state.pending) == 0, provider_label

    controller.create()  # create should resolve the dependency
    pending_reources = []

    for provider in provider_factory.providers:
        for slice_object in provider.slices.values():
            for resource in slice_object.resources:
                if 'resolved_dependencies' in resource and resource['resolved_dependencies']:
                    resources_with_resolved_dependencies.append(resource)

            pending_reources.extend(slice_object.pending)

    assert len(pending_reources) == 1
    assert len(resources_with_resolved_dependencies) == 1
    states = controller.get_states()

    for state in states:
        assert len(state.slice_states) == 1

        for slice_state in state.slice_states:
            assert len(slice_state.node_states) == 1
            # TODO This should be zero  for both providers once slice.create clear the pending ...
            assert len(slice_state.pending) == 0 or len(slice_state.pending) == 1
