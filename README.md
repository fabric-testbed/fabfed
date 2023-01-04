# Table of contents

 - [Description](#descr)
 - [Installation](#install)
 - [Operation Instructions](#operate)

# <a name="descr"></a>Description
The FabFed is a Python library for a cross-testbed federation framework that (1) models the network experiment (or "slice") across the FABRIC testbed and federated testbeds and providers, and (2) provides workflow tools to stitch l2 and l3 networks between the testbeds and providers.

The FabFed code took the initial form from the Mobius API, and refactored and reinvented the slice modeling, user interface, data structure and  stitching workflows. 

The example below showcases network stitching across providers, a [chi](https://www.chameleoncloud.org/) provider and a [fabric](https://portal.fabric-testbed.net/) provider. The configuration, while incomplete, highlights how fabfed-py expresses dependencies. In particular, line 12 states that the network labeled `fabric_network` gets its `vlan` from the `chi_network`. 

- For more details, refer to fabfed's [workflow design](./docs/workflow_design.md)
- For a complete example, refer to  [Fabric Chameleon Stitching](./examples/stitch)

```
  1 resource:
  2
  3   - network:
  4       - chi_network:
  5             provider: '{{ chi.chi_provider }}'
  6             site: CHI@UC
  7             vlans: []
  8   - network:
  9       - fabric_network:
 10            provider: '{{ fabric.fabric_provider }}'
 11            site: 'STAR'
 12            vlan: '{{ network.chi_network.vlans}}'
```

# <a name="install"></a>Installation
You can install using the following command
```
pip install -r requirements.txt 
pip install -e .
fabfed --help
fabfed workflow --help
fabfed sessions --help
```

# <a name="operate"></a>Operation Instructions
- [ ] Fabfed worflow configuration is specified across one or more <i>.fab<i> files. Fabfed does not care how these files  are named. Fabfed simply loads all the .fab configuration files, assembles them and parses the assembled configuration.  
- [ ] Fabfed will pickup any file ending with the <b>.fab</b> extension in the directory specified by
the <i>--config-dir</i>.  If this option is not present, the current directory is used. 
- [ ] The --var-file option can be used to override the default value of any variable. It consists of a set of key-value pairs with each pair written as ```key: value```. At runtime, all variables found in an assembled configuration must have a value other than ```None```. The parser will halt and throw an exeption otherwise. 
- [ ] The --session is a friendly name used to track a given workflow.  
- [ ] Use the --help options shown above if in doubt. 

```
fabfed workflow --config-dir some_dir --var-file some_var_file.yml --session some_session -validate

fabfed workflow --config-dir some_dir --var-file some_var_file.yml --session some_session  -apply

fabfed workflow --config-dir some_dir --var-file some_var_file.yml --session some_session -show

fabfed workflow --config-dir some_dir --var-file some_var_file.yml --session some_session -destroy

fabfed sessions -show
```

