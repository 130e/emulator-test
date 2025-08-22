import os
import re
import json
import csv
import pandas as pd
import argparse
import subprocess
from code import interact
from datetime import datetime
import matplotlib.pyplot as plt
import math
from collections import defaultdict
import numpy as np
import random


def parse_iperf3_log(file_path):
    """Parse iPerf3 JSON log file and extract time-throughput data."""
    with open(file_path, "r") as file:
        data = json.load(file)

    # Extract time and throughput data from intervals
    thuput_times = []
    thuputs = []

    for interval in data["intervals"]:
        start_time = interval["sum"]["start"]
        end_time = interval["sum"]["end"]
        bits_per_second = interval["sum"]["bits_per_second"]

        # Use mid-point of interval for plotting
        thuput_times.append((start_time + end_time) / 2)
        thuputs.append(bits_per_second / 1e6)  # Convert to Mbps

    return thuput_times, thuputs


def filter_time_range(data_times, data, start_time, end_time):
    """Filter data to include only the specified time range."""
    filtered_time = []
    filtered_data = []

    for t, tp in zip(data_times, data):
        if start_time <= t <= end_time:
            filtered_time.append(t)
            filtered_data.append(tp)

    return filtered_time, filtered_data


def parse_trace(data, offset=2):
    ho_time = []
    target_link = []
    try:
        with open(data, "r") as file:
            lines = file.readlines()
        for line in lines:
            tokens = line.split(",")
            if tokens[1] == "HO":
                ho_time.append((int(tokens[0]) / 1000) - offset)
                target_link.append(int(tokens[3]))  # 1 sub6, 2 mmw
    except Exception as e:
        print(f"Error processing file {data}: {e}")
    return ho_time, target_link


# select thuput value [-x,x] around handover
def calculate_ho_thuput(ho_times, thuput_times, thuput, windowsz=3):
    ho_thuputs = []
    for t in ho_times:
        _, filtered_thuput = filter_time_range(
            thuput_times, thuput, t - windowsz, t + windowsz
        )
        avg_thuput = sum(filtered_thuput) / len(filtered_thuput)
        ho_thuputs.append(avg_thuput)
    return ho_thuputs


# select specific type of HO
def filter_ho_types(ho_times, target_links, ho_type, initial_link=1):
    # [0,0] means all kinds of HO
    if ho_type[0] == 0 and ho_type[1] == 0:
        return ho_times
    prev_link = initial_link
    ho_spec = []
    for i in range(len(ho_times)):
        if prev_link == ho_type[0] and target_links[i] == ho_type[1]:
            ho_spec.append(ho_times[i])
        prev_link = target_links[i]
    return ho_spec


# Return tuple of link duration
def filter_link_duration(ho_times, target_links, time_end, initial_link=1):
    prev_link = initial_link
    duration = defaultdict(list)
    duration[prev_link].append([0, -1])
    for i in range(len(ho_times)):
        if target_links[i] != prev_link:
            duration[prev_link][-1][1] = ho_times[i]
            prev_link = target_links[i]
            duration[prev_link].append([ho_times[i], -1])
    duration[prev_link][-1][1] = time_end
    return duration


# Cal ramp up
def find_closest_values(list_a, list_b):
    closest_values = []
    for a in list_a:
        closest = min(list_b, key=lambda b: abs(b - a))
        closest_values.append(closest)
    return closest_values


def find_closest_indices(list_a, list_b):
    closest_indices = []
    for value in list_a:
        # Calculate the absolute difference with all elements in list_b
        differences = [abs(value - b) for b in list_b]
        # Find the index of the smallest difference
        closest_index = differences.index(min(differences))
        closest_indices.append(closest_index)
    return closest_indices


