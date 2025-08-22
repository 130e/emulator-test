import os
import re
import json
import csv
import pandas as pd
import argparse
import subprocess
from code import interact
from datetime import datetime


def parse_iperf3_log(file_path):
    """Parse iPerf3 JSON log file and extract time-throughput data."""
    with open(file_path, "r") as file:
        data = json.load(file)

    # Extract time and throughput data from intervals
    time_intervals = []
    throughputs = []

    for interval in data["intervals"]:
        start_time = interval["sum"]["start"]
        end_time = interval["sum"]["end"]
        bits_per_second = interval["sum"]["bits_per_second"]

        # Use mid-point of interval for plotting
        time_intervals.append((start_time + end_time) / 2)
        throughputs.append(bits_per_second / 1e6)  # Convert to Mbps

    return time_intervals, throughputs


def filter_time_range_iperf(time_intervals, data, start_time, end_time):
    """Filter data to include only the specified time range."""
    filtered_time = []
    filtered_data = []

    for t, tp in zip(time_intervals, data):
        if start_time <= t <= end_time:
            filtered_time.append(t)
            filtered_data.append(tp)

    return filtered_time, filtered_data


def estimate_frame(df, frame_size):
    # Sort packesorted_df = df.sort_values(by=["seq", "time"])ts by sequence number and timestamp
    df = df.sort_values(by=["seq", "time"]).reset_index(drop=True)
    df = df.drop_duplicates(subset="seq", keep="first")
    accumulated_length = 0
    frame_completion_timestamps = []
    frame_number = 1
    # Iterate through packets to calculate frame completion
    prev_completion_time = 0
    for _, row in df.iterrows():
        accumulated_length += row["len"]
        if accumulated_length >= frame_size:
            # Frame is complete
            if row["time"] < prev_completion_time:
                adjusted_time = prev_completion_time
            else:
                adjusted_time = row["time"]
            prev_completion_time = adjusted_time
            frame_completion_timestamps.append(
                {
                    "frame": frame_number,
                    "completion_time": adjusted_time,
                    "completion_time_raw": row["time"],
                }
            )
            frame_number += 1
            accumulated_length -= frame_size  # Start the next frame with leftover bytes
    # Convert frame completion timestamps to a DataFrame
    completion_df = pd.DataFrame(frame_completion_timestamps)
    completion_df["interval"] = completion_df["completion_time"].diff()
    # completion_df["interval"] = completion_df["completion_time"].diff()
    return completion_df


# Filter
def filter_relative_time_range(raw_df, start_time, end_time):
    df = raw_df[(raw_df["time"] >= start_time) & (raw_df["time"] <= end_time)].copy()
    df = df.sort_values(by=["time"]).reset_index(drop=True)
    return df


# Read TCP packet data
def process_server_log(fname, target_port):
    df = None
    with open(fname, "r") as f:
        parsed_data = []
        text = f.read()
        pattern = r"packet,(\d+),(\d+),(\d+),(\d+)"
        matches = re.findall(pattern, text)
        for epoch, port, tcp_seq, tcp_ack in matches:
            if int(port) == target_port:
                parsed_data.append(
                    {
                        "epoch": float(epoch) / 1000,
                        "seq": int(tcp_seq),
                        "srcport": target_port,
                        "ack": int(tcp_ack),
                    }
                )
        df = pd.DataFrame(parsed_data)
        # NOTE: iperf3 will use two connection, choose the latter one
        # df = df[df.srcport == target_port]
        df["time"] = df["epoch"] - df.iloc[0]["epoch"]
    return df


def check_rollover(df):
    df = df.sort_values(by="time").reset_index(drop=True)
    df["seq_diff"] = df["seq"].diff()
    # Detect rollovers (large negative differences)
    # For TCP, the sequence number rolls over from 2^32-1 to 0
    rollover_threshold = -(2**31)  # Half the maximum range, to account for some noise
    rollover_indices = df.index[df["seq_diff"] < rollover_threshold].tolist()
    rollover_pt = []
    if len(rollover_indices) != 0:
        print("time, epoch, seq")
        for idx in rollover_indices:
            row = df.iloc[idx]
            print(row.time, row.epoch, row.seq)
            rollover_pt.append(row.seq)
    return rollover_pt


def calculate_transit(df_server, df_client):
    server_earliest = df_server.groupby("seq", as_index=False)["epoch"].min()
    client_earliest = df_client.groupby("seq", as_index=False)["epoch"].min()
    merged = pd.merge(
        server_earliest, client_earliest, on="seq", suffixes=("_server", "_client")
    )
    merged["transit_time"] = merged["epoch_client"] - merged["epoch_server"]
    merged = merged.dropna()
    merged["time"] = merged["epoch_client"] - merged.iloc[0]["epoch_client"]
    return merged


