#!/bin/sh

# Check if the script is run as root
[ "$(id -u)" -ne 0 ] && echo "This script must be run as root" && exit 1

# Function to add TC rules
load() {
    local ifname="$1"
    local delay="$2"
    local delayLimit="$3"
    local rate="$4"
    local queuesz="$5"
    local jitter="$6"

    # Validate required parameters
    [ -z "$ifname" ] || [ -z "$delay" ] || [ -z "$delayLimit" ] || [ -z "$rate" ] || [ -z "$queuesz" ] || [ -z "$jitter" ] && {
        echo "Error: Missing parameters for 'load'"
        return 1
    }

    local bucketsz=$((rate / 250))

    tc qdisc del dev "$ifname" root 2>/dev/null
    tc qdisc add dev "$ifname" root handle 1:0 netem delay "${delay}ms" "${jitter}ms" limit "$delayLimit"
    tc qdisc add dev "$ifname" parent 1:1 handle 10:0 tbf rate "${rate}bit" burst "${bucketsz}b" limit "${queuesz}b" mtu 1500
}

# Function to modify existing TC rules
modify() {
    local ifname="$1"
    local delay="$2"
    local delayLimit="$3"
    local rate="$4"
    local queuesz="$5"
    local jitter="$6"

    # Validate required parameters
    [ -z "$ifname" ] || [ -z "$delay" ] || [ -z "$delayLimit" ] || [ -z "$rate" ] || [ -z "$queuesz" ] || [ -z "$jitter" ] && {
        echo "Error: Missing parameters for 'modify'"
        return 1
    }

    local bucketsz=$((rate / 250))

    tc qdisc change dev "$ifname" root handle 1:0 netem delay "${delay}ms" "${jitter}ms" limit "$delayLimit"
    tc qdisc change dev "$ifname" parent 1:1 handle 10:0 tbf rate "${rate}bit" burst "${bucketsz}b" limit "${queuesz}b" mtu 1500
}

# Main logic
case "$1" in
    add)
        echo "Creating a TC rule"
        echo "Params: $2 $3 $4 $5 $6 $7"
        load "$2" "$3" "$4" "$5" "$6" "$7"
        ;;
    auto)
        echo "Automatically creating TC rules for handover testing (ignore params)"
        load veth1 75 10000 $((200 * 1000000)) $((64 * 1024)) 5
        load veth2 33 10000 $((1400 * 1000000)) $((1024 * 1024)) 3
        ;;
    mod)
        echo "Modifying TC rules"
        echo "Params: $2 $3 $4 $5 $6 $7"
        modify "$2" "$3" "$4" "$5" "$6" "$7"
        ;;
    test)
        echo "Adding one TC for quick testing"
        load veth0 75 10000 $((200 * 1000000)) $((64 * 1024)) 5
        ;;
    *)
        echo "Usage: $0 {add|auto|mod} [ifname delay delayLimit rate queuesz jitter]"
        exit 1
        ;;
esac
