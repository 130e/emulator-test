# 5G Handover Emulator

Tested on Arch 6.5/Ubuntu 22.04/Debian 12, also Android 11(instruction WIP).

## Installation

Following instructions describe how to compile a statically linked binary `emulator`. The dependencies `libnetfilter_queue` will be compiled locally.

Alternatively, you can install the required `libnetfilter_queue` through other methods (distro packages) and compiled a dynamically linked binary instead. In this case you need to ajust the CMakeList.txt accordingly.

### Build Dependencies 

1. Install tools

Tools like gcc, cmake, make are needed. Install them for your environment.

```bash
# Examples
# Arch
sudo pacman -S base-devel cmake
# Ubuntu
sudo apt install build-essential cmake
```

2. Get Source

Visit [netfilter project website](https://netfilter.org) and download the source files. We are using libnfnetlink-1.0.2 and libnetfilter_queue-1.0.5.

```bash
# Extract the Libraries
tar -xjf libnfnetlink-1.0.2.tar.bz2
tar -xjf libnetfilter_queue-1.0.5.tar.bz2
# Compile and Install netlink first
cd libnfnetlink-1.0.2
./configure --prefix=$(pwd)/../lib --enable-static --disable-shared
make
make install
cd ..
# Same for libnetfilter_queue
cd libnetfilter_queue-1.0.5
./configure --prefix=$(pwd)/../lib --enable-static --disable-shared
make
make install
cd ..
```

At this point, both libraries are installed in the `./lib` directory.

### Build Project

Run CMake to configure the build process:
```bash
cmake -B build .
cd build
make
# Test run
./emulator
# It should complain that no input trace is provided
```
The binary is `build/emulator`.

### Using emulator with virtual network

We will create two network namespace, acting as two hosts; then create 3 network interface between them.

1. Setup network namespace

Get 130e/script-pool and check the host has required capability (iptables netfilterqueue, tc, tbf, netem, etc.)

```bash
# Run setup for once
cd script-pool/emulator/
# create two ns and three interfaces
# test_a -veth0- test_b
#        -veth1-
#        -veth2-
sudo ./netns.sh create test a b 3
# Enter ns test_a
sudo ./netns.sh exec test a bash
# Now you're in the root shell of the namespace!
```

2. Add iptables

You only need to run these **once** in your test_a (sender) environment.

```bash
# Must run in test_a ns
# Because script currently assume interface IP is 10.0.0.1

# Add iptables rules
./add_iptables.sh cleanup
./add_iptables.sh setup
# Add default tc rules
./load-tc-rules.sh auto
```

3. Run experiments

Go back to the emulator folder. We will run a debug trace to test the emulator.
```bash
# Host B (ns 10.0.0.2)
# listening for one iperf3 connection
iperf3 -s -1
# Host A (ns 10.0.0.1)
# Start the emulator; the iperf3 command is included in the trace.csv
# It connects to 10.0.0.2 and starts sending
cd emulator-test/build/
./emulator test_name ../input/trace-debug.csv
```

## Note

Trace input format
```
Handover
queue_num new_mark gap reord_cnt reord_offset loss
```