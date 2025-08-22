import argparse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from code import interact


def plot(x, y):
    plt.plot(x, y, marker=".", markersize=1)
    plt.savefig("test.png")
    plt.clf()


# Filter
def filter_relative_time_range(raw_df, start_time, end_time):
    df = raw_df[(raw_df["time"] >= start_time) & (raw_df["time"] <= end_time)].copy()
    df = df.sort_values(by=["time"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot logs")
    parser.add_argument("-a", "--auto")
    parser.add_argument("-n", "--name")
    parser.add_argument("-t", "--throughput")
    parser.add_argument("-j", "--jitter")
    parser.add_argument("-f", "--frames")
    parser.add_argument("-s", "--ss")
    parser.add_argument("-b", "--begin", type=float)
    parser.add_argument("-e", "--end", type=float)

    args = parser.parse_args()

    # Defaults
    # Auto variable is the prefix for all file names
    root_dir = "output"
    n_subfig = 0
    if args.auto != None:
        auto = args.auto
        print(f"[auto] Parse files with {auto} prefix in {root_dir}")

        fname = os.path.join(root_dir, f"{auto}-iperf-throughput.csv")
        if os.path.exists(fname):
            args.throughput = fname

        fname = os.path.join(root_dir, f"{auto}-ss-server.csv")
        if os.path.exists(fname):
            args.ss = fname

        # fname = os.path.join(root_dir, f"{auto}-jitter.csv")
        # if os.path.exists(fname):
        #     args.jitter = fname

        # fname = os.path.join(root_dir, f"{auto}-frames.csv")
        # if os.path.exists(fname):
        #     frames = fname

    # Check figs to plot
    n_subfig = sum([1 for x in (args.throughput, args.jitter, args.ss) if x is not None])
    if n_subfig == 0:
        print("No input file specified(or detected)")
        exit(1)
    fig, axes = plt.subplots(n_subfig, figsize=(12, 4))
    fig_id = 0
    if n_subfig == 1:
        ax = axes
        axes = [ax]

    if args.name == None:
        args.name = "unspec"
    else:
        fig.suptitle(args.name)

    # Data range
    begin_time, end_time = args.begin, args.end
    if begin_time == None:
        begin_time = 0
    if end_time == None:
        end_time = 1200

    if args.throughput:
        ax = axes[fig_id]
        fig_id += 1
        # iperf3
        df_iperf = pd.read_csv(args.throughput)
        df_iperf = filter_relative_time_range(df_iperf, begin_time, end_time)
        ax.plot(df_iperf.time, df_iperf.throughput, marker=".", markersize=2)
        ax.set_ylabel("Thuput(Mbps)")
        avg_thuput = df_iperf.throughput.mean()
        print(f"Average throughput {avg_thuput}")

    # Jitter
    # if args.jitter:
    #     ax = axes[fig_id]
    #     fig_id += 1
    #     df_jitter = pd.read_csv(args.jitter)
    #     df_jitter = filter_relative_time_range(df_jitter, begin_time, end_time)
    #     ax.plot(df_jitter.time, df_jitter.jitter, marker=".", markersize=1)
    #     ax.set_ylabel("Jitter(s)")

    # Frame completion time
    # if args.frames:
    #     ax = axes[fig_id]
    #     fig_id += 1
    #     df_frame = pd.read_csv(frames)
    #     df_frame = df_frame.sort_values(["completion_time"])
    #     ax.plot(df_frame.completion_time, df_frame.interval, marker=".", markersize=1)
    #     ax.set_ylabel("frame_interval(s)")

    # TODO: Manually set what to plot
    if args.ss:
        ax = axes[fig_id]
        fig_id += 1
        df_ss = pd.read_csv(args.ss)
        df_ss = filter_relative_time_range(df_ss, begin_time, end_time)
        ax.plot(df_ss.time, df_ss.segs_out, marker=".", markersize=1)
        ax.set_ylabel("bbr minRTT")
        # print("SS: bbr_mrtt:", pd.unique(df_ss.bbr_mrtt))
        # interact(local=locals())

        # ax = axes[fig_id]
        # fig_id += 1
        # ax.plot(df_ss.time, df_ss.cwnd, marker=".", markersize=1)
        # ax.set_ylabel("bbr cwnd")


    #     ho_text = """7899,HO,0,2,199,1,26,0
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

    
    # Save the plot
    fig_name = f"test-{args.name}.png"
    print("Save to", fig_name)
    plt.savefig(fig_name)
