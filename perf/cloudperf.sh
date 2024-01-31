#!/bin/bash

# Script Name: cloudperf.sh
# Description: This Bash script is designed to measure performance of Fabric and public clouds using FabFed.
# Authors: ESnet FabFed team
# Date: January 20, 2024

# Function to display script usage
display_usage() {
    echo "Usage: $0 <option>"
    echo "Options:"
    echo "  -h, --help    Display this help message"
    echo "  -v, --version Display script version"
    echo "  -p, --prefix Set the prefix: [gcp|aws]"
    echo "  -c, --concur Set the concurrency number"
    echo "  -d, --directory Set the directory for output data. The default is ~/temp/fabfed_data"
    echo "Examples:"
    echo "  $0 -p gcp -c 10"
    echo "  $0 -p gcp -c 10 -d ~/temp/fabfed_data"
}

# Function to display script version
display_version() {
    echo "Script Version 1.0"
}

# Main script starts here

# Check if the script is called with an argument
if [ $# -eq 0 ]; then
    display_usage
    exit 1
fi

session_prefix=""
N=0
data_directory="~/temp/fabfed_data"

# Process command line options
while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            display_usage
            exit 0
            ;;
        -v|--version)
            display_version
            exit 0
            ;;
        -p|--prefix)
            session_prefix=$2
            shift
            ;;
        -c|--concur)
            N=$2
            shift
            ;;
        -d|--directory)
            data_directory=$2
            shift
            ;;
        *)
            echo "Invalid option: $1"
            display_usage
            exit 1
            ;;
    esac
    shift
done

# Validate input parameters
if [[ -z $session_prefix ]]; then
    echo "Error: Session_prefix is incorrect"
    display_usage
fi
if [[ $N -le 0 ]]; then
    echo "Error: Concurrency is incorrect"
    display_usage
fi


# Init config dir
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# config_dir=/Users/lzhang9/Projects/fabric-testbed/fabfed/examples/$session_prefix
config_dir=$SCRIPT_DIR/../examples/$session_prefix

# Init vpc
index_step=1
if [ "$session_prefix" == "gcp" ]; then
    index_step=5    # max routers for each vpc
    vpc_array=(
        "vpc-69acc1d9-8c24-47cd-90b8-33be57167dbf" 
        "vpc-00d79c7f-debd-472e-8053-bb646c216183" 
        "vpc-33f21cdf-60af-4a96-bc48-3b0fb33dba5c" 
        "vpc-364676d0-ef76-4747-9612-65b899f40dd7" 
        "vpc-3bce06c3-6dba-4634-9713-685388807221")
elif [ "$session_prefix" == "aws" ]; then
    index_step=1    # max vgw for each vpc
    vpc_array=(
        "vpc-0936b973cf039f794" 
        "vpc-034da8fe2c9380fec"
        "vpc-05bf1ae332ca8b212"
        "vpc-0b98aec50e788b515"
        "vpc-03622eeacebd2999c"
        "vpc-0078659230c8965c0"
        "vpc-0f545e7c12a0db5bd"
        "vpc-05b18933db3b583c0"
        "vpc-0d6b6051615c003f5"
        "vpc-0fb12d80861220428"
        "vpc-0d79187d1f87c7813"
        "vpc-0a7449317ea631594"
        "vpc-0a77a4652771685ba")
fi

