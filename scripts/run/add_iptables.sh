#!/bin/sh
set -e

# Ensure the script is run as root
[ "$(id -u)" -ne 0 ] && echo "Error: This script must be run as root" && exit 1

# Define the network interface and ports
LOCAL_IP="10.0.0.1"
TARGET_IP="10.0.0.2"
PORT="5257"

# Function to set up iptables rules and routing configurations
setup() {
    echo "Setting up iptables and routing rules. Defaults: LOCAL_IP:${LOCAL_IP}, TARGET_IP:${TARGET_IP}, PORT:${PORT}"

    # Verify the local IP
    if ! ip a | grep -q "${LOCAL_IP}"; then
        echo "Error: This script is intended to be run on ${LOCAL_IP}."
        exit 1
    fi

    # 1. Configure iptables to use NFQUEUE
    echo "Configuring iptables rules for NFQUEUE..."
    iptables -A OUTPUT -p tcp --dport "${PORT}" -j NFQUEUE --queue-num 0
    iptables -A INPUT -p tcp --sport "${PORT}" -j NFQUEUE --queue-num 1

    # 2. Configure routing rules for multiple paths
    echo "Setting up routing tables..."
    ip route add "${TARGET_IP}" dev veth1 table 1 || echo "Route for veth1 already exists."
    ip route add "${TARGET_IP}" dev veth2 table 2 || echo "Route for veth2 already exists."

    # mark -> routing table
    ip rule add fwmark 1 lookup 1 || echo "Rule for fwmark 1 already exists."
    ip rule add fwmark 2 lookup 2 || echo "Rule for fwmark 2 already exists."

    echo "Configuration complete."
}

# Function to clean up iptables rules and routing configurations
cleanup() {
    echo "Cleaning up iptables rules and routing configurations..."

    # Remove iptables rules
    iptables -D OUTPUT -p tcp --dport "${PORT}" -j NFQUEUE --queue-num 0 2>/dev/null || echo "No OUTPUT NFQUEUE rule found."
    iptables -D INPUT -p tcp --sport "${PORT}" -j NFQUEUE --queue-num 1 2>/dev/null || echo "No INPUT NFQUEUE rule found."

    # Remove routes
    ip route del "${TARGET_IP}" dev veth1 table 1 2>/dev/null || echo "No route for veth1 found."
    ip route del "${TARGET_IP}" dev veth2 table 2 2>/dev/null || echo "No route for veth2 found."

    # Remove routing rules
    ip rule del fwmark 1 lookup 1 2>/dev/null || echo "No fwmark 1 rule found."
    ip rule del fwmark 2 lookup 2 2>/dev/null || echo "No fwmark 2 rule found."

    echo "Clean-up complete."
}

# Main logic to handle setup and cleanup
case "$1" in
    setup)
        setup
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {setup|cleanup}"
        exit 1
        ;;
esac