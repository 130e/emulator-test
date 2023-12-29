#!/bin/sh

[ $(id -u) -ne 0 ] && echo "must run as root" && exit 1

reload() {
    ifname="$1"
    delay="$2"
    delayLimit="$3"
    rate="$4"
    bucketsz=$((${rate}/250))
    queuesz="$5"
    tc qdisc del dev "${ifname}" root
    tc qdisc add dev "${ifname}" root handle 1:0 netem delay ${delay}ms limit ${delayLimit}
    tc qdisc add dev "${ifname}" parent 1:1 handle 10:0 tbf rate ${rate}bit burst ${bucketsz}b limit ${queuesz}b mtu 1500
}

modify() {
    ifname="$1"
    delay="$2"
    delayLimit="$3"
    rate="$4"
    bucketsz=$((${rate}/250))
    queuesz="$5"
    tc qdisc change dev "${ifname}" root handle 1:0 netem delay ${delay}ms limit ${delayLimit}
    tc qdisc change dev "${ifname}" parent 1:1 handle 10:0 tbf rate ${rate}bit burst ${bucketsz}b limit ${queuesz}b mtu 1500
}

echo "Remember to run in server netsh"
# ifname delay delayLimit rate queuesz
reload veth1 80 10000 $((60*1000000)) $((32*1024))

reload veth2 36 10000 $((1200*1000000)) $((1024*1024))
