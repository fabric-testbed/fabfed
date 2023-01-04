# Table of contents

 - [Description](#descr)
 - [Variables](#variables)
 - [Providers](#providers)
 - [Resources](#resources)
 - [Nodes](#nodes)
 - [Networks](#networks)
 - [Dependencies](#dependencies)
 - [Breaking The Configuration](#breaking)

# <a name="descr"></a>Description
This readme file describes fabfed-py workflow model. The model consist of three high level classes:
- [ ] variable
- [ ] provider
- [ ] resource

The provider class supports two types as of this writing.
- [ ] fabric
- [ ] chi

The resource class support three types:
- [ ] node
- [ ] network

The workflow model allows us to tie resources (nodes or networks) to a provide and to express dependencies among resources. This is explained in more details below. We recommend you read on but under the <i>config directory</i>, you can find several templates to quickly get started.

- [fabfed credential file template](../config/fabfed_credentials_template.yml)
- [fabric template](../config/fabric_config_template.yml)
- [chi template](../config/chi_config_template.yml)
- [stitching template](../config/stitch_template.yml)

# <a name="variables"></a>Variables
Variables have their own class named <i>variable</i>. A variable consists of a name and a value. Its declaration 
uses the <i>default</i> attribute signifying that it can be overriden at runtime using an external file. More on this later. The variable <i>fabric_site<i> declared below can be referred to by the expression ```'{{ var.fabric_site }}'``` and similarly ```'{{ var.node_name }}'``` would refer to the variable node_name.
 

```
variable: # Class 
  - fabric_site:  # Name
      default: STAR. # Default value
  - node_name:     # Default for this variable is None
 
```

A variable need not be declared at all as long as it is injected by supplying an external var-file. This var-file consists of a set of key-value pairs and can be specified by using the --var-file option when using the fabfed tool. Each key-value pair is written as ```key: value```. The sample var-file below would override the value ```STAR``` of the <i>fabric_site<i> declared above, would set the value of node_name to ```my_node```. 
 
 The parsing process would halt if a variable is not bound to a value other than ```None```.
 
 ```
 fabric_site: TACC
 node_name: my_node
 ```
 
# <a name="providers"></a>Providers
A provider has its own class named <i>provider<i>. It consists of a <i>type</i>, a <i>label</i> and a dictionary specifying its attributes. The snippet below declares a <i>fabric</i> provider. As of now we support two types: <i>chi</i> and <i>fabric</i>. The credential_file and the profile are attributes that are used to configure the provider's environment.

A <i>resource</i> would refer to this provider using its type and its label like so: ```'{{ fabric.fabric_provider }}'```

```
provider: # Class 
  - fabric: # Type: Can be fabric or chi
    - fabric_provider: # Label: Can be any string
         credential_file: ~/.fabfed/fabfed_credentials.yml
         profile: fabric # This can be any string provided it is present in the credential file
```
 
 The credential_file and the profile are attributes that are used to configure the provider's environment.
 The credential file contains information specific to a user and to a provider. This [template credential file](../config/fabfed_credentials_template.yml) specifies the attributes must supply for two profiles.
 
# <a name="resources"></a>Resources
A resource consists of a <i>type</i>, a <i>label</i> and a dictionary specifying its attributes. The parsing process guarantees that the combination of the type and the label is unique. Resources can refer to each other using the expression ```'{{ type.label }}'```. They can also refer to a resource's attribute using ```'{{ type.label.attribute_name }}'```. We will see examples of this in subsequent sections.


As of now we support the followiing types: <i>node</i>, and <i>network</i>. The <i>label</i> can be any string and is used as the name of the resource if the <i>name</i> attribute is not present. Resources are declaed under their own class named <i>resource<i>. 
 
# <a name="nodes"></a>Nodes
A <i>node<i> <b>must</b> refer to a provider. Here it refers to the provider declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this node using its type and label like so: ```'{{ node.fabric_node }}'```
 
```
resource: # Class
  - node:  # Type can be node or network
      - fabric_node:  # Label can be any string
            provider: '{{ fabric.fabric_provider }}'
            site: '{{ var.fabric_site }}'
            count: 1
            image: default_rocky_8                                  
```
# <a name="networks"></a>Networks
A <i>network<i> <b>must</b> refer to a provider. Here it refers to the provider declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this network using its type and label like so: ```'{{ network.fabric_network }}'```
 
```
resource: # Class
   - network:  # Type can be node or network
      - fabric_network: # Label can be any string
            provider: '{{ fabric.fabric_provider }}'
            site: '{{ var.fabric_site }}'
            name: my_network
```
 
# <a name="dependencies"></a>Dependencies
A resource can depend on another resource before it can be created. In the example below, the fabric_network which is provissioned by the fabric_provider depends on the vlans from the chi_network which is by a diiferent provider. The ```vlans``` of the chi network are known after its creation. Using this dependency, fabfed makes sure chi_netwok is created first before the fabric_network. If a resource's dependencies are not satisfied, it would not get created. It would be flagged as pending.
 

```
 resource:
   - network:
      - chi_network:
            provider: '{{ chi.chi_provider }}'
            name: stitch_net
            vlans: []

  - network:
      - fabric_network:
            provider: '{{ fabric.fabric_provider }}'
            vlan: '{{ network.chi_network.vlans }}'
```
 # <a name="breaking"></a>Breaking The Configuration
 
 A configuration can be broken into many configuration files endining with ```.fab``` extensions. Fabfed does not care about how the files are named. It loads all the files residing in a given directory that match the pattern ```*.fab```. It does so in no particular order and then proceeds to parse the assembled result. see [Fabric Chameleon Stitch](../examples/stitch)
 
 

