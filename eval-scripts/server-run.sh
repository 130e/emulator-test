#!/bin/bash

iperf3=iperf3 # at least 3.9
exe="./handoff"
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
        inputfname="./input/trace-$id-c.csv"
        outputfname="./replay/sv-$id-$algo.log"
        newtest=false
        echo "[server] Ready to test $inputfname and generate $outputfname"
        while true
        do
            read -p "test? y/N <- " ans
            if ! [ -z "${ans}" ] && [ "${ans}" = "y" ]
            then
                netstat -s | grep segments > prev-${algo}.txt
                $exe $inputfname
                newtest=true
                sleep 1
                netstat -s | grep segments > after-${algo}.txt
                mv ./sv-test-c.log $outputfname
                echo "file written"
            else
                echo "Skipped"
                break
            fi
        done
        #if [ $newtest = true ]
        #then
            #echo "New file written"
            #mv "./sv-test-c.log ./replay/sv-$fid-$algo.log"
        #fi
    done
done
