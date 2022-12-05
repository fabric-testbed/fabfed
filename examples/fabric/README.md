### Fabric Example:

In this example, the configuration is in a single file ```fabric_config.fab```. We can break this file into many ```.fab``` files and in any way we see fit. Remember Fabfed does not care about how the files are named. It loads all the files matching the pattern ```*.fab``` in no particular order and then parses the assembled result.
    
```
fabfed workflow --session <session> -validate
```


## Provisioning

- [ ] Make sure your providers are configured properly using [fabfed credential file template](../../config/fabfed_credentials_template.yml). You can change the location of this templare in <i>providers.fab</i>
- [ ] Assumes fabfed-py has been installed
- [ ] Remember you need not be in this directory. You can use the --config-dir option.  
- [ ] The --session is used to track your workflows and <b>for fabric it is used to name the slice.</b>


```
cd examples/fabric
fabfed workflow --help

## validate config
fabfed workflow --session <session> -validate

## provision resources
fabfed workflow --session <session> -apply

## display state. 
fabfed workflow --session <session> -show

## display sessions
fabfed sessions --help
fabfed sessions -show

## destroy Resources. 
fabfed workflow --session <session> -destroy
```
