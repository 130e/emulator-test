#!/bin/bash

iperf3=iperf3 # at least 3.9
algo="westwood"

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
        while true
        do
            read -p "[client] Ready to test $outputfname; test? y/N" ans
            if ! [ -z "${ans}" ] && [ "${ans}" = "y" ]
            then
                $iperf3 -s -i 0.1 -J --logfile $outputfname -1
                newtest=true
            else
                echo "Skipped"
                break
            fi
            #if [ newtest ]
            #then
                #mv "./sv-test-c.log ./replay/sv-$fid-$algo.log"
            #fi
        done
    done
done
