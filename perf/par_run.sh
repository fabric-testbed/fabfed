#!/bin/bash

config_dir=$1
session_prefix=$2
N=$3


session_prefix=$session_prefix-$N

for (( i = 1; i <= $N; i++ )) 
do
   mkdir -p /tmp/$session_prefix-$i
   echo > /tmp/$session_prefix-$i/fabfed.log
   rm -f /tmp/$session_prefix-$i//*.fab
   cp $config_dir/*.fab /tmp/$session_prefix-$i/
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -apply
   fabfed workflow -s $session_prefix-$i -apply > /dev/null 2>&1 &
   pids[${i}]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -stats > stats-apply.yml
   fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -show > show-apply.yml
   mv fabfed.log fabfed-apply.log
done

echo "Refresh token and hit any key when ready."
read key 

for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   sleep 2 
   echo fabfed workflow -s $session_prefix-$i -destroy
   fabfed workflow -s $session_prefix-$i -destroy > /dev/null 2>&1 &
   pids[${i}]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done


for (( i = 1; i <= $N; i++ )) 
do
   config_dir=/tmp/$session_prefix-$i
   cd /tmp/$session_prefix-$i
   echo fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -stats > stats-destroy.yml
   fabfed workflow -s $session_prefix-$i -stats
   fabfed workflow -s $session_prefix-$i -show > show-destroy.yml
   fabfed workflow -s $session_prefix-$i -show > show-destroy.yml
   mv fabfed.log fabfed-destroy.log
done

script_dir=$(dirname $0)
echo $script_dir/fabfed_stats.py /tmp $session_prefix-
$script_dir/fabfed_stats.py /tmp $session_prefix-
exit 0
