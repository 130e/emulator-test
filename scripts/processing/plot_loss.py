import numpy as np
import pandas as pd

# mpl params reference
import matplotlib.pyplot as plt
import matplotlib as mpl

textsize = 24
params = {
    "axes.labelsize": textsize,
    "font.size": textsize,
    "legend.fontsize": textsize,
    "legend.handlelength": 1.5,
    "legend.numpoints": 1,
    "xtick.labelsize": textsize,
    "ytick.labelsize": textsize,
    "lines.linewidth": 2.5,
    "text.usetex": False,
    "figure.figsize": [12, 4],
}
mpl.rcParams.update(params)

# For each variant, how many losses mitigated?
algos = ["CUBIC", "Reno", "Highspeed", "BIC", "H-TCP"]
# Define line styles, colors, and plot parameters
line_styles = ["solid", "dotted", "dashed", "dashdot", (0, (3, 5, 1, 5, 1, 5))]
colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]
cdfs = []

# [666, 187, 209, 187] = 1249
total_hos = 1249

# CUBIC
# 38
ones = 0.018
twos = 0.006
zeros = 0.973
more = 1 - ones - twos - zeros
d = [
    round(total_hos * zeros),
    round(total_hos * ones),
    round(total_hos * twos),
    round(total_hos * more),
]
cumulative_frequencies = np.cumsum(d)
total_tests = sum(d)
cubic_cdf = cumulative_frequencies / total_tests
cdfs.append(cubic_cdf)

# Reno
ones = 0.011
twos = 0.008
zeros = 0.98
more = 1 - ones - twos - zeros
d = [
    round(total_hos * zeros),
    round(total_hos * ones),
    round(total_hos * twos),
    round(total_hos * more),
]
cumulative_frequencies = np.cumsum(d)
total_tests = sum(d)
reno_cdf = cumulative_frequencies / total_tests
cdfs.append(reno_cdf)

# HS
ones = 0.025
twos = 0.01
zeros = 0.96
more = 1 - ones - twos - zeros
d = [
    round(total_hos * zeros),
    round(total_hos * ones),
    round(total_hos * twos),
    round(total_hos * more),
]
cumulative_frequencies = np.cumsum(d)
total_tests = sum(d)
reno_cdf = cumulative_frequencies / total_tests
cdfs.append(reno_cdf)

# BIC
ones = 0.023
twos = 0.03
zeros = 0.94
more = 1 - ones - twos - zeros
d = [
    round(total_hos * zeros),
    round(total_hos * ones),
    round(total_hos * twos),
    round(total_hos * more),
]
cumulative_frequencies = np.cumsum(d)
total_tests = sum(d)
reno_cdf = cumulative_frequencies / total_tests
cdfs.append(reno_cdf)

# HTCP
ones = 0.02
twos = 0.005
zeros = 0.97
more = 1 - ones - twos - zeros
d = [
    round(total_hos * zeros),
    round(total_hos * ones),
    round(total_hos * twos),
    round(total_hos * more),
]
cumulative_frequencies = np.cumsum(d)
total_tests = sum(d)
reno_cdf = cumulative_frequencies / total_tests
cdfs.append(reno_cdf)

for i in range(len(cdfs)):
    plt.plot(range(len(d)), cdfs[i], color=colors[i], linestyle=line_styles[i], label=algos[i])

plt.xticks(range(len(d)))
plt.legend(
    labels=algos,
    # loc="upper center",
    # ncol=5,
    borderpad=0,
    frameon=False,
)
plt.savefig(
    "./journal-eval-loss.pdf",
    format="pdf",
    dpi=600,
    # transparent=True,
    bbox_inches="tight",
    # pad_inches=0,
)
