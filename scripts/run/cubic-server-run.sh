#!/bin/bash

rm sv-test-c.log
make
#echo $1
./handoff $1
