### Chi Example:

In this example, the configuration has been split into many files that end with extension <i>.fab</i>.
Fabfed does not care about how the files are named. It loads all the files matching the pattern <i>*.fab</i> in no particular order and then parses the assembled result:

    - vars.fab
    - providers.fab
    - slices.fab
    - resources.fab
    
A close look at vars.fab reveals a variable <i>slice_name</i> with default value ```None```. And so validation will fail complaining about "variable slice_name is not bound"

```
# This should fail .... "variable slice_name is not bound"
fabfed workflow --session chi -validate
```

There are two ways to fix this: One approach is to modify vars.fab and specify a default value like so. 

```
variable:
  - chi_site:
      - default: CHI@UC
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
fabfed workflow --var-file var-file.yml --session chi -validate

## provision resources
fabfed workflow --var-file var-file.yml --session chi -apply

## display state. 
fabfed workflow --var-file var-file.yml --session chi -show

## display sessions
fabfed sessions -show

## destroy Resources. 
fabfed workflow --var-file var-file.yml --session chi -destroy
```
