#!/bin/bash

iperf3=iperf3 # at least 3.9
emulator="/data/ztliu/emulator-test/build/emulator"
algo="$1"

if [ -z "$algo" ]
then
    echo "Error: specify TCP congestion control algorithm"
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
    echo "================"
    declare -n traces=${locations[$loc_idx]}
    for id in "${traces[@]}"
    do
        inputfname="./input/trace-$id-c.csv"
        serverOutput="./output/server-$id-$algo.log"
        clientOutput="./output/client-$id-$algo.log"
        echo "Input trace: $inputfname"
        while true
        do
            read -p "> Run test? y/N <- " ans
            if ! [ -z "${ans}" ] && [ "${ans}" = "y" ]
            then
                echo "Running test..."

                echo "[Client] $clientOutput"
                sudo ip netns exec test_b $iperf3 -s -i 0.1 -J --logfile $clientOutput -1 &

                sleep 1
                
                echo "[Server] $serverOutput"
                sudo ip netns exec test_a $emulator $algo $inputfname
                sudo mv ./sv-test-c.log $serverOutput
                echo "[Server] Fixed server fname"
            else
                echo "Skipped"
                break
            fi
        done
        echo "----------------"
    done
done
