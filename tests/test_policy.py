from fabfed.controller.policy_helper import load_policy, find_stitch_port
from fabfed.util.constants import Constants
from fabfed.exceptions import StitchPortNotFound

import pytest


def test_policy_with_site():
    yaml_str = '''
fabric:
  group:
      - name: UTAH
        consumer-for:
          - cloudlab/UTAH         
cloudlab:
  stitch-port:
      - site: AAA
        member-of:
          - UTAH
        device_name: dev1
        preference: 10
      - site: BBB
        member-of:
          - UTAH
        device_name: dev2
        preference: 30 
      - site: AAA
        member-of:
          - UTAH
        device_name: dev3
        preference: 20 
  group:
    - name: UTAH
      producer-for:
        - fabric/UTAH
    '''

    policy = load_policy(content=yaml_str)
    stitch_info = find_stitch_port(policy=policy,
                                   providers=['cloudlab', 'fabric'],
                                   site="AAA")

    assert stitch_info.stitch_port['site'] == 'AAA'
    assert stitch_info.stitch_port['device_name'] == 'dev3'
    assert stitch_info.producer == 'cloudlab'
    assert stitch_info.consumer == 'fabric'


def test_policy_no_site():
    yaml_str = '''
fabric:
  group:
      - name: UTAH
        consumer-for:
          - cloudlab/UTAH         
cloudlab:
  stitch-port:
      - site: AAA
        member-of:
          - UTAH
        device_name: dev1
        preference: 10
      - site: BBB
        member-of:
          - UTAH
        device_name: dev2
        preference: 30 
      - site: CCC
        member-of:
          - UTAH
        device_name: dev3
        preference: 20 
  group:
    - name: UTAH
      producer-for:
        - fabric/UTAH
    '''

    policy = load_policy(content=yaml_str)
    stitch_info = find_stitch_port(policy=policy,
                                   providers=['fabric', 'cloudlab'],
                                   site=None)

    assert stitch_info.stitch_port['site'] == 'BBB'
    assert stitch_info.stitch_port['device_name'] == 'dev2'
    assert stitch_info.producer == 'cloudlab'
    assert stitch_info.consumer == 'fabric'


def test_bidrectional_policy():
    yaml_str = '''
fabric:
  stitch-port:
      - site: AAA
        member-of:
          - AWS
        device_name: dev1
        preference: 100
      - site: BBB
        member-of:
          - AWS
        device_name: dev2
        preference: 10
  group:
      - name: AWS
        producer-for:
          - sense/AWS
        consumer-for:
          - sense/AWS
sense:
  stitch-port:
      - site: CCC
        member-of:
          - AWS
        region:
        device_name: dev3
        local_name: TenGigE0/0/0/11/3
        preference: 110
  group:
      - name: AWS 
        profile: FABRIC-AWS-DX-VGW
        consumer-for:
          - fabric/AWS
        producer-for:
          - fabric/AWS
    '''

    policy = load_policy(content=yaml_str)
    stitch_info = find_stitch_port(policy=policy,
                                   providers=['fabric', 'sense'],
                                   site=None)

    assert stitch_info.stitch_port['site'] == 'CCC'
    assert stitch_info.stitch_port['device_name'] == 'dev3'
    assert stitch_info.producer == 'sense'
    assert stitch_info.consumer == 'fabric'


def test_bidrectional_policy2():
    yaml_str = '''
fabric:
  stitch-port:
      - site: AAA
        member-of:
          - AWS
        device_name: dev1
        preference: 100
      - site: BBB
        member-of:
          - AWS
        device_name: dev2
        preference: 900
  group:
      - name: AWS
        producer-for:
          - sense/AWS
        consumer-for:
          - sense/AWS
sense:
  stitch-port:
      - site: CCC
        member-of:
          - AWS
        region:
        device_name: dev3
        local_name: TenGigE0/0/0/11/3
        preference: 110
  group:
      - name: AWS 
        profile: FABRIC-AWS-DX-VGW
        consumer-for:
          - fabric/AWS
        producer-for:
          - fabric/AWS
    '''

    policy = load_policy(content=yaml_str)
    stitch_info = find_stitch_port(policy=policy,
                                   providers=['fabric', 'sense'],
                                   site=None)

    assert stitch_info.stitch_port['site'] == 'BBB'
    assert stitch_info.stitch_port['device_name'] == 'dev2'
    assert stitch_info.producer == 'fabric'
    assert stitch_info.consumer == 'sense'


