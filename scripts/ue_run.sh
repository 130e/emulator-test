#/bin/sh
set -e

[ $(id -u) -ne 0 ] && echo "must run as root" && exit 1

echo "Run in UE chroot"

iptables-legacy -A OUTPUT -m tcp -p tcp --dport 5201 -j NFQUEUE --queue-num 0
iptables-legacy -A INPUT -m tcp -p tcp --sport 5201 -j NFQUEUE --queue-num 1
