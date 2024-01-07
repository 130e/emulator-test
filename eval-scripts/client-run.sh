#!/bin/bash

iperf3=iperf3 # at least 3.9

downtown=({1..6})
parkinglot=(7)
sportpark=(8 9)
airport=(10 11)
seaport=(12 13)

labels=('A' 'B' 'C' 'D' 'E' )
locations=(downtown parkinglot sportpark airport seaport)

for loc_idx in "${!locations[@]}"; do
    echo "location ${labels[$loc_idx]}"
    declare -n traces=${locations[$loc_idx]}
    for id in "${traces[@]}"; do
        fname="./replay/cl-$id-westwood.log"
        echo "prepare to test $fname"
        read ans

        if [ -z ${ans} ]; then
            echo "skipped"
        elif [ $ans = "y" ]; then
            $iperf3 -s -i 0.1 -J --logfile $fname -1
            echo "Waiting for key press to clear log and restart..."
        else
            echo "unkonwn input. Skipped."
        fi
    done
done
