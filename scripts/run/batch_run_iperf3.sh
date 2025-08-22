#!/bin/bash

set -e

ROOTDIR="/data/ztliu/emulator-test"
INPUTDIR="$ROOTDIR/input"
OUTPUTDIR="$ROOTDIR/scripts/processing/output"
iperf3=iperf3 # at least 3.9
emulator="$ROOTDIR/build/emulator"
PORT=5257
algo="$1"

if [ -z "$algo" ]; then
    echo "Error: specify TCP congestion control algorithm"
    exit
fi

debug=(5)
downtown=({1..6})
parkinglot=(7)
sportpark=(8 9)
airport=(10 11)
seaport=(12 13)

labels=('DEBUG' 'A' 'B' 'C' 'D' 'E')
locations=(debug downtown parkinglot sportpark airport seaport)

for loc_idx in "${!locations[@]}"; do
    echo "scenario ${labels[$loc_idx]}"
    echo "================"
    declare -n traces=${locations[$loc_idx]}
    for id in "${traces[@]}"; do
        original_trace="$INPUTDIR/trace-$id.csv"
        emulator_input="$OUTPUTDIR/trace-$id-test.csv"
        sv_iperf_log="$OUTPUTDIR/$algo-$id-iperf-server.json"
        sv_ss_log="$OUTPUTDIR/$algo-$id-ss-server.log"
        cl_iperf_log="$OUTPUTDIR/$algo-$id-iperf-client.json"

        echo "Iperf3 server log: $sv_iperf_log"
        echo "Iperf3 client log: $cl_iperf_log"

        while [ true ]; do
            echo "Remember to run tcpdump:"
            echo "  tcpdump -i any -s 100 -w $algo-$id-capture-client.pcap"
            read -p "Start test? (clean all logs) y/N <--- " ans </dev/tty
            if [ "$ans" = "y" ]; then
                # Generate test
                python3 $ROOTDIR/scripts/run/generate_input.py $original_trace $emulator_input $sv_iperf_log $sv_ss_log
                if pgrep -x "iperf3" >/dev/null; then
                    echo "Error: there are unfinished iperf3 process"
                    echo "----------------"
                else
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
                    echo -e "\a"

                    mv ./packet.log "$OUTPUTDIR/$algo-$id-capture-server.log"
                fi
            else
                break
            fi
            echo "----------------"
        done
        echo "----------------"
    done
done