def test_find_stitch_port_using_node_site1():
    policy_str = '''
    fabric:
      stitch-port:
          - site: AAA
            member-of:
              - AWS
            device_name: dev1
            preference: 1
          - site: BBB
            member-of:
              - AWS
            device_name: dev2
            preference: 10
      group:
          - name: AWS
            producer-for:
              - sense/AWS
            consumer-for:
              - sense/AWS
    sense:
      group:
          - name: AWS 
            profile: FABRIC-AWS-DX-VGW
            consumer-for:
              - fabric/AWS
            producer-for:
              - fabric/AWS
        '''

    config_str = '''
provider:
  - fabric:
      - my_provider1:
          - name: prov1
  - sense:
      - my_provider2:
          - name: prov2
resource:
  - network:
      - net1:
          - provider: '{{ fabric.my_provider1 }}'
            interface: '{{ node.node1 }}'
            stitch_with: '{{ network.net2 }}'
      - net2:
          - provider: '{{ sense.my_provider2 }}'
  - node:
      - node1:
          - provider: '{{ fabric.my_provider1 }}'
            site: BBB 
        '''

    from fabfed.util.config import WorkflowConfig

    config = WorkflowConfig(content=config_str)
    policy = load_policy(content=policy_str)
    from fabfed.controller.policy_helper import handle_stitch_info

    resources = handle_stitch_info(config, policy, config.get_resource_configs())

    for network in [resource for resource in resources if resource.is_network]:
        stitch_info = network.attributes[Constants.RES_STITCH_INFO]

        assert stitch_info.stitch_port['site'] == 'BBB'


def test_find_stitch_port_using_node_site2():
    policy_str = '''
    fabric:
      stitch-port:
          - site: AAA
            member-of:
              - AWS
            device_name: dev1
          - site: BBB
            member-of:
              - AWS
            device_name: dev2
            preference: 10
      group:
          - name: AWS
            producer-for:
              - sense/AWS
            consumer-for:
              - sense/AWS
    sense:
      group:
          - name: AWS 
            profile: FABRIC-AWS-DX-VGW
            consumer-for:
              - fabric/AWS
            producer-for:
              - fabric/AWS
        '''

    config_str = '''
provider:
  - fabric:
      - my_provider1:
          - name: prov1
  - sense:
      - my_provider2:
          - name: prov2
resource:
  - network:
      - net1:
          - provider: '{{ fabric.my_provider1 }}'
            stitch_with: '{{ network.net2 }}'
      - net2:
          - provider: '{{ sense.my_provider2 }}'
  - node:
      - node1:
          - provider: '{{ fabric.my_provider1 }}'
            site: BBB 
            network: '{{ network.net1 }}'
        '''

    from fabfed.util.config import WorkflowConfig

    config = WorkflowConfig(content=config_str)
    policy = load_policy(content=policy_str)
    from fabfed.controller.policy_helper import handle_stitch_info

    resources = handle_stitch_info(config, policy, config.get_resource_configs())

    for network in [resource for resource in resources if resource.is_network]:
        stitch_info = network.attributes[Constants.RES_STITCH_INFO]

        assert stitch_info.stitch_port['site'] == 'BBB'


def test_no_stitch_info():
    policy_str = '''
    fabric:
      group:
          - name: AWS
            producer-for:
              - sense/AWS
            consumer-for:
              - sense/AWS
    sense:
      group:
          - name: AWS 
            profile: FABRIC-AWS-DX-VGW
            consumer-for:
              - fabric/AWS
            producer-for:
              - fabric/AWS
        '''

    config_str = '''
provider:
  - fabric:
      - my_provider1:
          - name: prov1
  - sense:
      - my_provider2:
          - name: prov2
resource:
  - network:
      - net1:
          - provider: '{{ fabric.my_provider1 }}'
            stitch_with: '{{ network.net2 }}'
      - net2:
          - provider: '{{ sense.my_provider2 }}'
  - node:
      - node1:
          - provider: '{{ fabric.my_provider1 }}'
            site: BBB 
            network: '{{ network.net1 }}'
        '''

    from fabfed.util.config import WorkflowConfig

    config = WorkflowConfig(content=config_str)
    policy = load_policy(content=policy_str)
    from fabfed.controller.policy_helper import handle_stitch_info

    with pytest.raises(StitchPortNotFound):
        handle_stitch_info(config, policy, config.get_resource_configs())
