import pandas as pd
import matplotlib.pyplot as plt

# Step 1: Load Packet Arrival Times
arrival_times = []
with open("arrival_times.txt", "r") as f:
    for line in f:
        arrival_times.append(float(line.strip()))

# Step 2: Convert Arrival Times to Milliseconds
arrival_times_ms = [t * 1000 for t in arrival_times]

# Step 3: Calculate Inter-Arrival Times (IAT) in milliseconds
iat_ms = [0]  # First packet has no previous IAT
iat_ms.extend([(arrival_times[i] - arrival_times[i - 1]) * 1000 for i in range(1, len(arrival_times))])

# Step 4: Calculate Jitter (RFC 3550 Formula) in milliseconds
jitter_ms = [0]  # Initial jitter value
for i in range(1, len(iat_ms)):
    jitter_ms.append(jitter_ms[-1] + (abs(iat_ms[i] - iat_ms[i - 1]) - jitter_ms[-1]) / 16)

# Step 5: Save Results to CSV
output_file = "arrival_iat_jitter_ms.csv"
df = pd.DataFrame({
    "Packet Number": range(1, len(arrival_times_ms) + 1),
    "Arrival Time (ms)": arrival_times_ms,
    "Inter-Arrival Time (IAT) (ms)": iat_ms,
    "Jitter (ms)": jitter_ms
})
df.to_csv(output_file, index=False)
print(f"Results saved to {output_file}")

# Step 6: Plot Jitter vs Arrival Time
plt.figure(figsize=(10, 6))
plt.plot(arrival_times_ms, jitter_ms, label="Jitter", color="blue", marker="o")
plt.title("Jitter vs Packet Arrival Time")
plt.xlabel("Packet Arrival Time (ms)")
plt.ylabel("Jitter (ms)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("jitter.png")
