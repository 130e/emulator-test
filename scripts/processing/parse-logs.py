import os
import re
import json
import csv
import pandas as pd
import argparse
import code

def parse_iperf3_log(file_path):
    """Parse iPerf3 JSON log file and extract time-throughput data."""
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Extract time and throughput data from intervals
    time_intervals = []
    throughputs = []

    for interval in data['intervals']:
        start_time = interval['sum']['start']
        end_time = interval['sum']['end']
        bits_per_second = interval['sum']['bits_per_second']

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


def estimate_frame(df, outputfname, start_time=0, end_time=90):
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
        if accumulated_length >= FRAME_SIZE:
            # Frame is complete
            if row["time"] < prev_completion_time:
                adjusted_time = prev_completion_time
            else:
                adjusted_time = row["time"]
            prev_completion_time = adjusted_time

            frame_completion_timestamps.append({"frame": frame_number, "completion_time": adjusted_time, "completion_time_raw": row["time"]})
            frame_number += 1
            accumulated_length -= FRAME_SIZE  # Start the next frame with leftover bytes
    
    # Convert frame completion timestamps to a DataFrame
    completion_df = pd.DataFrame(frame_completion_timestamps)
    completion_df["interval"] = completion_df["completion_time"].diff()

    # completion_df["interval"] = completion_df["completion_time"].diff()
    
    # Save the frame completion timestamps to a CSV file
    completion_df.to_csv(outputfname, index=False)

# Filter
def filter_relative_time_range(raw_df, start_time, end_time):
    df = raw_df[(raw_df["time"] >= start_time) & (raw_df["time"] <= end_time)].copy()
    df = df.sort_values(by=["time"]).reset_index(drop=True)
    return df

# Read TCP packet data
def process_pkt_log(fname, srcport):
    df = None
    with open(fname, "r") as f:
        parsed_data = []
        text = f.read()
        pattern = r'packet,(\d+),(\d+),(\d+),(\d+)'
        matches = re.findall(pattern, text)
        for epoch, port, tcp_seq, tcp_ack in matches:
            if int(port) == srcport:
                parsed_data.append({"epoch":float(epoch)/1000, "seq":int(tcp_seq), "ack":int(tcp_ack)})
        df = pd.DataFrame(parsed_data)
        # An estimate of relative timestamp
        df["time"] = df["epoch"] - df.iloc[0]["epoch"]
    return df

def check_rollover(df):
    print("Checking rollover seq")
    df = df.sort_values(by='time').reset_index(drop=True)
    df['seq_diff'] = df['seq'].diff()
    # Detect rollovers (large negative differences)
    # For TCP, the sequence number rolls over from 2^32-1 to 0
    rollover_threshold = -(2**31)  # Half the maximum range, to account for some noise
    rollover_indices = df.index[df['seq_diff'] < rollover_threshold].tolist()
    for idx in rollover_indices:
        print(df.iloc[idx-1])
        print(df.iloc[idx])
        print(df.iloc[idx+1])
        print()
    return

def calculate_transit(df_server, df_client):
    server_earliest = df_server.groupby('seq', as_index=False)['epoch'].min()
    client_earliest = df_client.groupby('seq', as_index=False)['epoch'].min()
    merged = pd.merge(server_earliest, client_earliest, on='seq', suffixes=('_server', '_client'))
    merged['transit_time'] = merged['epoch_client'] - merged['epoch_server']
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
    for i,r in df.iloc[1:].iterrows():
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
    return df.assign(jitter = results)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse logs"
    )
    parser.add_argument("-i", "--iperf_log")
    parser.add_argument("-c", "--client_log")
    parser.add_argument("-s", "--server_log")
    parser.add_argument("-p", "--port", type=int)
    parser.add_argument("-b", "--start", type=int)
    parser.add_argument("-e", "--end", type=int)

    args = parser.parse_args()

    start_time, end_time = args.start, args.end
    if start_time == None:
        start_time = 0
    if end_time == None:
        end_time = 100

    if True:
        server_log = args.server_log
        server_port = args.port
        client_log = args.client_log
        basefname = os.path.basename(client_log).split(".")[0]
        output_file = f"{basefname}.jitter.csv"
        df_server = process_pkt_log(server_log, server_port)
        df_server = filter_relative_time_range(df_server, start_time, end_time)
        df_client = pd.read_csv(client_log, names=["time", "epoch","src_ip", "dst_ip", "seq", "ack", "len"])
        df_client = filter_relative_time_range(df_client, start_time, end_time)

        check_rollover(df_client)
        check_rollover(df_server)

    if False:
        # iPerf3
        # iperf_log = "../../output/client-iperf3-1-bbr.log"
        iperf_log = args.iperf_log
        basefname = os.path.basename(iperf_log).split(".")[0]
        iperf_output = f"{basefname}.tp.csv"
        time_intervals, throughputs = parse_iperf3_log(iperf_log)
        time_intervals, throughputs = filter_time_range_iperf(time_intervals, throughputs, start_time, end_time)
        with open(iperf_output, "w") as file:
            writer = csv.writer(file)
            writer.writerow(["time", "throughput"])
            for i in range(len(throughputs)):
                writer.writerow([time_intervals[i], throughputs[i]])
        print("Iperf3 processing done")

    if False:
        # Jitter
        print("Parsing jitter")
        server_log = args.server_log
        server_port = args.port
        client_log = args.client_log
        basefname = os.path.basename(client_log).split(".")[0]

        df_server = process_pkt_log(server_log, server_port)
        df_server = filter_relative_time_range(df_server, start_time, end_time)
        df_client = pd.read_csv(client_log, names=["time", "epoch","src_ip", "dst_ip", "seq", "ack", "len"])
        df_client = filter_relative_time_range(df_client, start_time, end_time)

        output_file = f"{basefname}.matched.csv"
        df_matched = calculate_transit(df_server, df_client)
        df_matched.to_csv(output_file, index=False)

        output_file = f"{basefname}.jitter.csv"
        df_jitter = calculate_jitter(df_matched)
        df_jitter.to_csv(output_file, index=False)

    if False:
        # Frame
        # tshark commands are needed to first
        # tshark -r trace-0-cubic.pcap -Y "tcp.stream == 1 && tcp.dstport == 5257" -T fields -e frame.time_relative -e frame.time_epoch -e ip.src -e ip.dst -e tcp.seq_raw -e tcp.ack_raw -e tcp.len -E separator=, > client-pkt-cubic-0.csv
        FRAME_SIZE = 666667  # bytes (for a 4K video frame at 20 Mbps, 30 fps)
        client_log = args.client_log
        basefname = os.path.basename(client_log).split(".")[0]
        output_file = f"{basefname}.frames.csv"
        estimate_frame(client_log, output_file, start_time, end_time)
        print("Frame processing done")
