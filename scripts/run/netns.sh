#!/bin/sh
set -e

[ $(id -u) -ne 0 ] && echo "must run as root" && exit 1

print_help() {
  echo "usage: $PROGRAM <create|exec|destroy> ..."
}

print_create_help() {
  echo "usage: $PROGRAM create <net> <host_a> <host_b> <number_of_veth>"
}

print_exec_help() {
  echo "usage: $PROGRAM exec <net> <host> <command> [args...]"
}

print_destroy_help() {
  echo "usage: $PROGRAM destroy <net>"
}

create_netns() {
  net="$2"
  host_a="$3"
  host_b="$4"
  n="$5"
  if [ -z "$net" ] || [ -z "$host_a" ] || [ -z "$host_b" ] || [ "$host_a" = "$host_b" ] || [ ! -n "$n" ] || [ "$n" -lt 1 ]; then
    print_create_help
    exit 1
  fi
  netns_a="${net}_${host_a}"
  netns_b="${net}_${host_b}"
  echo "creating net namespaces"
  ip netns add "$netns_a"
  ip netns add "$netns_b"
  ip -netns "$netns_a" link set dev lo up
  ip -netns "$netns_b" link set dev lo up
  echo "creating veth pairs"
  for i in $(seq 1 $n); do
    veth_name="veth$(($i - 1))"
    ip -netns "$netns_a" link add dev "$veth_name" type veth peer name "${veth_name}_b"
    ip -netns "$netns_a" link set "${veth_name}_b" netns "$netns_b" 
    ip -netns "$netns_b" link set "${veth_name}_b" name "$veth_name"
    ip -netns "$netns_a" addr add "10.0.0.1/32" dev "$veth_name"
    ip -netns "$netns_a" link set dev "$veth_name" up
    ip -netns "$netns_b" addr add "10.0.0.2/32" dev "$veth_name"
    ip -netns "$netns_b" link set dev "$veth_name" up
  done
  ip -netns "$netns_a" route add 10.0.0.2 dev veth0
  ip -netns "$netns_b" route add 10.0.0.1 dev veth0
  echo "created netns [$netns_a] and [$netns_b] with $n veth pair(s)"
}

exec_netns() {
  net="$2"
  host="$3"
  if [ -z "$net" ] || [ -z "$host" ] || [ $# -lt 3 ]; then
    print_exec_help
    exit 1
  fi
  shift; shift; shift
  ip netns exec "${net}_${host}" "$@"
}

destroy_netns() {
  net="$2"
  if [ -z "$net" ]; then
    print_destroy_help
    exit 1
  fi
  echo "deleting all netns with prefix [$net]"
  ip netns ls | grep "^$net" | xargs -r -n 1 ip netns delete
}

case "$1" in
  create)
    create_netns "$@"
  ;;
  exec)
    exec_netns "$@"
  ;;
  destroy)
    destroy_netns "$@"
  ;;
  *)
    print_help
    exit 1
  ;;
esac
