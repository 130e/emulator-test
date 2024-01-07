#!/bin/bash

iperf3=iperf3 # at least 3.9
exe="./handoff"
algo="westwood"

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
        inputfname="./input/trace-$id-c.csv"
        outputfname="./replay/sv-$id-$algo.log"
        echo "prepare to test $inputfname and generate $outputfname"
        read ans

        if [ -z ${ans} ]; then
            echo "skipped"
        elif [ $ans = "y" ]; then
            $exe $inputfname
            echo "Waiting for key press to clear log and restart..."
            mv "./replay/sv-test-c.log ./replay/sv-$fid-$algo.log"
        else
            echo "unkonwn input. Skipped."
        fi
    done
done
