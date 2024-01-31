#!/bin/bash

config_dir=$1
session_prefix=$2
N=$3

session_prefix=$session_prefix-$N

vlan=3100
# vlan=3110

for (( i = 1; i <= $N; i++ )) 
do
   mkdir -p /tmp/$session_prefix-$i
   echo > /tmp/$session_prefix-$i/fabfed.log
   cp $config_dir/*.fab /tmp/$session_prefix-$i/
   temp=`expr $vlan + $i`
   echo "vlan: $temp" > /tmp/$session_prefix-$i/varfile.yml
   cat /tmp/$session_prefix-$i/varfile.yml
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -v varfile.yml -apply
   fabfed workflow -s $session_prefix-$i -v varfile.yml -apply > /dev/null 2>&1 &
   fabfed workflow -s $session_prefix-$i -show > show-apply.yml
   pids[${i}]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -v varfile.yml -stats
   fabfed workflow -s $session_prefix-$i -v varfile.yml -stats > stats-apply.yml
   fabfed workflow -s $session_prefix-$i -v varfile.yml -stats
   fabfed workflow -s $session_prefix-$i -v varfile.yml -show > show-apply.yml
   mv fabfed.log fabfed-apply.log
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -v varfile.yml -destroy
   fabfed workflow -s $session_prefix-$i -v varfile.yml -destroy > /dev/null 2>&1 &
   pids[${i}]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -v varfile.yml -stats
   fabfed workflow -s $session_prefix-$i -v varfile.yml -stats > stats-destroy.yml
   fabfed workflow -s $session_prefix-$i -v varfile.yml -stats
   fabfed workflow -s $session_prefix-$i -v varfile.yml -show > show-destroy.yml
   fabfed workflow -s $session_prefix-$i -show > show-destroy.yml
   mv fabfed.log fabfed-destroy.log
done

script_dir=$(dirname $0)
echo $script_dir/fabfed_stats.py /tmp $session_prefix-
$script_dir/fabfed_stats.py /tmp $session_prefix-
exit 0