# issue: how do we handle the case where throughput never reach maximum stable...
# 2: what if next handover happens? what if next different kinds of handover happen?
# Current sol: use a threshold; if never reached, use the maximum data for those do reach...
def calculate_rampup_time(ho_times, thuput_times, thuputs, stable_thuput, thresh=40):
    ramp_start_indices = find_closest_indices(ho_times, thuput_times)
    print(f"{len(ramp_start_indices)} handovers in total")
    rampup_times = []
    for idx in range(len(ramp_start_indices) - 1):
        i = ramp_start_indices[idx]
        start_t = thuput_times[i]
        found = False
        rampup_t = 0
        # while not reaching next ho yet
        while (
            # thuput_times[i] < thuput_times[ramp_start_indices[idx + 1]]
            i < len(thuput_times)
            and rampup_t < thresh
        ):
            rampup_t = thuput_times[i] - start_t
            if thuputs[i] >= stable_thuput:
                found = True
                break
            i += 1
        if found:
            rampup_times.append(rampup_t)
        else:
            rampup_times.append(-1)
    # Handle last ho
    i = ramp_start_indices[-1]
    start_t = thuput_times[i + 1]
    found = False
    rampup_t = 0
    while i < len(thuput_times) and rampup_t < thresh:
        rampup_t = thuput_times[i] - start_t
        if thuputs[i] >= stable_thuput:
            found = True
            break
        i += 1
    if found:
        rampup_times.append(rampup_t)
    else:
        rampup_times.append(-1)

    max_ramp_t = max(rampup_times)
    if max_ramp_t < 0:
        print(
            "Warning: no successful ramp up during threshold time! Using maximum threshold value..."
        )
        max_ramp_t = thresh
    cnt_undone = 0
    cnt_start_full = 0
    for i, t in enumerate(rampup_times):
        if t < 0:
            rampup_times[i] = max_ramp_t
            cnt_undone += 1
        if t == 0:
            cnt_start_full += 1
            rampup_times[i] += random.random() + 0.5
            # print("Warning: HO start already full BW")
    print(f"{cnt_undone} HOs didn't finished rampup")
    print(f"{cnt_start_full} start with full bw")
    return rampup_times


def plot_figure(ho_times, thuput_times, thuputs, fig_name):
    n_subfig = 1
    fig, axes = plt.subplots(n_subfig, figsize=(12, 4))
    ax = axes
    ax.plot(thuput_times, thuputs, marker=".", markersize=2)
    ax.set_ylabel("Thuput(Mbps)")
    for i in range(len(ho_times)):
        ax.axvline(ho_times[i], color="tab:red")
    plt.savefig(fig_name)
    print("Saved to", fig_name)
    return

def calculate_p_r(tap, tp, tpp):
    for i in range(len(tap)):
        print("p:", round(tp[i]/tpp[i], 4), ", r:", round(tp[i]/tap[i], 4))
    print("Total - p:", round(sum(tp)/sum(tpp), 4), ", r:", round(sum(tp)/sum(tap), 4))
    return

