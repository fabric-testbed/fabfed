# Table of contents

 - [Description](#descr)
 - [Variables](#variables)
 - [Providers](#providers)
 - [Resources](#resources)
 - [Slices](#slices)
 - [Nodes](#nodes)
 - [Networks](#networks)
 - [Dependencies](#dependencies)

# <a name="descr"></a>Description
This readme file describes fabfed-py workflow model. The model consist of three high level classes:
- [ ] variable
- [ ] provider
- [ ] resource

The provider class supports two types as of this writing.
- [ ] fabric
- [ ] chi

The resource class support three types:
- [ ] slice
- [ ] node
- [ ] network

The workflow model allows us to tie a slice to a provider, a node or a network to a slice, and finally it allows to express dependencies among resources. This is explained in more details below. We recommend you read on but under the <i>config directory</i>, you can find several templates to quickly get started.

- [fabfed credential file template](../config/fabfed_credentials_template.yml)
- [fabric template](../config/fabric_config_template.yml)
- [chi template](../config/chi_config_template.yml)
- [stitching template](../config/stitch_template.yml)

# <a name="variables"></a>Variables
Variables have their own class named <i>variable</i>. A variable consists of a name and a value. Its declaration 
uses the <i>default</i> attribute signifying that it can be overriden by supplying a value in an external variable file. The variable <i>fabric_site<i> declated below can be referred to by the expression '{{ var.fabric_site }}'. 
 

```
variable: # Class 
  - fabric_site:  # Name
      - default: STAR. # Default value
 
```

 A variable need not be declared at all as long as it is injected by supplying an external file.  This sample variable file would override the value of the <i>fabric_site<i> declared above and would inject the variable <i>slice_name<i>.
 So any reference to '{{ var.slice_name }}' would be replaced by the value <i>test_slice</i>. 
 
 The parsing process would halt if a variable is not bound to a value. 
 
 ```
 slice_name: test_slice
 fabric_site: TACC
 ```
 
# <a name="providers"></a>Providers
A provider has its own class named <i>provider<i>. It consists of a <i>type</i>, a <i>label</i> and a dictionary specifying its attributes. The snippet below declares a <i>fabric</i> provider. As of now we support two types: <i>chi</i> and <i>fabric</i>. The credential_file and the profile are attributes that are used to configure the provider's environment.

A <i>slice</i> would refer to this provider using its type and its label like so: '{{ fabric.fabric_provider }}'

```
provider: # Class 
  - fabric: # Type: Can be fabric or chi
    - fabric_provider: # Label: Can be any string
       - credential_file: ~/.fabfed/fabfed_credentials.yml
         profile: fabric # This can be any string provided it is present in the credential file
```
 
 The credential_file and the profile are attributes that are used to configure the provider's environment.
 The credential file contains information specific to a user and to a provider. This [template credential file](../config/fabfed_credentials_template.yml) specifies the attributes must supply for two profiles.
 
# <a name="resources"></a>Resources
A resource consists of a <i>type</i>, a <i>label</i> and a dictionary specifying its attributes. The parsing process guarantees that the combination of the type and the label is unique. Resources can refer to each other using the expression '{{ type.label }}'. They can also refer to a resource's attribute using '{{ type.label.attribute_name }}'. We will see examples of this in subsequent sections.


As of now we support three types: <i>slice</i>, <i>node</i>, and <i>network</i>. The <i>label</i> can be any string and is used as the name of the resource if the <i>name</i> attribute is not present. Resources are declaed under their own class named <i>resource<i>. 
 

# <a name="slices"></a>Slices
The snippet below declares a fabric slice. A slice <b>must</b> refer to a provider. Here it refers to the provider
declared above. The <i>name</i> of the slice is set the variable <i>slice_name</i> that must be declared in the config file or injected.  If this <i>name</i> attribute were not present, the label would be used to name this slice instead. 

A <i>node</i> or a <i>network</i> would refer to this slice using its type and its label like so: '{{ slice.fabric_slice }}'

```
resource: # Class
  - slice: # Type can be slice, node, or network
      - fabric_slice: # Label
          - provider: '{{ fabric.fabric_provider }}'
            name: '{{ var.slice_name }}'
```
# <a name="nodes"></a>Nodes
A <i>node<i> <b>must</b> refer to a slice. Here it refers to the slice declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this node using its type and label like so: '{{ node.fabric_node }}'
 
```
resource: # Class
  - node:  # Type can be slice, node or network
      - fabric_node:  # Label can be any string
          - slice:  '{{ slice.fabric_slice }}'
            site: '{{ var.fabric_site }}'
            count: 1
            image: default_rocky_8                                  
```
# <a name="networks"></a>Networks
A <i>network<i> <b>must</b> refer to a slice. Here it refers to the slice declared above. 
 
A <i>node</i> or a <i>network</i> would refer to this network using its type and label like so: '{{ network.fabric_network }}'
 
```
resource: # Class
   - network:  # Type can be slice, node or network
      - fabric_network: # Label can be any string
          - slice: '{{ slice.fabric_slice }}'
            site: '{{ var.fabric_site }}'
            name: my_network
```
 
# <a name="dependencies"></a>Dependencies
A resource can depend on another resource before it can be created. The example below shows how the chi_network which belongs to the chi_slice depends on the vlan from the fabric_network which is in a different slice. The vlan of the chi network is known after its creation. Using this dependency fabfed makes sure chi_netwok is created first and then extracts the vlan attribute and then proceeds to create the fabric_network. The name of the attribute need not be the same. Finally, if a resource's dependencies are not satisfied, it would not get created. it would be flagged as pending.
 

```
 resource:
   - network:
      - chi_network:
          - slice:  '{{ slice.chi_slice }}'
            name: aes_super_stitch_net

  - network:
      - fabric_network:
          - slice: '{{ slice.fabric_slice }}'
            vlan: '{{ network.chi_network.vlan }}'
```

