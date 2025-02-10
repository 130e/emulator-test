import json
import argparse
import matplotlib.pyplot as plt

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

def filter_time_range(time_intervals, throughputs, start_time, end_time):
    """Filter data to include only the specified time range."""
    filtered_time = []
    filtered_throughputs = []

    for t, tp in zip(time_intervals, throughputs):
        if start_time <= t <= end_time:
            filtered_time.append(t)
            filtered_throughputs.append(tp)

    return filtered_time, filtered_throughputs

def plot_throughput(logs_data, output_file=None):
    """Generate and save time-throughput figure for multiple logs."""
    plt.figure(figsize=(10, 6))

    for log_data in logs_data:
        label, time_intervals, throughputs = log_data
        plt.plot(time_intervals, throughputs, label=label)

    plt.title('Time vs Throughput')
    plt.xlabel('Time (s)')
    plt.ylabel('Throughput (Mbps)')
    plt.grid(True)
    plt.legend()

    if output_file:
        plt.savefig(output_file, format='pdf')
        print(f"Figure saved as {output_file}")
    else:
        plt.show()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Parse iPerf3 logs and generate a time-throughput plot.")
    parser.add_argument("input_files", nargs='+', help="Paths to the iPerf3 log files in JSON format.")
    parser.add_argument("--output", help="Path to save the output figure as a PDF file.", default=None)
    parser.add_argument("--start-time", type=float, help="Start time for the plot (in seconds).", default=None)
    parser.add_argument("--end-time", type=float, help="End time for the plot (in seconds).", default=None)

    args = parser.parse_args()

    logs_data = []

    # Parse each log and filter by time range if specified
    for i, input_file in enumerate(args.input_files):
        time_intervals, throughputs = parse_iperf3_log(input_file)

        if args.start_time is not None and args.end_time is not None:
            time_intervals, throughputs = filter_time_range(time_intervals, throughputs, args.start_time, args.end_time)

        logs_data.append((f"Log {i+1}", time_intervals, throughputs))

    # Plot the data
    plot_throughput(logs_data, args.output)
