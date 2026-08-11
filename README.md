# 5G Handover Emulator

Tested on Arch 6.5/Ubuntu 22.04/Debian 12, also Android 11 (instruction WIP).

## Installation

This section walks through compiling a statically linked binary `emulator`, using locally compiled dependency `libnetfilter_queue`.

Alternatively, install from package manager and compiled a dynamically linked binary instead. In that case adjust `CMakeList.txt` accordingly.

### Build Dependencies 

#### 1. Install Compiler Tools

```bash
# Examples
# Arch
sudo pacman -S base-devel cmake
# Ubuntu
sudo apt install build-essential cmake
```

#### 2. Get Source

Visit [netfilter project website](https://netfilter.org) and download the source files. We are using libnfnetlink-1.0.2 and libnetfilter_queue-1.0.5.

```bash
# Get the source
mkdir -p dep/
cd dep/
# wget ....
tar -xjf libnfnetlink-1.0.2.tar.bz2
# ...

# Compile and Install netlink first
cd libnfnetlink-1.0.2
./configure --prefix=$(pwd)/../ --enable-static --disable-shared
make && make install

# Do the same for libnetfilter_queue
cd ../libnetfilter_queue-1.0.5
PKG_CONFIG_PATH=$(pwd)/../lib/pkgconfig ./configure --prefix=$(pwd)/../ --enable-static --disable-shared
make && make install
```

Now both libraries are installed in the `./lib` directory.

### Build Project

Run CMake to configure the build process:

```bash
cmake -B build .
cd build && make
# Test run. It should complain that no input trace is provided
./emulator
```

The binary is `build/emulator`.

### Emulation Example

In this example, we will create two network namespace, and then create 3 network interface between them.

#### 1. Setup network namespace

Ensure the emulation host has required capability (iptables netfilterqueue, tc, tbf, netem, etc.)

```bash
# Run setup for once
cd scripts/run/
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

## Trace format

The replay trace is a csv, one event per line:

```csv
time_ms,EVENT_TYPE,params...
```

`time_ms` is relative to the start of the emulation. The scheduler sorts events stably, so events sharing a timestamp fire in the order they appear in the file. Fields are split on `,` alone (no spaces), and an unrecognized `EVENT_TYPE` only logs an error and skips the line.

Two conventions run through every event:

- **`queue_num`** is the NFQUEUE number from the iptables rules. With
  `add_iptables.sh`, queue 0 is egress (`OUTPUT`) and queue 1 is ingress
  (`INPUT`).
- **`mark`** is the fwmark written into each packet's verdict. `ip rule fwmark N lookup N` turns it into a route, so mark 1 sends traffic over `veth1` and mark 2 over `veth2`. This is how a handover actually moves the flow.

| Event            | Purpose                                  |
|------------------|------------------------------------------|
| `INIT`           | open/close a queue                       |
| `CMD`            | run a shell command                      |
| `HO`             | emulate a handover                       |
| `SOL_INIT_SCHED` | arm the receive-window controller        |
| `SOL_HANDLEDUP`  | toggle duplicate-ACK suppression         |
| `SOL_HO`         | handover with the countermeasure applied |
| `SOL_HANDLERW`   | recognized but not implemented           |

### `INIT`

```csv
time_ms,INIT,queue_num,mark,end_ms
```

Opens the queue and starts consuming it at `time_ms`, tears it down at `end_ms`.
The initial fwmark is applied when `mark > 0`. Every queue used by later events needs one of these first, and the run lasts until the last scheduled event has fired. So this `end_ms` sets the emulation duration.

```csv
0,INIT,0,1,50000
0,INIT,1,1,50000
```

### `CMD`

```csv
time_ms,CMD,command
```

Handed to `system()`. It runs on the scheduler thread and blocks it until it returns, so append `&` for anything long-running (e.g. starting the iperf3 client). The command cannot contain a comma.

```csv
1000,CMD,iperf3 -c 10.0.0.2 -p 5257 -t 30 &
```

### `HO`

```csv
time_ms,HO,queue_num,new_mark,gap_ms,reord_cnt,reord_offset,loss
```

Expands into several scheduler events that together emulate one handover:

- `time_ms` : stop draining the queue. Packets accumulate in the kernel (up to `NFQ_QUEUE_SIZE`) instead of being verdicted; this is the radio gap.
- `time_ms` : set the fwmark to `new_mark`, moving the flow to the other link.
- `time_ms + gap_ms` : resume draining. The backlog flushes as a burst.
- `loss` : drop that many packets once the queue resumes.
- `reord_cnt` / `reord_offset` : hold `reord_cnt` packets without a verdict, let the next `reord_offset` packets through, then release the held ones in reverse order. Capped at `WORKER_MAX_REORDER_COUNT` (1000).

Note: while `reord_cnt > 0`, the parser currently overrides the `loss` field with `reord_cnt + 10` (`src/event.c`), so the value in the trace is ignored for reordering handovers.

```csv
9000,HO,0,1,30,1,10,0
```

### `SOL_INIT_SCHED`

```csv
time_ms,SOL_INIT_SCHED,queue_num,enable_rw,sample_interval,threshold,pace,start_time,mark1,hist_rw1,rtt1,mark2,hist_rw2,rtt2
```

Configures the receive-window controller and links it to a queue's worker.
Should point at the **ingress** queue: it rewrites the window field of packets arriving from the peer, which is what throttles the sender (equivalent to patching at the client egress).

- `enable_rw` : whether the worker actually rewrites `tcph->window`. else, dry-run.
- `sample_interval` : sampling period in ms used while burst estimating. Passive adaptation samples at the current link's `rtt` instead.
- `threshold`, `pace` : integer percentages, divided by 100. Utilization above `threshold` grows the window by `pace`; below 0.7 it shrinks by `pace/4`.
- `start_time` : when the periodic sampler first fires, in ms.
- `markN,hist_rwN,rttN` : per-link heuristic init values (twice for links 1 and 2) to bootstrap bandwidth estimator. `hist_rw` is the starting/remembered window and `rtt` the link RTT in ms. The controller starts on link 1.

```csv
0,SOL_INIT_SCHED,1,0,30,90,2,1500,1,2000,82,2,4000,46
```

### `SOL_HANDLEDUP`

```csv
time_ms,SOL_HANDLEDUP,queue_num,enable
```

Turns duplicate-ACK suppression on (`1`) or off (`0`) for that queue. An ACK is dropped when its ack number repeats the previous one and it carries no payload.

### `SOL_HO`

```csv
time_ms,SOL_HO,queue_num,mark,enable_freeze,freeze_ms,enable_dedup,smooth_ms,burst_duration,enable_adapt
```

The receiver-side counterpart to `HO`: it neither stops the queue nor damages packets, it retunes the window controller across a handover. `mark` selects the link to switch to. The current window is saved as the old link's `hist_rw` and the new link's remembered value is restored.

The remaining fields form a sequence of phases:

- `time_ms` : if `enable_freeze`, clamp the advertised window for `freeze_ms`
  (the "zero window until RACH" trick). The clamp value is taken from the `mark`
  field and floored at 10, so in practice it is always 10.
- `time_ms + freeze_ms` : if `enable_dedup`, start suppressing duplicate ACKs for
  `smooth_ms`; if `burst_duration > 0`, start burst estimation for that long.
- `time_ms + freeze_ms + burst_duration` : if `enable_adapt`, hand over to
  passive adaptation.
