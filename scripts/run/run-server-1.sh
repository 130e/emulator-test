#!/bin/bash

rm server-test.log
make
#echo $1
./handoff $1
