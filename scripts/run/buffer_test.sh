./scripts/load-tc-rules.sh mod veth1 76 10000 $((200*1000000)) 524288 6
./scripts/load-tc-rules.sh mod veth2 43 10000 $((1400*1000000)) 2097152 3 &
