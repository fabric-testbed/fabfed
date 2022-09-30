from fabfed.util.parser import Parser, DependencyInfo
from fabfed.exceptions import ParseConfigException
import pytest


def test_malformed_node():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 2
      - my_node2:
          - slice: '{{ slice.my_slice }}'
            count: 2

  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_no_nodes_and_no_networks():
    yaml_str = '''
resource:
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_no_slices():
    yaml_str = '''
resource:
  - node:
      - my_node:
            - count: 2
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_malformed_slice():
    yaml_str = '''
resource:
  - node:
      - my_node:
            - slice: '{{ slice.my_slice }}'
  - slice:
      - my_slice:
            - no_provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_slices():
    yaml_str = '''
resource:
  - node:
      - my_node:
            - slice: '{{ slice.my_slice }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_slices_across_providers():
    yaml_str = '''
resource:
  - node:
      - my_node:
            - slice: '{{ slice.my_slice }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
  - slice:
      - my_slice:
          - provider: '{{ prov2.my_provider2 }}'
provider:
  - prov1:
    - my_provider:
       - user: user1 
  - prov2:
    - my_provider2:
       - user: user1        
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_slice_bad_reference():
    yaml_str = '''
resource:
  - slice:
      - my_slice:
          - provider: '{{ prov20.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_no_provider():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 2
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 5
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'       
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_providers():
    yaml_str = '''
provider:
  - prov1:
    - my_provider:
       - user: user1 
  - prov2:
    - my_provider:
       - user: user2        
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_nodes():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 2
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 5
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1      
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_nodes_across_slices():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 2
  - node:
      - my_node:
          - slice: '{{ slice.my_slice2 }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
  - slice:
      - my_slice2:
          - provider: '{{ prov2.my_provider2 }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
  - prov2:
    - my_provider2:
       - user: user1
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_networks_across_slices():
    yaml_str = '''
resource:
  - network:
      - my_net:
          - slice: '{{ slice.my_slice }}'
            count: 2
  - network:
      - my_net:
          - slice: '{{ slice.my_slice2 }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
  - slice:
      - my_slice2:
          - provider: '{{ prov2.my_provider2 }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
  - prov2:
    - my_provider2:
       - user: user1
    '''

    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_across_types():
    yaml_str = '''
resource:
  - node:
      - my_var:
          - slice: '{{ slice.my_var }}'
            count: 2
  - network:
      - my_var:
          - slice: '{{ slice.my_slice2 }}'
  - slice:
      - my_var:
          - provider: '{{ prov1.my_provider }}'
  - slice:
      - my_slice2:
          - provider: '{{ prov2.my_provider2 }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
  - prov2:
    - my_provider2:
       - user: user1
    '''

    Parser.parse(content=yaml_str)


def test_different_types():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice: '{{ slice.my_slice }}'
            count: 1
            up: True
            vlans: [1, 2]
            network:
              type: ipv4
              ip:
                - interface: eth0
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
        '''
    _, _, resources = Parser.parse(content=yaml_str)
    assert len(resources) == 1
    assert len(resources[0].dependencies) == 0


def test_missing_variable():
    yaml_str = '''
provider:
  - prov1:
    - my_provider:
       - user: '{{ var.user_name }}'
resource:
  - node:
      - my_node:
          - slice:  '{{ slice.my_slice }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
    '''
    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_duplicate_variables():
    yaml_str = '''
variable:
  - slice_name:
      - default: "test_slice"
  - slice_name:
      - default: "user10"
provider:
  - prov1:
    - my_provider:
       - user: "some_user"
resource:
  - node:
      - my_node:
          - slice:  '{{ slice.my_slice }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
    '''
    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)


def test_variables():
    yaml_str = '''
variable:
  - slice_name:
      - default: "test_slice"
  - user_name:
      - default: "user10"
  - open_ports: 
      - default: [22, 443]
  - groups:
      - default:
  - vlan: 
      
provider:
  - prov1:
    - my_provider:
       - user: '{{ var.user_name }}'
       
resource:
  - node:
      - my_node:
          - slice:  '{{ slice.my_slice }}'
            ports:  '{{ var.open_ports }}'
            vlan:   '{{ var.vlan }}'
            groups: '{{ var.groups }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
            name:     '{{ var.slice_name }}'
    '''
    with pytest.raises(ParseConfigException):
        Parser.parse(content=yaml_str)

    # now let's inject some values for groups and vlan
    var_dict = dict(groups=['g1'], vlan=5)

    providers, slices, resources = Parser.parse(content=yaml_str, var_dict=var_dict)
    assert slices[0].name == 'test_slice'
    assert providers[0].attributes['user'] == 'user10'
    assert resources[0].attributes['ports'] == [22, 443]
    assert resources[0].attributes['vlan'] == 5
    assert resources[0].attributes['groups'] == ['g1']


def test_dependencies():
    yaml_str = '''
resource:
  - node:
      - my_node:
          - slice:  '{{ slice.my_slice }}'
            simple_attr: '{{ network.my_network.vlan }}'
            list_attr:  [ '{{ network.my_network.ip }}', '{{ network.my_network.port }}']
            complex_attr:
              type: '{{ network.my_network.subnet }}'
              ip:
                - interface: '{{ network.my_network.os_interface.mask }}'
  - network:
      - my_network:
          - slice:  '{{ slice.my_slice }}'
  - slice:
      - my_slice:
          - provider: '{{ prov1.my_provider }}'
provider:
  - prov1:
    - my_provider:
       - user: user1
    '''
    providers, slices, resources = Parser.parse(content=yaml_str)
    assert len(providers) == 1
    assert len(slices) == 1
    assert len(resources) == 2

    for resource in resources:
        if resource.is_node:
            assert len(resource.attributes) == 3
            assert list(resource.attributes.keys()) == ['simple_attr', 'list_attr', 'complex_attr']
            assert isinstance(resource.attributes['simple_attr'], DependencyInfo)
            assert len(resource.attributes['list_attr']) == 2
            assert len(resource.attributes['complex_attr']) == 2
            assert len(resource.dependencies) == 5
            keys = set()
            attributes = set()

            for dep in resource.dependencies:
                keys.add(dep.key)
                attributes.add(dep.attribute)

            assert keys == {'complex_attr.ip.interface', 'list_attr', 'simple_attr', 'complex_attr.type'}
            assert attributes == {'ip', 'port', 'vlan', 'os_interface.mask', 'subnet'}

            temp = list()
            temp.append(resource.attributes['simple_attr'])
            temp.extend(resource.attributes['list_attr'])
            adict = resource.attributes['complex_attr']
            temp.append(adict['type'])
            ip_dep = adict['ip'][0]
            temp.append(ip_dep['interface'])
            assert len(resource.dependencies) == len(temp)
            temp = [d for d in temp if not isinstance(d, DependencyInfo)]
            assert not temp
