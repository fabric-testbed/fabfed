# Chameleon Example

- [ ] Make sure your providers are configured properly using [fabfed credential file template](../../config/fabfed_credentials_template.yml), You can change the location of this templare in <i>providers.fab</i>
- [ ] You need not be in this directory. You can use the <i>--config-dir</i>
- [ ] Assumes fabfed-py has been installed
```
cd examples/chi

fabfed workflow  --session chi -validate       # This should fail. Needs slice_name
echo "slice_name: REPLACE_ME" > vars.yml          # Make sure your slice name is "unique"
fabfed workflow  --var-file vars.yml --session chi  -validate
fabfed workflow  --var-file vars.yml --session chi  -apply
fabfed workflow  --var-file vars.yml --session chi  -show
fabfed sessions -show

# Destroy.
fabfed workflow  --var-file vars.yml --session chi -destroy
```
