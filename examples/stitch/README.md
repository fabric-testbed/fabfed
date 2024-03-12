### Stitch Example:

In this example, the configuration has been split into many files that end with the ```.fab``` extension.
Fabfed does not care about how the files are named. It loads all the files matching the pattern ```*.fab``` in no particular order and then parses the assembled result. 

    - providers.fab
    - networks.fab
    - nodes.fab

## Provisioning

- [ ] Make sure your providers are configured properly using [fabfed credential file template](../../config/fabfed_credentials_template.yml). You can change the location of this templare in <i>providers.fab</i>
- [ ] Assumes fabfed-py has been installed
- [ ] Remember you need not be in this directory. You can use the --config-dir option.  
- [ ] The --session is used to track your workflows and <b>for chi provider is used as a prefix to name the resources and for fabric it is used to name the slice.</b>


```
cd examples/stitch
fabfed workflow --help
## validate config
fabfed workflow --session <session> -validate

## shows the stitch info ... 
fabfed workflow --session <session> -init [-json]

## prints a summary of what resources will be added or deleted
fabfed workflow --session <session> -plan [-json]

## provision resources
fabfed workflow --session <session> -apply

## display state. 
fabfed workflow --session <session> -show [-json]

## display sessions
fabfed sessions -show

## destroy resources and the session if sucessful
fabfed workflow --session <session> -destroy
```
