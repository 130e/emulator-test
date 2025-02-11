import argparse
import matplotlib.pyplot as plt
import pandas as pd
import code

def plot(logs_data, output_file=None):
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
    parser = argparse.ArgumentParser(
        description="Plot logs"
    )
    parser.add_argument("-n", "--name")
    parser.add_argument("-t", "--throughput")
    parser.add_argument("-j", "--jitter")
    parser.add_argument("-f", "--frames")
    # parser.add_argument("-s", "--start", type=int)
    # parser.add_argument("-e", "--end", type=int)

    args = parser.parse_args()

    n = 2
    fig, axes = plt.subplots(n)

    ax = axes[0]
    # iperf3
    iperf_output = args.throughput
    df_iperf = pd.read_csv(iperf_output)
    ax.plot(df_iperf.time, df_iperf.throughput)
    ax.set_ylabel("Thuput(Mbps)")

    # Jitter
    ax = axes[1]
    df_jitter = pd.read_csv(args.jitter)
    ax.plot(df_jitter.time, df_jitter.jitter)
    ax.set_ylabel("Jitter")

    # Frame completion time
    # ax = axes[1]
    # frame_output = args.frames
    # df_frame = pd.read_csv(frame_output)
    # df_frame = df_frame.sort_values(["completion_time"])
    # ax.plot(df_frame.completion_time, df_frame.interval)
    # ax.set_ylabel("frame_interval(s)")

#     ho_text = """7899,HO,0,2,199,1,26,0
# 13602,HO,0,2,33,4,4,0
# 33603,HO,0,2,11,0,0,0
# 36870,HO,0,2,24,0,0,0
# 40462,HO,0,1,11,4,1,0
# 41353,HO,0,1,62,5,1,0
# 43206,HO,0,1,49,0,0,0
# 44375,HO,0,1,41,2,1,0
# 50996,HO,0,1,12,1,62,0
# 60185,HO,0,1,21,1,62,0
# 61071,HO,0,1,49,0,0,0"""
#     lines = ho_text.split("\n")
#     prev_cell = "1"
    
#     for line in lines:
#         items = line.split(",")
#         ho = items[0]
#         cell = items[3]
#         ho = int(ho)/1000
#         ho -= 2
#         if cell != prev_cell:
#             color = "r"
#         else:
#             color = "b"
#         prev_cell = cell
#         ax.axvline(ho, color=color)

    plt.title(args.name)
    plt.savefig("Test.png")