#
# Prepare config, log and var files
#
for (( i = 1, j = 0; i <= $N; i++ ))
do
    # echo $i $j
    mkdir -p $data_directory/$session_prefix-$i

    echo > $data_directory/$session_prefix-$i/fabfed.log

    rm -f $data_directory/$session_prefix-$i//*.fab
    cp $config_dir/*.fab $data_directory/$session_prefix-$i/
    if [ "$session_prefix" == "gcp" ]; then
        temp=${vpc_array[$j]}
        echo "vpc: $temp" > $data_directory/$session_prefix-$i/varfile.yml
        cat $data_directory/$session_prefix-$i/varfile.yml

        if [[ $(($i%$index_step)) -eq 0 ]]; then
            j=$(($j + 1))
        fi
    fi
    if [ "$session_prefix" == "aws" ]; then
        temp=${vpc_array[$j]}
        echo "vpc: $temp" > $data_directory/$session_prefix-$i/varfile.yml
        cat $data_directory/$session_prefix-$i/varfile.yml

        if [[ $(($i%$index_step)) -eq 0 ]]; then
            j=$(($j + 1))
        fi
    fi
done

#
# Apply
#
for (( i = 1; i <= $N; i++ ))
do
   cd $data_directory/$session_prefix-$i
   # echo fabfed workflow -s $session_prefix-$i -apply -c $config_dir 
   # fabfed workflow -s $session_prefix-$i -c $config_dir -apply  > /dev/null 2>&1 &
   if [[ -e $data_directory/$session_prefix-$i/varfile.yml ]]; then
    echo fabfed workflow -s $session_prefix-$i -v varfile.yml  -apply
    fabfed workflow -s $session_prefix-$i -v varfile.yml  -apply > /dev/null 2>&1 &
    # fabfed workflow -s $session_prefix-$i -v varfile.yml  -init
   else
    echo fabfed workflow -s $session_prefix-$i -apply
    fabfed workflow -s $session_prefix-$i -apply  > /dev/null 2>&1 &
    # fabfed workflow -s $session_prefix-$i -init
   fi 
   pids[${i}]=$!
   sleep 5
done

for pid in ${pids[*]}; do
    wait $pid
    # Check the exit status of the background process
    if [[ ! $? -eq 0 ]]; then
        echo "Error: stop and exit duo to errors in $pid."
        exit 1
    fi
done

for (( i = 1; i <= $N; i++ ))
do
   cd $data_directory/$session_prefix-$i
   # echo fabfed workflow -s $session_prefix-$i -c $config_dir -stats
   # fabfed workflow -s $session_prefix-$i -c $config_dir -stats
   if [[ -e $data_directory/$session_prefix-$i/varfile.yml ]]; then
    echo fabfed workflow -s $session_prefix-$i -v varfile.yml  -stats
    fabfed workflow -s $session_prefix-$i -v varfile.yml  -stats | tee stats-apply.yml
    fabfed workflow -s $session_prefix-$i -v varfile.yml  -show | tee show-apply.yml
    # fabfed workflow -s $session_prefix-$i -v varfile.yml  -validate 
   else
    echo fabfed workflow -s $session_prefix-$i -stats
    fabfed workflow -s $session_prefix-$i -stats| tee stats-apply.yml
    fabfed workflow -s $session_prefix-$i -show | tee show-apply.yml
    # fabfed workflow -s $session_prefix-$i -validate
   fi

   mv fabfed.log fabfed-apply.log
done

#
# Break
#
sleep 10


#
#  Destroy
#
for (( i = 1; i <= $N; i++ ))
do
   cd $data_directory/$session_prefix-$i
   # echo fabfed workflow -s $session_prefix-$i -c $config_dir -destroy
   # fabfed workflow -s $session_prefix-$i -c $config_dir -destroy > /dev/null 2>&1 &
   if [[ -e $data_directory/$session_prefix-$i/varfile.yml ]]; then
     echo fabfed workflow -s $session_prefix-$i -v varfile.yml  -destroy
     fabfed workflow -s $session_prefix-$i -v varfile.yml  -destroy > /dev/null 2>&1 &
     # fabfed workflow -s $session_prefix-$i -v varfile.yml  -validate 
   else
     echo fabfed workflow -s $session_prefix-$i -destroy
     fabfed workflow -s $session_prefix-$i -destroy  > /dev/null 2>&1 &
     # fabfed workflow -s $session_prefix-$i -validate
   fi 
   pids[${i}]=$!
   sleep 5
done

for pid in ${pids[*]}; do
    wait $pid
done

for (( i = 1; i <= $N; i++ ))
do
   cd $data_directory/$session_prefix-$i
   if [[ -e $data_directory/$session_prefix-$i/varfile.yml ]]; then
    echo fabfed workflow -s $session_prefix-$i -v varfile.yml  -stats
    fabfed workflow -s $session_prefix-$i -v varfile.yml  -stats | tee stats-destroy.yml
    fabfed workflow -s $session_prefix-$i -v varfile.yml  -show | tee show-destroy.yml
    # fabfed workflow -s $session_prefix-$i -v varfile.yml  -validate 
   else
    echo fabfed workflow -s $session_prefix-$i -stats
    fabfed workflow -s $session_prefix-$i -stats | tee stats-destroy.yml
    fabfed workflow -s $session_prefix-$i -show | tee show-destroy.yml
    # fabfed workflow -s $session_prefix-$i -validate
   fi

   mv fabfed.log fabfed-destroy.log 
done

#
# Generate stats
#

stat_tool=$SCRIPT_DIR/fabfed_stats.py
if [[ -e $stat_tool ]]; then
    cd $data_directory
    echo $stat_tool $data_directory/data $session_prefix $data_directory/mydata.csv
    $stat_tool $data_directory $session_prefix $data_directory/mydata.csv
    cat $data_directory/mydata.csv
fi

#
# Zip up
#
# rm $data_directory/$session_prefix-$N.zip
#
# for (( i = 1; i <= $N; i++ ))
# do
#    if [ -d $data_directory/$session_prefix-$i ]; then
#      zip -r $data_directory/$session_prefix-$N.zip $data_directory/$session_prefix-$i
#    fi
# done
# zip -r $data_directory/$session_prefix_c$N.zip $data_directory/mydata.csv

exit 0