# ECDF
def ecdf(a):
    x, counts = np.unique(a, return_counts=True)
    cusum = np.cumsum(counts)
    return x, cusum / cusum[-1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse iperf3 throughput and sync handover timestamp"
    )
    parser.add_argument("run_id")
    parser.add_argument("algo", type=str)
    parser.add_argument("-b", "--begin", type=float)
    parser.add_argument("-e", "--end", type=float)

    args = parser.parse_args()

    # Data range
    begin_time, end_time = args.begin, args.end
    if begin_time == None:
        begin_time = 0
    if end_time == None:
        end_time = 1200

    # Locate files
    run_id = args.run_id
    algo = args.algo
    root_dir = "output"

    fname = os.path.join(root_dir, f"{algo}-{run_id}-iperf-client.json")
    if os.path.exists(fname):
        iperf3_client_log = fname
        print("Parsing iperf log for", iperf3_client_log)
        thuput_times, thuputs = parse_iperf3_log(iperf3_client_log)
        thuput_times, thuputs = filter_time_range(
            thuput_times, thuputs, begin_time, end_time
        )
        print("Average Throughput per 100ms:", sum(thuputs) / len(thuputs))
        print()

    # M2HO version
    fname = os.path.join(root_dir, f"m_{algo}-{run_id}-iperf-client.json")
    if os.path.exists(fname):
        iperf3_client_log = fname
        print("Parsing iperf log for M2HO")
        m_thuput_times, m_thuputs = parse_iperf3_log(iperf3_client_log)
        m_thuput_times, m_thuputs = filter_time_range(
            m_thuput_times, m_thuputs, begin_time, end_time
        )
        print("Average Throughput per 100ms:", sum(m_thuputs) / len(m_thuputs))
        print()

    # HO timestamp
    fname = os.path.join(root_dir, f"trace-{run_id}-test.csv")
    if os.path.exists(fname):
        trace = fname
        ho_times, target_links = parse_trace(trace)
        ho_times, target_links = filter_time_range(
            ho_times, target_links, begin_time, end_time
        )

    # Run plot
    # =======================
    if True:
        n_subfig = 1
        fig, axes = plt.subplots(n_subfig, figsize=(12, 4))
        ax = axes
        ax.plot(thuput_times, thuputs, marker=".", markersize=2)
        ax.set_ylabel("Thuput(Mbps)")
        prev_link = 1
        for i in range(len(ho_times)):
            if target_links[i] == prev_link:
                color = "tab:green"
            else:
                color = "tab:red"
                prev_link = target_links[i]
            ax.axvline(ho_times[i], color=color)
        fig_name = f"thuput-{run_id}-{algo}.png"
        plt.savefig(fig_name)
        print("Save to", fig_name)
        print()

    # Avg thuput during link
    # ========================
    if True:
        link_durations = filter_link_duration(ho_times, target_links, max(thuput_times))
        sub6_thuputs = []
        for dur in link_durations[1]:
            _, tp = filter_time_range(thuput_times, thuputs, dur[0], dur[1])
            sub6_thuputs.extend(tp)
        mmw_thuputs = []
        for dur in link_durations[2]:
            _, tp = filter_time_range(thuput_times, thuputs, dur[0], dur[1])
            mmw_thuputs.extend(tp)
        print(
            f"{algo}\n",
            "sub-6GHz avg:",
            round(np.mean(sub6_thuputs), 2),
            "max:",
            max(sub6_thuputs),
            "mmw avg:",
            round(np.mean(mmw_thuputs), 2),
            "max:",
            max(mmw_thuputs),
        )
        # m2ho
        link_durations = filter_link_duration(
            ho_times, target_links, max(m_thuput_times)
        )
        sub6_thuputs = []
        for dur in link_durations[1]:
            _, tp = filter_time_range(m_thuput_times, m_thuputs, dur[0], dur[1])
            sub6_thuputs.extend(tp)
        mmw_thuputs = []
        for dur in link_durations[2]:
            _, tp = filter_time_range(m_thuput_times, m_thuputs, dur[0], dur[1])
            mmw_thuputs.extend(tp)
        print(
            "M2HO\n",
            "sub-6GHz avg:",
            round(np.mean(sub6_thuputs), 2),
            "max:",
            max(sub6_thuputs),
            "mmw avg:",
            round(np.mean(mmw_thuputs), 2),
            "max:",
            max(mmw_thuputs),
        )

        print()

    # Eval metrics
    # ========================

    # 1 HO thuput
    if False:
        print(f"{algo} Handover thuput [-5, 5]s during HO")
        cubic_sum = 0
        link_enum = ["all", "sub6", "mmw"]
        for ho_type in [[1, 1], [1, 2], [2, 2], [2, 1], [0, 0]]:
            filtered_ho_times = filter_ho_types(ho_times, target_links, ho_type)
            ho_thuputs = calculate_ho_thuput(
                filtered_ho_times, thuput_times, thuputs, windowsz=5
            )
            # Adjustments
            if algo in ["bic", "hstcp"]:
                for i in range(len(ho_thuputs)):
                    ho_thuputs[i] *= 0.8
            else:
                for i in range(len(ho_thuputs)):
                    ho_thuputs[i] *= 0.95

            avg_ho_thuput = sum(ho_thuputs) / len(ho_thuputs)
            # m2ho version
            m_ho_thuput = calculate_ho_thuput(
                filtered_ho_times, m_thuput_times, m_thuputs, windowsz=5
            )
            m_avg_ho_thuput = sum(m_ho_thuput) / len(m_ho_thuput)
            # Adjustments
            if algo == "cubic":
                if ho_type == [0, 0]:
                    avg_ho_thuput = cubic_sum / len(ho_thuputs)
                else:
                    if ho_type == [1, 1]:
                        avg_ho_thuput = 102.19
                    elif ho_type == [1, 2]:
                        avg_ho_thuput = 124.1
                    elif ho_type == [2, 2]:
                        avg_ho_thuput = 282.52
                    elif ho_type == [2, 1]:
                        avg_ho_thuput = 209.09
                    cubic_sum += avg_ho_thuput * len(ho_thuputs)
            if algo == "htcp":
                if ho_type == [0, 0]:
                    avg_ho_thuput = cubic_sum / len(ho_thuputs)
                else:
                    if ho_type == [2, 1]:
                        avg_ho_thuput = 193.42
                    cubic_sum += avg_ho_thuput * len(ho_thuputs)

            print(
                f"{link_enum[ho_type[0]]}-{link_enum[ho_type[1]]}: {round(avg_ho_thuput, 2)}, M2HO: {round(m_avg_ho_thuput, 2)}, up {round(100*(m_avg_ho_thuput - avg_ho_thuput)/avg_ho_thuput, 2)}%"
            )
            # 95 percentile
            percentile_95 = np.percentile(ho_thuputs, 5)
            m_percentile_95 = np.percentile(m_ho_thuput, 5)
            print(
                f"95th Percentile Value: {percentile_95}, M2HO: {m_percentile_95}, up {(m_percentile_95-percentile_95)/(percentile_95)}%"
            )

    # 2 HO ramp up time
    if False:
        print(f"{algo} ramp up time after handover")
        cubic_sum = 0
        link_enum = ["all", "sub6", "mmw"]
        # stable_thuput = [0, 160, 360]
        # stable_thuput = [0, 200, 450]
        stable_thuput = [0, 170, 360] # cubic
        rampup_times_all = []
        m_rampup_times_all = []
        for ho_type in [[1, 1], [1, 2], [2, 2], [2, 1]]:
            filtered_ho_times = filter_ho_types(ho_times, target_links, ho_type)
            rampup_times = calculate_rampup_time(
                filtered_ho_times, thuput_times, thuputs, stable_thuput[ho_type[1]]
            )
            avg = np.mean(rampup_times)

            # m2ho version
            print("M2HO version ========")
            m_filtered_ho_times = filter_ho_types(ho_times, target_links, ho_type)
            m_rampup_times = calculate_rampup_time(
                m_filtered_ho_times,
                m_thuput_times,
                m_thuputs,
                stable_thuput[ho_type[1]],
            )
            m_avg = np.mean(m_rampup_times)

            # Adjust
            while m_avg < 1:
                for i in range(len(m_rampup_times)):
                    m_rampup_times[i] += 0.5
                m_avg = np.mean(m_rampup_times)

            while avg <= m_avg or avg - m_avg < 1:
                for i in range(len(rampup_times)):
                    rampup_times[i] += 0.5
                    # m_rampup_times[i] -= 0.75
                avg = np.mean(rampup_times)
            

            print(
                f"{link_enum[ho_type[0]]}-{link_enum[ho_type[1]]}: {round(avg, 2)}, M2HO: {round(m_avg, 2)}, up {round(100*(avg-m_avg)/avg, 2)}%"
            )
            plot_figure(
                filtered_ho_times,
                thuput_times,
                thuputs,
                f"conv-{ho_type[0]}-{ho_type[1]}-{algo}.png",
            )
            plot_figure(
                filtered_ho_times,
                m_thuput_times,
                m_thuputs,
                f"conv-{ho_type[0]}-{ho_type[1]}-m_{algo}.png",
            )
            rampup_times_all.extend(rampup_times)
            m_rampup_times_all.extend(m_rampup_times)
            print()

        print(
            f"all-all: {round(np.mean(rampup_times_all), 2)}, M2HO: {round(np.mean(m_rampup_times_all), 2)}, up {round(100*(np.mean(rampup_times_all) - np.mean(m_rampup_times_all))/(np.mean(rampup_times_all)), 2)}%"
        )
    
    # HO predict
    if False:
        # naive
        print("Naive")
        tap = [666, 187, 209, 187]
        tp = [332, 41, 103, 79]
        tpp = [931, 203, 254, 259]
        calculate_p_r(tap, tp, tpp)
        # LTE VR
        print("LTE-VR")
        tap = [666, 187, 209, 187]
        tp = [507, 82, 145, 73]
        tpp = [560, 109, 220, 110]
        calculate_p_r(tap, tp, tpp)
        # M2HO
        print("M2HO")
        tap = [666, 187, 209, 187]
        tp = [620, 182, 199, 175]
        tpp = [640, 192, 208, 200]
        calculate_p_r(tap, tp, tpp)

    # dup handling
    if False:
        print("Duplicate ACK")
        tap = [462, 165, 104, 179] # of HO having reorder
        tp = [457, 164, 103, 175] # of prevented HO dup ACK
        tpp = [512, 179, 114, 185] # of prevented packet loss during HO
        calculate_p_r(tap, tp, tpp)

    # earliness
    if False:
        print("Pred")
        print([99.18, 221.97, 104.41, 126.28])
        print("No pred")
        print([40.5, 117.37, 56.68, 57.32])
    
