#!/usr/bin/env bash

script_dir=$(dirname $0)
cd $script_dir

# workaround for now. 1.6.4 ould not need this
mkdir -p ~/work/fabric_config
mkdir -p ~/.fabfed

sed -i "s/FABRIC_PROJECT/$FABRIC_PROJECT/" fabfed_credentials.yml.cicd
sed -i "s/FABRIC_USER/$FABRIC_USER/" fabfed_credentials.yml.cicd
echo "$FABRIC_TOKEN" > /token.json

cp fabfed_credentials.yml.cicd ~/.fabfed/

echo "$FABRIC_BASTION_KEY" > /bastion
echo "$FABRIC_SLIVER_KEY" > /sliver
echo "$FABRIC_SLIVER_PUBKEY" > /sliver.pub

fabfed workflow -s test-fabric-l2vpn -plan 
fabfed workflow -s test-fabric-l2vpn -apply
fabfed workflow -s test-fabric-l2vpn -show
exit 0
