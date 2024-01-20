#!/usr/bin/env bash

script_dir=$(dirname $0)
echo $script_dir
cd $script_dir

cp controller.py /fabfed/controller/controller.py 
pip install --break-system-package / > /dev/null 2>&1

echo "PROJECT=$CHI_USER"
sed "s/CHI_PROJECT/$CHI_PROJECT/" fabfed_credentials.yml.replaceme > ~/fabfed_credentials.yml
cat ~/fabfed_credentials.yml

string=$CHI_PASSWORD
length=${#string}
echo "LENGTH=$length"

for ((i = 0; i < length; i++)); do
    char="${string:i:1}"
    echo "Character at position $i: $char"
done

exit 0

sed -i "s/CHI_PASSWORD/$CHI_PASSWORD/" ~/fabfed_credentials.yml
sed -i "s/CHI_USER/$CHI_USER/" ~/fabfed_credentials.yml

# set -ex

# fabfed workflow -s test-chi-stich -validate
# fabfed workflow -s test-chi-stich -init
# fabfed workflow -s test-chi-stich -apply
# fabfed sessions -show -json
fabfed workflow -s test-chi-stich -apply
fabfed workflow -s test-chi-stich -show -summary
fabfed workflow -s test-chi-stich -destroy
fabfed workflow -s test-chi-stich -show -summary
fabfed sessions -show -json
exit 0
