#!/bin/sh
set -e

[ $(id -u) -ne 0 ] && echo "must run as root" && exit 1

echo "Remember to run in 10.0.0.1"

iptables -A OUTPUT -m tcp -p tcp --dport 5201 -j NFQUEUE --queue-num 0
iptables -A INPUT -m tcp -p tcp --sport 5201 -j NFQUEUE --queue-num 1
#iptables -A OUTPUT -m mark --mark 1 -j NFQUEUE --queue-num 1
#iptables -A OUTPUT -m mark --mark 2 -j NFQUEUE --queue-num 2
ip route add 10.0.0.2 dev veth1 table 1
ip route add 10.0.0.2 dev veth2 table 2
ip rule add fwmark 1 lookup 1
ip rule add fwmark 2 lookup 2

#echo "Set to veth1 by default."
#iptables -t mangle -A OUTPUT -m tcp -p tcp --dport 5201 -j MARK --set-mark 1
