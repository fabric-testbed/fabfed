#!/bin/bash

config_dir=$1
session_prefix=$2
N=$3

for (( i = 1; i <= $N; i++ )) 
do
   mkdir -p /tmp/$session_prefix-$i
   echo > /tmp/$session_prefix-$i/fabfed.log
   rm -f /tmp/$session_prefix-$i/*.fab
   cp $config_dir/*.fab /tmp/$session_prefix-$i/
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -apply
   fabfed workflow -s $session_prefix-$i -apply > /dev/null 2>&1
   mv fabfed.log fabfed-apply.log

   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -stats > stats-apply.yml
   fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -show > show-apply.yml
done

echo "Refresh token and hit any key when ready."
read key
echo "GOING TO SLEEP $key"
sleep 30

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -destroy
   fabfed workflow -s $session_prefix-$i -destroy > /dev/null 2>&1
   mv fabfed.log fabfed-destroy.log

   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -stats > stats-destroy.yml
   fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -show > show-destroy.yml
done

script_dir=$(dirname $0)
$script_dir/fabfed_stats.py /tmp $session_prefix- 
exit 0
