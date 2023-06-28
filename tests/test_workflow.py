import logging

from fabfed.controller.controller import Controller
from fabfed.util import state as sutil
from fabfed.util.config import WorkflowConfig
from typing import List
from fabfed.controller.provider_factory import default_provider_factory

from fabfed.model.state import ProviderState


def get_stats(*, states: List[ProviderState]):
    nodes = networks = services = pending = failed = 0

    for state in states:
        pending += len(state.pending)
        nodes += len(state.node_states)
        networks += len(state.network_states)
        services += len(state.service_states)
        failed += len(state.failed)

    return nodes, networks, services, pending, failed


def run_apply_workflow(*, session, config_str) -> List[ProviderState]:
    config = WorkflowConfig(content=config_str)
    logger = logging.getLogger(__name__)
    controller = Controller(config=config, logger=logger)
    controller.init(session=session, provider_factory=default_provider_factory)
    controller.plan(provider_states=[])
    controller.create(provider_states=[])
    states = controller.get_states()
    sutil.save_states(states, session)
    return states


def run_destroy_workflow(*, session, config_str) -> List[ProviderState]:
    config = WorkflowConfig(content=config_str)
    logger = logging.getLogger(__name__)
    controller = Controller(config=config, logger=logger)
    controller.init(session=session, provider_factory=default_provider_factory)
    states = sutil.load_states(session)
    controller.delete(provider_states=states)
    sutil.save_states(states, session)

    if not states:
         sutil.destroy_session(session)

    return states


def test_simple_workflow():
    config_str = '''
provider:
  - dummy:
    - my_provider:
       - url: https://some_url:5000
resource:
  - service:
      - dtn:
         - provider: '{{ dummy.my_provider }}'
           image: ubuntu
    '''
    session = "test_simple"
    states = run_apply_workflow(session=session, config_str=config_str)
    assert len(states) == 1
    assert get_stats(states=states) == (0, 0, 1, 0, 0)
    states = run_destroy_workflow(session=session, config_str=config_str)
    assert len(states) == 0


def test_service_dependency_workflow():
    config_str = '''
provider:
  - dummy:
    - my_provider:
       - url: https://some_url:5000
         name: prov1
  - dummy:
    - my_provider2:
       - url: https://some_other_url:5000
         name: prov2
resource:
  - service:
      - dtn1:
         - provider: '{{ dummy.my_provider }}'
           image: "centos"
           exposed_attribute_x: "{{ service.dtn2 }}"
  - service:
      - dtn2:
         - provider: '{{ dummy.my_provider2 }}'
           image: ubuntu
    '''
    session = "test_service_dependency"
    states = run_apply_workflow(session=session, config_str=config_str)
    assert len(states) == 2
    assert get_stats(states=states) == (0, 0, 2, 0, 0)
    states = run_destroy_workflow(session=session, config_str=config_str)
    assert len(states) == 0


def test_attribute_dependency_workflow():
    config_str = '''
provider:
  - dummy:
    - my_provider:
       - url: https://some_url:5000
         name: prov1
  - dummy:
    - my_provider2:
       - url: https://some_other_url:5000
         name: prov2
resource:
  - service:
      - dtn1:
         - provider: '{{ dummy.my_provider }}'
           image: "centos"
           count: 5
           exposed_attribute_x: "{{ service.dtn2.exposed_attribute_x }}"
  - service:
      - dtn2:
         - provider: '{{ dummy.my_provider2 }}'
           image: ubuntu
    '''
    session = "test_attribute_dependency"
    states = run_apply_workflow(session=session, config_str=config_str)
    assert len(states) == 2

    assert get_stats(states=states) == (0, 0, 6, 0, 0)
    x = states[0].service_states[0].attributes["exposed_attribute_x"]

    for state in states:
        for service_state in state.service_states:
            assert service_state.attributes["exposed_attribute_x"] == x

    states = run_destroy_workflow(session=session, config_str=config_str)
    assert len(states) == 0


def test_multiple_service_dependency_workflow():
    config_str = '''
provider:
  - dummy:
    - my_provider:
       - url: https://some_url:5000
         name: prov1
  - dummy:
    - my_provider2:
       - url: https://some_other_url:5000
         name: prov2
resource:
  - service:
      - dtn1:
         - provider: '{{ dummy.my_provider }}'
           image: "centos"
           exposed_attribute_x: ["{{ service.dtn2 }}", "{{ service.dtn3 }}"]
           count: 10
  - service:
      - dtn2:
         - provider: '{{ dummy.my_provider2 }}'
           image: ubuntu
           count: 2
  - service:
      - dtn3:
         - provider: '{{ dummy.my_provider2 }}'
           image: ubuntu
           count: 3
 
    '''
    session = "test_service_dependency"
    states = run_apply_workflow(session=session, config_str=config_str)
    assert len(states) == 2
    assert get_stats(states=states) == (0, 0, 15, 0, 0)
    states = run_destroy_workflow(session=session, config_str=config_str)
    assert len(states) == 0
