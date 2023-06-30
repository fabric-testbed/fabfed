# Table of contents

 - [Description](#descr)
 - [Variables](#variables)
 - [Providers](#providers)
 - [Configs](#configs)
 - [Layer3](#layer3)
 - [Peering](#peering)
 - [Resources](#resources)
 - [Nodes](#nodes)
 - [Networks](#networks)
 - [Dependencies](#dependencies)
 - [Network Stiching Policy](#stitching)
 - [Breaking The Configuration](#breaking)

# <a name="descr"></a>Description
This readme file describes fabfed-py workflow model. The model consist of the following high level classes:
- [ ] variable
- [ ] provider
- [ ] config
- [ ] resource

The `provider` class supports the following types.
- [ ] fabric
- [ ] chi
- [ ] cloudlab
- [ ] sense
- [ ] janus
      
The `config` class support the following types:
- [ ] layer3
- [ ] peering
      
The `resource` class support three types:
- [ ] node
- [ ] network
- [ ] service

The workflow model allows us to define resources and to express dependencies among them. This is explained in more details below. We recommend you read on but under the <i>config directory</i>, you can find a template credential and a complete chameleon to fabric stitching example.

- [fabfed credential file template](../config/fabfed_credentials_template.yml)
- [stitching example](../config/chi_to_fabric_stitching.fab)

# <a name="variables"></a>Variables
Variables have their own class named <i>variable</i>. A variable consists of a name and a value. Its declaration 
uses the <i>default</i> attribute signifying that it can be overriden at runtime using an external var-file. More on this later. 
The variable <i>fabric_site<i> declared below can be referred to by the expression ```'{{ var.fabric_site }}'``` and similarly ```'{{ var.node_name }}'``` 
would refer to the variable node_name.
 

```
variable:             # Class 
  - fabric_site:      # Label
      default: STAR   # Default value
  - node_name:        # Default for this variable is None and so it must be overridden using a var-file
 
```

A variable need not be declared at all as long as it is injected by supplying an external var-file. This var-file consists of a set of key-value pairs and can be specified on the fabfed command line tool with the --var-file option. Each key-value pair is written as ```key: value```. The sample var-file below would override the value ```STAR``` of the <i>fabric_site<i> declared above and would set the value of node_name to ```my_node```. 
 
 ```
 fabric_site: TACC
 node_name: my_node
 ```
 <b>NOTE</b>: The parsing process would halt if a variable is not bound to a value other than ```None```.
  
# <a name="providers"></a>Providers
A provider has its own class named <i>provider<i>. It consists of a <i>type</i>, a <i>label</i> and a dictionary. The snippet below declares a <i>fabric</i> provider. The `credential_file` and the `profile` attributes are used to configure the provider's environment.

A <i>resource</i> msut refer to a provider using its type and its label like so: ```provider: '{{ fabric.fabric_provider }}'```

```
provider:                                                    # Class 
  - fabric:                                                  # Prvider Type: Must be one of these. [fabric, chi, sense, cloudlab, janus]
    - fabric_provider:                                       # Label: Can be any string
         credential_file: ~/.fabfed/fabfed_credentials.yml
         profile: fabric                                     # This can be any string and is to point to a section in the credential file
```
 
 The `credential_file` and the `profile` are attributes used to configure the provider's environment. The credential YAML file contains a section or a profile for each provider. Unlike the provider type, the profile is an arbitrary string used to point to a section in the credential file. And each section contains information specific to a user and to each provider. The example below shows a credential file for fabric and chi. Consult the [template credential file](../config/fabfed_credentials_template.yml) for all the providers we currently support
  
```
# Sample Fabfed Credential File

fabric:
   bastion-user-name:
   token-location:
   bastion-key-location:
   project_id:
   slice-private-key-location:
   slice-public-key-location:

chi:
   project_name:
   key_pair:
   user:
   password:
   slice-private-key-location:
   slice-public-key-location:
```

# <a name="configs"></a>Configs

A config consists of a <i>type</i>, a <i>label</i> and a dictionary specifying its attributes. The parsing process guarantees that the combination of the type and the label is unique. One can think of Configs as glorifed variables. 
We have two types `layer3` and `peering` and the Network Resources refer to these configs.

# <a name="layer3"></a>Layer3

In the example below the fabric and the chi networks share or point to the same layer3 config. The controller detects that and partitions the ip address space automatically. This results in a more concise and less error-prone configuration.

```
config:
  - layer3:
      - my_layer:
          subnet: 192.168.100.0/24
          gateway: 192.168.100.1
          ip_start: 192.168.100.100
          ip_end: 192.168.100.250
resource:
  - network:
      - chi_network:
          layer3: "{{ layer3.my_layer }}"
      - fabric_network
          layer3: "{{ layer3.my_layer }}"
```

# <a name="peering"></a>Peering

TODO:

# <a name="resources"></a>Resources
A resource consists of a <i>type</i>, a <i>label</i> and a dictionary. The parsing process guarantees that the combination of the type and the label is unique. Resources can refer to each other using the expression ```'{{ type.label }}'```. They can also refer to a resource's attribute using ```'{{ type.label.attribute_name }}'```. 

As of now we support the following types: <i>node</i>, <i>network</i>, and <i>service</i>. The <i>label</i> can be any string and is used as the name of the resource if the <i>name</i> attribute is not present. Resources are declared under their own class named <i>resource<i>. 
 
# <a name="nodes"></a>Nodes
A <i>node</i> <b>must</b> refer to a provider. Here it refers to the provider declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this node using its type and label like so: ```'{{ node.fabric_node }}'```
 
```
resource:                                               # Class
  - node:                                               # Type must be one of node, network, or service
      - fabric_node:                                    # Label can be any string
            provider: '{{ fabric.fabric_provider }}'
            site: '{{ var.fabric_site }}'
            count: 1
            image: default_rocky_8                                  
```
# <a name="networks"></a>Networks
A <i>network</i> <b>must</b> refer to a provider. Here it refers to the provider declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this network using its type and label like so: ```'{{ network.fabric_network }}'```
 
```
resource:                                               # Class
   - network:                                           # Type can be node or network
      - fabric_network:                                 # Label can be any string
            provider: '{{ fabric.fabric_provider }}'
            site: '{{ var.fabric_site }}'
            name: my_network
```
# <a name="services"></a>Services
A <i>service</i> <b>must</b> refer to a provider. Here it refers to a Janus provider for container management.
 
 
```
provider:
  - janus:
      - janus_provider:
          credential_file: ~/.fabfed/fabfed_credentials.yml
          profile: janus


resource:                                                          # Class
   - service:                                                      # Must be one of node, network, or service
      - dtn_service:                                               # Label can be any string
          - provider: '{{ janus.janus_provider }}'
            node: [ '{{ node.my_node0 }}', '{{ node.my_node1 }}' ] # List of nodes to apply the service to
            image: [Optional]
            profile: [Optional]
```
 
# <a name="dependencies"></a>Dependencies
A resource can refer to other resources that it depends on. Line 9 in the example below, states that the <i>fabric_network</i> depends 
on the <i>fabric_node</i>. This is an `internal dependency` as both resources are handled by the same provider. The fabfed 
controller detects this internal dependency and processes the fabric_node before the fabric_network. 
Also note that the `interface` attribute implies that the fabric_network is interested in the `interfaces` 
of the fabric_network.
 
```
1. resource:
2.   - network:
3.      - chi_network:
4.             provider: '{{ chi.chi_provider }}'
5.             layer3: "{{ layer3.my_layer }}"
6.             stitch_with: '{{ network.fabric_network }}'  # Externally Dependency. Normally this would mean fabric_network would be processed first. 
7.      - fabric_network:
8.             provider: '{{ fabric.fabric_provider }}'
9.             interface: '{{ node.fabric_node }}'          # Internal dependency
10.            layer3: "{{ layer3.my_layer }}"
11      - fabric_node:
12             provider: '{{ fabric.fabric_provider }}'
13             site: '{{ var.fabric_site }}'
14             image: default_rocky_8
15             count: 1
```

 # <a name="stitching"></a>Network Stiching Policy
 
 The `stitch_with` dependency in line 6 above depicts an external dependency as it involves two resources from different providers. Fabfed 
 controller ensures that the ordering is correct for both internal and external dependencies. Normally the `fabric_network` 
 would be handled before the chi_network. However, the `stitch_with` is a <b>special</b> attribute that 
 declares that the two networks are to be stitched and it is handled differently. 
 
 The fabfed controller supports a policy-defined network stitching and consults a policy file to pick a suitable stitch_port 
 between two providers and determines the producer/consumer relationship. For `chi` and `fabric`, it so happened that 
 there is only one `stitch-port` and that the `chi network` is the producer. The `chi_network` produces a `vlan` that the 
 `fabric_network` uses to create a `facility port`. And so the controller would reorder the resources as needed to ensure 
 that the producer is processed first.
 
 Below is a snippet from the policy file showing the single `stitch-port` from `chi` to `fabric`. The groups are used to specify 
 the consumer/producer relationship. For sense and fabric, there are many stitch ports and bi-directional consumer/producer 
 relationships. The `stich-port` with the highest preference gets selected but the `stitch_option` attribute can be usedto select a 
 desired `stitch-port`. See sense workflows under the examples directory.
 
 ```
fabric:
  group:
      - name: STAR
        consumer-for:
            - chi/STAR
chi:
  stitch-port:
    - site: STAR
      member-of:
        - STAR
      device_name: Chameleon-StarLight
      preference: 100 # higher is preferred

  group:
    - name: STAR
      producer-for:
        - fabric/STAR

 ```
 
 # <a name="breaking"></a>Breaking The Configuration
 
 A configuration can be broken into many configuration files ending with ```.fab``` extensions. Fabfed does not care about how the files are named. 
 It loads all the files residing in a given directory that match the pattern ```*.fab```. It does so in no particular order and then proceeds to parse the assembled result. see [Fabric Chameleon Stitch](../examples/stitch)
 
 

