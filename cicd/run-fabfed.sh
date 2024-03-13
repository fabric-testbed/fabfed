#!/usr/bin/env bash

conf_dir=$1
session=$2
var_file=$3

echo "CONF_DIR=$conf_dir"
echo "SESSION=$session"
echo "VAR_FILE=$var_file"

script_dir=$(dirname $0)

mkdir -p ~/work/fabric_config # workaround for now. 1.6.4 ould not need this
mkdir -p ~/.fabfed

cp $script_dir/fabfed_credentials.yml.cicd ~/.fabfed/
sed -i "s/FABRIC_PROJECT/$FABRIC_PROJECT/" ~/.fabfed/fabfed_credentials.yml.cicd
sed -i "s/FABRIC_USER/$FABRIC_USER/" ~/.fabfed/fabfed_credentials.yml.cicd

if [ -n "$var_file" ]
then
  options="-v $3"
fi

echo "***************** APPLYING  ****************"
echo fabfed workflow -c $conf_dir $options -s $session -apply
fabfed workflow -c $conf_dir $options -s $session -apply
ret1=$?

echo "***************** APPLY SUMMARY  ****************"
echo fabfed workflow -c $conf_dir $options -s $session -show -summary
summary=`fabfed workflow -c $conf_dir $options -s $session -show -summary`
fabfed workflow -c $conf_dir $options -s $session -show -summary
fabfed sessions -show

echo "***************** DESTOYING ****************"
echo fabfed workflow -c $conf_dir $options -s $session -destroy
fabfed workflow -c $conf_dir $options -s $session -destroy
ret2=$? 

echo "***************** DESTROY SUMMARY  ****************"
fabfed workflow -c $conf_dir $options -s $session -show -summary
fabfed sessions -show

echo "***************** APPLY RESULTS ****************"
echo "APPLY RESULTS:"
echo $summary

if [[ ! $ret1 -eq 0 ]]; then
     echo "Apply failed ....."
fi

if [[ ! $ret2 -eq 0 ]]; then
     echo "Destroy failed ....."
fi

if [[ ! $ret1 -eq 0 ]]; then
     exit 1
fi

if [[ ! $ret2 -eq 0 ]]; then
     exit 2
fi

exit 0
