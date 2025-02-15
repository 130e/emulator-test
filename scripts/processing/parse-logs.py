import os
import re
import json
import csv
import pandas as pd
import argparse
import subprocess
import code


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
    # code.interact(local=locals())
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
    # code.interact(local=locals())
    return df.assign(jitter=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse logs")
    parser.add_argument("output_prefix")
    parser.add_argument("-i", "--iperf_log")
    parser.add_argument("--client_pcap")
    parser.add_argument("-c", "--client_capture")
    parser.add_argument("-s", "--server_capture")
    parser.add_argument("-b", "--begin", type=float)
    parser.add_argument("-e", "--end", type=float)

    args = parser.parse_args()

    # Data range
    begin_time, end_time = args.begin, args.end
    if begin_time == None:
        begin_time = 0
    if end_time == None:
        end_time = 1200

    # Filename handling
    # TODO: Dirty!
    output_prefix = f"output/{args.output_prefix}"

    if args.iperf_log != None:
        # iPerf3
        print("Parsing iperf log")
        iperf_log = args.iperf_log
        iperf_output = f"{output_prefix}-iperf-throughput.csv"
        time_intervals, throughputs = parse_iperf3_log(iperf_log)
        time_intervals, throughputs = filter_time_range_iperf(
            time_intervals, throughputs, begin_time, end_time
        )
        print("Average Throughput per 100ms:", sum(throughputs)/len(throughputs))
        with open(iperf_output, "w") as file:
            writer = csv.writer(file)
            writer.writerow(["time", "throughput"])
            for i in range(len(throughputs)):
                writer.writerow([time_intervals[i], throughputs[i]])
            print("Saved as", iperf_output)

    if args.client_pcap != None:
        print("Running tshark to convert pcap (assuming default iperf3 config)")
        client_pcap = args.client_pcap
        # Run tshark command
        cmd = [
            "tshark",
            "-r",
            client_pcap,
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
        output_file = f"{output_prefix}-packet-client.csv"
        # Run the command and write the output to a file
        with open(output_file, "w") as f:
            f.write(header)

        with open(output_file, "a") as f:
            completed_proc = subprocess.run(cmd, stdout=f, check=True)
            if completed_proc.returncode == 0:
                client_cap = output_file

    # Read from cmd if not from pcap
    if args.client_capture != None:
        client_cap = args.client_capture

    if args.server_capture != None and client_cap != None:
        print("Parsing packet metrics")

        df_client = pd.read_csv(client_cap)
        df_client = filter_relative_time_range(df_client, begin_time, end_time)

        # Check if we have TCP sequence number rollover
        # Checking one side should be enough
        print("Checking TCP sequence number roll over")
        rollover_pt = check_rollover(df_client)
        if len(rollover_pt) != 0:
            print("Error: TCP SEQ rollover happpening!")
            exit()

        target_port = df_client.src_port.unique()[0]
        server_cap = args.server_capture
        df_server = process_server_log(server_cap, target_port)
        df_server = filter_relative_time_range(df_server, begin_time, end_time)
        print("Server done")

        # Match packets and calculate transit time
        print("Matching packets")
        output_file = f"{output_prefix}-transit.csv"
        df_matched = calculate_transit(df_server, df_client)
        df_matched.to_csv(output_file, index=False)

        # Calculate jitter
        print("Calculating jitter")
        output_file = f"{output_prefix}-jitter.csv"
        df_jitter = calculate_jitter(df_matched)
        df_jitter.to_csv(output_file, index=False)

        # Estimate Frames
        print("Estimating frames")
        frame_size = 666667  # bytes (for a 4K video frame at 20 Mbps, 30 fps)
        output_file = f"{output_prefix}-frames.csv"
        df_frame = estimate_frame(df_client, frame_size)
        df_frame.to_csv(output_file, index=False)
