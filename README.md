# Table of contents

 - [Description](#descr)
 - [Code Structure](#code)
 - [Installation](#install)
 - [Operation Instructions](#operate)

# <a name="descr"></a>Description
The FabFed is a Python library for a cross-testbed federation framework that (1) models the network experiment (or "slice") across the FABRIC testbed and federated testbeds and providers, and (2) provides workflow tools to stitch l2 and l3 networks between the testbeds and providers.

The FabFed code took the initial form from the Mobius API, and refactored and reinvented the slice modeling, user interface, data structure and  stitching workflows. 

The example below showcases network stitching of two slices, a [chi](https://www.chameleoncloud.org/) slice and a [fabric](https://portal.fabric-testbed.net/) slice. The configuration, while incomplete, highlights how fabfed-py expresses dependencies. In particular, line 17 states that the network labelled fabric_network gets its vlan from the chi_network. 

- For more details, refer to fabfed's [workflow design](./docs/workflow_design.md)
- For a complete example, refer to  [Fabric Chameleon Stitching](./config/stitch_template.yml)

```
  1 resource:
  2   - slice:
  3       - fabric_slice:
  4           - provider: '{{ fabric.fabric_provider }}'
  5   - slice:
  6       - chi_slice:
  7           - provider: '{{ chi.chi_provider }}'
  8   - network:
  9       - chi_network:
 10           - slice:  '{{ slice.chi_slice }}'
 11             site: CHI@UC
 12.            vlans: []
 13   - network:
 14       - fabric_network:
 15           - slice: '{{ slice.fabric_slice }}'
 16             site: 'STAR'
 17             vlan: '{{ network.chi_network.vlans}}'
```

# <a name="code"></a>Code Structure

# <a name="install"></a>Installation
You can install using the following command
```
pip install -e .
pytests -s tests/
fabfed --help
fabfed workflow --help
fabfed sessions --help
fabfed -h
```

# <a name="operate"></a>Operation Instructions

```
fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -validate

fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -apply

fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -show

fabfed workflow --config chi_config.yml --var-file vars.yml --session test-chi -destroy

fabfed sessions -show
```

