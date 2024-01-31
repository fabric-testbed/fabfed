#!/bin/bash

dest_dir=/tmp

config_dir=$1
session_prefix=$2
N=$3


prepare() {
  config_dir=$1
  session_prefix=$2
  N=$3
  session_prefix=$session_prefix-$N

  for (( i = 1; i <= $N; i++ )) 
  do
    mkdir -p $dest_dir/$session_prefix-$i
    echo > $dest_dir/$session_prefix-$i/fabfed.log
    rm -f $dest_dir/$session_prefix-$i//*.fab
    cp $config_dir/*.fab $dest_dir/$session_prefix-$i/
  done
}

run() {
  config_dir=$1
  session_prefix=$2
  N=$3
  action=$4
  session_prefix=$session_prefix-$N

  for (( i = 1; i <= $N; i++ )) 
  do
    config_dir=$dest_dir/$session_prefix-$i
    cd $dest_dir/$session_prefix-$i
    echo fabfed workflow -s $session_prefix-$i -$action
    fabfed workflow -s $session_prefix-$i -$action > /dev/null 2>&1 &
    pids[${i}]=$!
  done
}


waitFor() {
  star_pids=("$@")
  for pid in ${star_pids[*]}; do
    echo "AHA ....$pid"
    wait $pid
  done
}

save() {
  config_dir=$1
  session_prefix=$2
  N=$3
  action=$4
  session_prefix=$session_prefix-$N

  for (( i = 1; i <= $N; i++ )) 
  do
    config_dir=$dest_dir/$session_prefix-$i
    cd $dest_dir/$session_prefix-$i
    echo fabfed workflow -s $session_prefix-$i -stats
    fabfed workflow -s $session_prefix-$i -stats > stats-$action.yml
    fabfed workflow -s $session_prefix-$i -stats
    fabfed workflow -s $session_prefix-$i -show > show-$action.yml
    mv fabfed.log fabfed-$action.log
  done
}

prepare /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/tacc tacc-con 2
prepare /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/star star-con 2

all_pids=()
run /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/tacc tacc-con 2 apply
all_pids+=(${pids[*]})
run /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/star star-con 2 apply
all_pids+=(${pids[*]})
waitFor "${all_pids[@]}"
save /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/tacc tacc-con 2 apply
save /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/star star-con 2 apply

all_pids=()
run /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/tacc tacc-con 2 destroy
all_pids+=(${pids[*]})
run /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/star star-con 2 destroy 
all_pids+=(${pids[*]})
waitFor "${all_pids[@]}"
save /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/tacc tacc-con 2 destroy 
save /Users/AEssiari/FABRIC/testing2/fabfed/examples/demos/chameleon/star star-con 2 destroy 

script_dir=$(dirname $0)
echo $script_dir/fabfed_stats.py $dest_dir tacc-con 
$script_dir/fabfed_stats.py $dest_dir tacc-con- 
echo $script_dir/fabfed_stats.py $dest_dir star-con
$script_dir/fabfed_stats.py $dest_dir star-con- 
exit 0
