import csv
import matplotlib.pyplot as plt

# Input and output files
input_file = "frame_timestamps.csv"
output_file_intervals = "frame_intervals.csv"
output_file_jitter = "frame_jitter.csv"

# Read frame completion times
frame_timestamps = []
with open(input_file, "r") as file:
    reader = csv.reader(file)
    next(reader)  # Skip header
    for row in reader:
        frame_number, timestamp = row
        frame_timestamps.append(float(timestamp))

# Calculate frame intervals and jitter
frame_intervals = [abs(frame_timestamps[i+1] - frame_timestamps[i]) for i in range(len(frame_timestamps) - 1)]
jitter_values = [abs(frame_intervals[i+1] - frame_intervals[i]) for i in range(len(frame_intervals) - 1)]

# Save frame intervals to a CSV file
with open(output_file_intervals, "w") as file:
    writer = csv.writer(file)
    writer.writerow(["Frame Timestamp (s)", "Interval (s)"])
    for i in range(len(frame_intervals)):
        writer.writerow([frame_timestamps[i+1], frame_intervals[i]])

# Save jitter values to a CSV file
with open(output_file_jitter, "w") as file:
    writer = csv.writer(file)
    writer.writerow(["Frame Timestamp (s)", "Jitter (s)"])
    for i in range(len(jitter_values)):
        writer.writerow([frame_timestamps[i+2], jitter_values[i]])

# Plotting frame intervals
plt.figure(figsize=(10, 6))
plt.plot(frame_timestamps[1:], frame_intervals, marker='o', label="Frame Intervals (s)")
plt.xlabel("Frame Timestamp (s)")
plt.ylabel("Interval (s)")
plt.title("Frame Intervals Over Time")
plt.legend()
plt.grid()
plt.savefig("frame_intervals-2.png")

# Plotting jitter
plt.figure(figsize=(10, 6))
plt.plot(frame_timestamps[2:], jitter_values, marker='o', color='orange', label="Frame Jitter (s)")
plt.xlabel("Frame Timestamp (s)")
plt.ylabel("Jitter (s)")
plt.title("Frame Jitter Over Time")
plt.legend()
plt.grid()
plt.savefig("frame_jitter-2.png")