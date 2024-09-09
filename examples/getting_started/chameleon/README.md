### Chi Example:

In this example, the configuration has been split into many files that end with extension <i>.fab</i>.
Fabfed does not care about how the files are named. It loads all the files matching the pattern <i>*.fab</i> in no particular order and then parses the assembled result:

    - vars.fab
    - providers.fab
    - resources.fab

## Provisioning

- [ ] Make sure your providers are configured properly using [fabfed credential file template](../../config/fabfed_credentials_template.yml). You can change the location of this templare in <i>providers.fab</i>
- [ ] Assumes fabfed-py has been installed
- [ ] Remember you need not be in this directory. You can use the --config-dir option.  
- [ ] The --session is used to track your workflows and <b>for chi it is as a prefix to name resources</b>.


```
cd examples/chi
fabfed workflow --help
## validate config
fabfed workflow --session <session> -validate

## provision resources
fabfed workflow --session <session> -apply

## display state. 
fabfed workflow --session <session> -show

## display sessions
fabfed sessions -show

## destroy Resources. 
fabfed workflow --session <session> -destroy
```
