#!/bin/bash

set -e

ROOTDIR="/data/ztliu/emulator-test"
INPUTDIR="$ROOTDIR/input"
OUTPUTDIR="$ROOTDIR/output"
iperf3=iperf3 # at least 3.9
emulator="$ROOTDIR/build/emulator"
PORT=5257
algo="$1"

if [ -z "$algo" ]; then
    echo "Error: specify TCP congestion control algorithm"
    exit
fi

downtown=({1..6})
parkinglot=(7)
sportpark=(8 9)
airport=(10 11)
seaport=(12 13)

labels=('A' 'B' 'C' 'D' 'E')
locations=(downtown parkinglot sportpark airport seaport)

for loc_idx in "${!locations[@]}"; do
    echo "location ${labels[$loc_idx]}"
    echo "================"
    declare -n traces=${locations[$loc_idx]}
    for id in "${traces[@]}"; do
        # DEBUG overrride
        # id="debug"

        original_trace="$INPUTDIR/trace-$id.csv"
        emulator_input="$OUTPUTDIR/trace-$id-test.csv"
        sv_iperf_log="$OUTPUTDIR/server-iperf3-$id-$algo.log"
        sv_ss_log="$OUTPUTDIR/server-ss-$id-$algo.log"
        cl_iperf_log="$OUTPUTDIR/client-iperf3-$id-$algo.log"

        echo "Input trace: $sv_iperf_log"

        # Generate test
        python3 $ROOTDIR/scripts/run/generate_input.py $original_trace $emulator_input $sv_iperf_log $sv_ss_log

        read -p "Start test? (will clean all logs) y/N <--- " ans </dev/tty
        if [ "$ans" = "y" ]; then
            if [ -f $cl_iperf_log ]; then
                rm -f $cl_iperf_log
            fi
            sudo ip netns exec test_b $iperf3 -s -p $PORT -i 0.1 -J --logfile $cl_iperf_log -1 &
            sleep 2
            if [ -f $sv_iperf_log ]; then
                rm -f $sv_iperf_log
            fi
            if [ -f $sv_ss_log ]; then
                rm -f $sv_ss_log
            fi
            sudo ip netns exec test_a $emulator $algo $emulator_input
            sleep 5
        fi

        echo "----------------"
        read -p "Press Enter to continue" </dev/tty
    done
done
