### Fabric Example:

In this example, the configuration is in a single file ```fabric_config.fab```. We can break this file into many ```.fab``` files and in any way we see fit. Remember Fabfed does not care about how the files are named. It loads all the files matching the pattern ```*.fab``` in no particular order and then parses the assembled result.
    
A close look at vars.fab reveals a variable <i>slice_name</i> with default value ```None```. And so validation will fail complaining about "variable slice_name is not bound"

```
# This should fail .... "variable slice_name is not bound"
fabfed workflow --session fabric -validate
```

There are two ways to fix this: One approach is to modify vars.fab and specify a default value like so. 

```
variable:
  - fabric_site:
      - default: STAR
 - slice_name:
     - default: REPLACE_ME
```

Here we will follow a second approach. We will use the --var-file option to supply a value to slice_name. The var-file is a simple yaml file containing key-value pairs. Each pair is written as ```key: value```.

```
# You can use your favorite editor or just the echo command. 
echo "slice_name: REPLACE_ME" > var-file.yml
cat var-file.yml 

```

## Provisioning

- [ ] Make sure your providers are configured properly using [fabfed credential file template](../../config/fabfed_credentials_template.yml). You can change the location of this templare in <i>providers.fab</i>
- [ ] Assumes fabfed-py has been installed
- [ ] Assumes var-file.yml has been created as explained above. 
- [ ] Remember you need not be in this directory. You can use the --config-dir option.  
- [ ] The --session is used to track your workflows   


```
cd examples/stitch
fabfed workflow --help

## validate config
fabfed workflow --var-file var-file.yml --session fabric -validate

## provision resources
fabfed workflow --var-file var-file.yml --session fabric -apply

## display state. 
fabfed workflow --var-file var-file.yml --session fabric -show

## display sessions
fabfed sessions --help
fabfed sessions -show

## destroy Resources. 
fabfed workflow --var-file var-file.yml --session fabric -destroy
```
