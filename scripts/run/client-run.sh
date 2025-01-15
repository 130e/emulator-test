#!/bin/bash

iperf3=iperf3 # at least 3.9
algo="$1"

if [ -z "$algo" ]
then
    echo "specify algorithm"
    exit
fi

downtown=({1..6})
parkinglot=(7)
sportpark=(8 9)
airport=(10 11)
seaport=(12 13)

labels=('A' 'B' 'C' 'D' 'E' )
locations=(downtown parkinglot sportpark airport seaport)

for loc_idx in "${!locations[@]}"
do
    echo "location ${labels[$loc_idx]}"
    declare -n traces=${locations[$loc_idx]}
    for id in "${traces[@]}"
    do
        outputfname="./replay/cl-$id-$algo.log"
        newtest=false
        echo "[client] Ready to test $outputfname"
        while true
        do
            read -p "test? y/N <- " ans
            if ! [ -z "${ans}" ] && [ "${ans}" = "y" ]
            then
                $iperf3 -s -i 0.1 -J --logfile $outputfname -1
                newtest=true
            else
                echo "Skipped"
                break
            fi
        done
    done
done