# RFC 3550 jitter calculation
def calculate_jitter(df):
    jitter = 0
    error_cnt = 0
    results = []
    results.append(jitter)
    prev_transit_time = df.iloc[0]["transit_time"]
    for i, r in df.iloc[1:].iterrows():
        transit_time = r["transit_time"]
        if transit_time < 0:
            error_cnt += 1
            results.append(0)
            continue
        jitter += (abs(transit_time - prev_transit_time) - jitter) / 16
        results.append(jitter)
        prev_transit_time = transit_time
    if error_cnt != 0:
        print(f"Error: {error_cnt} packets out of order and cannot be sorted")
    return df.assign(jitter=results)


# Parse BBR ss line
def parse_bbr_info(bbr_str):
    """Parse the BBR information string into a dictionary."""
    # Extract content between parentheses
    bbr_match = re.search(r"\((.*?)\)", bbr_str)
    if not bbr_match:
        return {}

    bbr_params = {}
    # Split by comma and parse each parameter
    for param in bbr_match.group(1).split(","):
        if ":" not in param:
            continue
        key, value = param.split(":")
        # Remove 'bbr' prefix if present
        key = key.replace("bbr", "").strip()
        # Convert values to numeric where possible
        if "Mbps" in value:
            value = float(value.replace("Mbps", ""))
        elif value.replace(".", "").isdigit():
            value = float(value)
        bbr_params[key] = value
    return bbr_params


def parse_ss_line(line):
    # Extract timestamp
    time_match = re.search(r"time:(\d+)", line)
    if not time_match:
        return None
    timestamp = int(time_match.group(1))
    # Create a dictionary to store all metrics
    metrics = {
        "epoch": (timestamp / 1e9),  # nano to sec
    }
    # Handle BBR information separately first
    bbr_match = re.search(r"bbr:\((.*?)\)", line)
    if bbr_match:
        bbr_info = parse_bbr_info(bbr_match.group(0))
        metrics["bbr"] = bbr_info
        # Remove the BBR part from the line to avoid parsing conflicts
        line = line.replace(bbr_match.group(0), "")
    # Extract remaining key-value pairs
    pairs = re.findall(r"(\w+):([^ ]+)", line)
    for key, value in pairs:
        try:
            # Convert numeric values
            if value.replace(".", "").isdigit():
                value = float(value)
            # Handle percentage values
            elif "%" in value:
                value = float(value.replace("%", ""))
            # Handle Mbps values
            elif "Mbps" in value:
                value = float(value.replace("Mbps", ""))
        except ValueError:
            # If conversion fails, keep the original string value
            pass
        metrics[key] = value
    return metrics


