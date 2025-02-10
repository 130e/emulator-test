import json
import csv
import pandas as pd
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

def filter_time_range(time_intervals, data, start_time, end_time):
    """Filter data to include only the specified time range."""
    filtered_time = []
    filtered_data = []

    for t, tp in zip(time_intervals, data):
        if start_time <= t <= end_time:
            filtered_time.append(t)
            filtered_data.append(tp)

    return filtered_time, filtered_data

# Read TCP packet data
def estimate_frame(fname, outputfname, start_time=0, end_time=90):
    raw_df = pd.read_csv(fname, names=["time", "src_ip", "dst_ip", "seq", "ack", "len"])
    df = raw_df[(raw_df["time"] >= start_time) & (raw_df["time"] <= end_time)].copy()

    # Sort packesorted_df = df.sort_values(by=["seq", "time"])ts by sequence number and timestamp
    df = df.sort_values(by=["seq", "time"]).reset_index(drop=True)
    df = df.drop_duplicates(subset="seq", keep="first")

    # code.interact(local=locals())

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


if __name__ == "__main__":
    start_time,end_time = 0,90
    
    # iPerf3
    iperf_log = "../../output/client-iperf3-1-bbr.log"
    iperf_output = "./data_tp.csv"
    time_intervals, throughputs = parse_iperf3_log(iperf_log)
    time_intervals, throughputs = filter_time_range(time_intervals, throughputs, start_time, end_time)
    with open(iperf_output, "w") as file:
        writer = csv.writer(file)
        writer.writerow(["time", "throughput"])
        for i in range(len(throughputs)):
            writer.writerow([time_intervals[i], throughputs[i]])
    print("Iperf3 processing done")

    # Frame
    # tshark commands are needed to first
    # 92.398 sequence roll over
    # Parameters
    FRAME_SIZE = 666667  # bytes (for a 4K video frame at 20 Mbps, 30 fps)
    pcap_log = "./client_pkt.csv"
    output_file = "frame_timestamps.csv"
    estimate_frame(pcap_log, output_file, start_time, end_time)
    print("Frame processing done")
