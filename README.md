# Table of contents

 - [Description](#descr)
 - [Code Structure](#code)
 - [Installation](#install)
 - [Operation Instructions](#operate)

# <a name="descr"></a>Description
The FabFed is a Python library for a cross-testbed federation framework that (1) models the network experiment (or "slice") across the FABRIC testbed and federated testbeds and providers, and (2) provides workflow tools to stitch l2 and l3 networks between the testbeds and providers.

The FabFed code took the initial form from the Mobius API, and refactored and reinvented the slice modeling, user interface, data structure and  stitching workflows. 

The example below showcases network stitching of two slices, a fabric slice and a chameleon slice. The example while incomplete highlights how fafed-py expresses dependencies. In particular it shows how the fabric network gets its vlan from the chi network. For a complete example, refer to 
[Fabric Chameleoon Stitiching](./config/config_template.yml)

```
resource:
  - slice:
      - fabric_slice:
          - provider: '{{ fabric.fabric_provider }}'
  - slice:
      - chi_slice:
          - provider: '{{ chi.chi_provider }}'   
  - network:
      - chi_network:
          - slice:  '{{ slice.chi_slice }}'
            site: CHI@UC     
  - network:
      - fabric_network:
          - slice: '{{ slice.fabric_slice }}'
            site: 'STAR'
            vlan: '{{ network.chi_network.vlans}}'
```

# <a name="code"></a>Code Structure

# <a name="install"></a>Installation
You can install using the following command
```
pip install fabfed-py
```

# <a name="operate"></a>Operation Instructions