def parse_ss(ss_log):
    df = pd.DataFrame()
    parsed_data = []
    try:
        with open(ss_log, "r") as f:
            for line_number, line in enumerate(f, 1):
                try:
                    parsed_line = parse_ss_line(line.strip())
                    if parsed_line:
                        parsed_data.append(parsed_line)
                except Exception as e:
                    print(f"Warning: Error parsing line {line_number}: {e}")
                    print(f"Line content: {line.strip()}")
                    break
    except FileNotFoundError:
        print(f"Error: Log file '{ss_log}' not found")
    except Exception as e:
        print(f"Error parsing file: {e}")

    # Flatten BBR metrics for CSV output
    flattened_data = []
    for entry in parsed_data:
        flat_entry = entry.copy()
        if "bbr" in flat_entry:
            bbr_data = flat_entry.pop("bbr")
            for k, v in bbr_data.items():
                flat_entry[f"bbr_{k}"] = v
        flattened_data.append(flat_entry)

    df = pd.DataFrame(flattened_data)
    df.time = df.epoch - df.epoch.min()

    # # Get all unique keys for CSV headers
    # headers = set()
    # for entry in flattened_data:
    #     headers.update(entry.keys())

    # try:
    #     with open(output_file, "w", newline="") as f:
    #         writer = csv.DictWriter(f, fieldnames=sorted(headers))
    #         writer.writeheader()
    #         writer.writerows(flattened_data)
    # except Exception as e:
    #     print(f"Error saving CSV: {e}")
    #     return False
    # return True

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse logs")
    parser.add_argument("--prefix")
    parser.add_argument("--nocap", action="store_true")
    parser.add_argument("-i", "--iperf_log")
    parser.add_argument("--client_pcap")
    parser.add_argument("-c", "--client_packets")
    parser.add_argument("-s", "--server_packets")
    parser.add_argument("--ss_log")
    parser.add_argument("-b", "--begin", type=float)
    parser.add_argument("-e", "--end", type=float)

    args = parser.parse_args()

    # Data range
    begin_time, end_time = args.begin, args.end
    if begin_time == None:
        begin_time = 0
    if end_time == None:
        end_time = 1200

    # Defaults
    root_dir = "output"
    if args.prefix != None:
        prefix = args.prefix

        fname = os.path.join(root_dir, f"{prefix}-iperf-client.json")
        if os.path.exists(fname):
            args.iperf_log = fname

        # if not args.nocap:
        #     fname = os.path.join(root_dir, f"{prefix}-capture-client.pcap")
        #     if os.path.exists(fname):
        #         args.client_pcap = fname
        # else:
        #     fname = os.path.join(root_dir, f"{prefix}-packet-client.csv")
        #     if os.path.exists(fname):
        #         args.client_packets = fname

        # fname = os.path.join(root_dir, f"{prefix}-capture-server.log")
        # if os.path.exists(fname):
        #     args.server_packets = fname

        # TODO: handle all TCP variants
        # fname = os.path.join(root_dir, f"{prefix}-ss-server.log")
        # if os.path.exists(fname):
        #     args.ss_log = fname
    else:
        prefix = "manual"

    # iPerf3 result
    if args.iperf_log != None:
        iperf_log = args.iperf_log
        print("Parsing iperf log")
        output_file = os.path.join(root_dir, f"{prefix}-iperf-throughput.csv")
        time_intervals, throughputs = parse_iperf3_log(iperf_log)
        time_intervals, throughputs = filter_time_range_iperf(
            time_intervals, throughputs, begin_time, end_time
        )
        print("Average Throughput per 100ms:", sum(throughputs) / len(throughputs))
        with open(output_file, "w") as file:
            writer = csv.writer(file)
            writer.writerow(["time", "throughput"])
            for i in range(len(throughputs)):
                writer.writerow([time_intervals[i], throughputs[i]])
            print("Saved as", output_file)
        print()

    if args.client_pcap != None:
        pcap = args.client_pcap
        print("Running tshark")
        # Run tshark command
        cmd = [
            "tshark",
            "-r",
            pcap,
            "-Y",
            "tcp.stream == 1 && tcp.dstport == 5257",
            "-T",
            "fields",
            "-e",
            "frame.time_relative",
            "-e",
            "frame.time_epoch",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.seq_raw",
            "-e",
            "tcp.ack_raw",
            "-e",
            "tcp.len",
            "-E",
            "separator=,",
        ]
        header = "time,epoch,src_ip,dst_ip,src_port,dst_port,seq,ack,len\n"
        output_file = os.path.join(root_dir, f"{prefix}-packet-client.csv")
        # Run the command and write the output to a file
        with open(output_file, "w") as f:
            f.write(header)

        with open(output_file, "a") as f:
            completed_proc = subprocess.run(cmd, stdout=f, check=True)
            if completed_proc.returncode == 0:
                args.client_packets = output_file
                print(f"> Output {output_file}")
        print()

    if args.server_packets != None and args.client_packets != None:
        print("Parsing packet metrics")
        client_packets = args.client_packets
        server_packets = args.server_packets

        df_client = pd.read_csv(client_packets)
        df_client = filter_relative_time_range(df_client, begin_time, end_time)

        # Check if we have TCP sequence number rollover
        # Checking one side should be enough
        print("Checking TCP sequence number roll over")
        rollover_pt = check_rollover(df_client)
        if len(rollover_pt) != 0:
            print("Error: TCP SEQ rollover happpening!")
            exit()
        else:
            print("> all good!")

        target_port = df_client.src_port.unique()[0]
        df_server = process_server_log(server_packets, target_port)
        df_server = filter_relative_time_range(df_server, begin_time, end_time)

        # Match packets and calculate transit time
        print("Matching packets")
        output_file = os.path.join(root_dir, f"{prefix}-transit.csv")
        df_matched = calculate_transit(df_server, df_client)
        df_matched.to_csv(output_file, index=False)

        # Calculate jitter
        print("Calculating jitter")
        output_file = os.path.join(root_dir, f"{prefix}-jitter.csv")
        df_jitter = calculate_jitter(df_matched)
        df_jitter.to_csv(output_file, index=False)

        # Estimate Frames
        # print("Estimating frames")
        # frame_size = 666667  # bytes (for a 4K video frame at 20 Mbps, 30 fps)
        # output_file = os.path.join(root_dir, f"{prefix}-frames.json")
        # df_frame = estimate_frame(df_client, frame_size)
        # df_frame.to_csv(output_file, index=False)
        print()

    if args.ss_log != None:
        ss_log = args.ss_log
        if "bbr" in ss_log:
            print("Parsing ss log for bbr")
            df_ss = parse_ss(ss_log)
            df_ss = filter_relative_time_range(df_ss, begin_time, end_time)
            output_file = os.path.join(root_dir, f"{prefix}-ss-server.csv")
            df_ss.to_csv(output_file, index=False)
        print()
