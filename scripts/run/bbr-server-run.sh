#!/bin/bash
fname=sv-test-b.log
trace=$1
rm $fname
make
./handoff $trace
