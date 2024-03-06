#!/usr/bin/env bash

script_dir=$(dirname $0)
cd $script_dir

# workaround for now. 1.6.4 ould not need this
mkdir -p ~/work/fabric_config

mkdir -p ~/.fabfed

ls -l /creds

cp ../../fabfed_credentials.yml.cicd ~/.fabfed/
sed -i "s/FABRIC_PROJECT/$FABRIC_PROJECT/" ~/.fabfed/fabfed_credentials.yml.cicd
sed -i "s/FABRIC_USER/$FABRIC_USER/" ~/.fabfed/fabfed_credentials.yml.cicd

fabfed workflow -s test-fabric -plan 
exit $? 
