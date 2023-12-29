#!/bin/bash

rm sv-test-s.log
make
#echo $1
./handoff $1
