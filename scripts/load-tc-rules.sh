#!/bin/sh

[ $(id -u) -ne 0 ] && echo "must run as root" && exit 1

load() {
    ifname="$1"
    delay="$2"
    delayLimit="$3"
    rate="$4"
    bucketsz=$((${rate}/250))
    queuesz="$5"
    jitter="$6"
    tc qdisc del dev "${ifname}" root
    tc qdisc add dev "${ifname}" root handle 1:0 netem delay ${delay}ms ${jitter}ms limit ${delayLimit}
    tc qdisc add dev "${ifname}" parent 1:1 handle 10:0 tbf rate ${rate}bit burst ${bucketsz}b limit ${queuesz}b mtu 1500
}

modify() {
    ifname="$1"
    delay="$2"
    delayLimit="$3"
    rate="$4"
    bucketsz=$((${rate}/250))
    queuesz="$5"
    jitter="$6"
    # netem rate limit?
    #tc qdisc change dev "${ifname}" root handle 1:0 netem rate 1200mbit delay ${delay}ms ${jitter}ms limit ${delayLimit}
    tc qdisc change dev "${ifname}" root handle 1:0 netem delay ${delay}ms ${jitter}ms limit ${delayLimit}
    tc qdisc change dev "${ifname}" parent 1:1 handle 10:0 tbf rate ${rate}bit burst ${bucketsz}b limit ${queuesz}b mtu 1500
}

# ifname delay delayLimit rate queuesz jitter
#reload veth1 80 10000 $((60*1000000)) $((32*1024))
#reload veth2 35 10000 $((1200*1000000)) $((1024*1024))

case "$1" in
    init)
        echo "INIT TC rules"
        load veth1 75 10000 $((200*1000000)) $((64*1024)) 5 
        load veth2 33 10000 $((1400*1000000)) $((1024*1024)) 3
        ;;
    mod)
        echo "modding TC rules"
        modify $2 $3 $4 $5 $6 $7
        ;;
    *)
        echo "$1"
        exit 1
        ;;
esac
