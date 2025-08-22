import io
import numpy as np
import pandas as pd
import json
import re

# mpl params reference
# import matplotlib.pyplot as plt
# import matplotlib as mpl
# textsize = 24
# params = {
#     "axes.labelsize": textsize,
#     "font.size": textsize,
#     "legend.fontsize": textsize,
#     "legend.handlelength": 1.5,
#     "legend.numpoints": 1,
#     "xtick.labelsize": textsize,
#     "ytick.labelsize": textsize,
#     "lines.linewidth": 2.5,
#     "text.usetex": False,
#     "figure.figsize": [12, 4],
# }
# mpl.rcParams.update(params)

# Compensensate for XCAL trace delay
defaultOffset = 2.4


# Set dataframe time range
def set_df_range(df, time_range, reset_ts=False):
    d = df[df["seconds"] > time_range[0]]
    d = d[d["seconds"] < time_range[1]]
    d = d.reset_index(drop=True)
    if reset_ts:
        d["seconds"] -= d.loc[0, "seconds"]
    return d


# Assuming single stream
def read_iperf(fname, sender=False):
    with open(fname, "r") as f:
        # sender/recv
        # if sender == True:
        #     text = "".join(f.readlines()[:-11])
        #     data = json.loads(text)
        # else:
        #     data = json.load(f)
        data = json.load(f)
        jitter = []
        seconds = []
        thput = []
        start_time = data["start"]["timestamp"]["timesecs"]
        # UDP
        if data["start"]["test_start"]["protocol"] == "UDP":
            loss = []
            for interval in data["intervals"]:
                seconds.append(round(interval["sum"]["start"], 1))
                jitter.append(round(interval["sum"]["jitter_ms"], 1))
                thput.append(round(interval["sum"]["bits_per_second"]))
                loss.append(interval["sum"]["lost_percent"])
            df = pd.DataFrame(
                {
                    "seconds": seconds,
                    "throughput": thput,
                    "jitter": jitter,
                    "loss_rate": loss,
                }
            )
        # TCP
        elif data["start"]["test_start"]["protocol"] == "TCP":
            # TCP sender
            if sender == True:
                snd_cwnd, rtt = [], []
                for interval in data["intervals"]:
                    sample = interval["streams"][0]
                    seconds.append(round(sample["start"], 1))
                    thput.append(round(sample["bits_per_second"]))
                    snd_cwnd.append(sample["snd_cwnd"])
                    rtt.append(sample["rtt"])
                df = pd.DataFrame(
                    {
                        "seconds": seconds,
                        "throughput": thput,
                        "snd_cwnd": snd_cwnd,
                        "rtt": rtt,
                    }
                )
            # TCP receiver
            else:
                for interval in data["intervals"]:
                    seconds.append(round(interval["sum"]["start"], 1))
                    thput.append(round(interval["sum"]["bits_per_second"]))
                df = pd.DataFrame({"seconds": seconds, "throughput": thput})
        return df, start_time


# XCAL NSA status log
def read_handover(fname, m, d, y=2023):
    for_pd = io.StringIO()
    with open(fname) as f:
        for line in f:
            new_line = re.sub(r",", "|", line.rstrip(), count=6)
            print(new_line, file=for_pd)
    for_pd.seek(0)
    df = pd.read_csv(
        for_pd,
        sep="|",
        names=["Time", "Chipset Time", "UE-NET", "Channel", "Tech", "Message", "Info"],
    )
    df["seconds"] = pd.to_datetime(df["Time"], format="%H:%M:%S.%f")
    df["seconds"] = df["seconds"].map(
        lambda x: x.replace(month=m, day=d, year=y)
        .tz_localize("America/Los_Angeles")
        .to_pydatetime()
        .timestamp()
    )
    return df


# ECDF
def ecdf(a):
    x, counts = np.unique(a, return_counts=True)
    cusum = np.cumsum(counts)
    return x, cusum / cusum[-1]
