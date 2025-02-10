import csv
import matplotlib.pyplot as plt
import re
import code


# Parameters
frame_size = 666667  # bytes (for a 4K video frame at 20 Mbps, 30 fps)
fname = "./client_pkt.csv"
output_file = "frame_timestamps.csv"

# Read TCP packet data
packets = []
with open(fname, "r") as file:
    reader = csv.reader(file, delimiter="\t")
    for row in reader:
        timestamp, src_ip, dst_ip, seq, ack, length = row
        length = int(length)
        if float(timestamp) > 140:
            break
        if length > 0:
            packets.append({
                "timestamp": float(timestamp),
                "seq": int(seq),
                "length": int(length)
            })

# Sort packets by sequence number and timestamp
packets.sort(key=lambda x: (x["seq"], x["timestamp"]))

# Calculate frame timestamps, handling duplicates
frame_timestamps = []
current_frame_size = 0
frame_start_time = None
seen_sequences = set()  # Track processed sequence numbers

for packet in packets:
    if packet["seq"] in seen_sequences:
        # Skip duplicate packet
        continue
    seen_sequences.add(packet["seq"])

    if current_frame_size == 0:
        frame_start_time = packet["timestamp"]  # First packet of the frame

    current_frame_size += packet["length"]

    if current_frame_size >= frame_size:
        frame_timestamps.append(packet["timestamp"])
        current_frame_size = 0  # Reset for the next frame

# Save frame timestamps to a CSV file
with open(output_file, "w") as file:
    writer = csv.writer(file)
    writer.writerow(["Frame Number", "Completion Timestamp"])
    for i, timestamp in enumerate(frame_timestamps, start=1):
        writer.writerow([i, timestamp])

print(f"Frame timestamps saved to {output_file}")

plt.plot(frame_timestamps)
plt.savefig("frames.png")
