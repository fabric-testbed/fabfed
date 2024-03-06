#!/usr/bin/env bash

script_dir=$(dirname $0)
cd $script_dir

# workaround for now. 1.6.4 would not need this
mkdir -p ~/work/fabric_config
mkdir -p ~/.fabfed

cp ../../fabfed_credentials.yml.cicd ~/.fabfed/
sed -i "s/FABRIC_PROJECT/$FABRIC_PROJECT/" ~/.fabfed/fabfed_credentials.yml.cicd
sed -i "s/FABRIC_USER/$FABRIC_USER/" ~/.fabfed/fabfed_credentials.yml.cicd

fabfed workflow -s test-fabric-l2vpn -plan 
fabfed workflow -s test-fabric-l2vpn -apply
fabfed workflow -s test-fabric-l2vpn -show
exit 0
