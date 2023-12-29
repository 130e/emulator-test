#!/bin/bash

fname=cl-test-s.log
while true; do
    rm $fname
    echo "Ready to run - iperf client started"
    iperf3 -s -i 0.1 -J --logfile $fname -1
    echo "Waiting for key press to clear log and restart..."
    read
done
