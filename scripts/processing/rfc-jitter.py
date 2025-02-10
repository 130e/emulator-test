import pyshark
import csv
import matplotlib.pyplot as plt
import re
import code
import pandas as pd


# DEBUG counter

# Function to parse PCAP and extract timestamps and sequence numbers
def parse_pcap(pcap_file, filter):
    packets = []
    capture = pyshark.FileCapture(pcap_file, display_filter=filter)
    n = 200
    for packet in capture:
        n -= 1
        if n <= 0:
            break
        try:
            tcp_layer = packet.tcp
            seq_num = int(tcp_layer.seq)
            timestamp = float(packet.sniff_timestamp)
            packets.append((seq_num, timestamp))
        except AttributeError:
            print("Pcap parsing error")
            continue
    capture.close()
    print("Parsing done")
    return packets

# Generate client csv
# tshark -r trace-1-client-debug.pcap -Y "ip.dst == 10.0.0.2" -T fields -e frame.time_epoch -e tcp.seq_raw -e tcp.ack_raw -E separator=, > client_arrival.csv

def parse_serverts(filename):
    parsed_data = []
    with open(filename, "r") as f:
        text = f.read()
        pattern = r'packet,(\d+),(\d+),(\d+),(\d+)'
        matches = re.findall(pattern, text)
        for epoch, port, tcp_seq, tcp_ack in matches:
            if port == "50730":
                parsed_data.append((int(epoch), int(tcp_seq), int(tcp_ack)))        
    return parsed_data

def parse_clientts(filename):
    parsed_data = []
    with open(filename, "r") as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            epoch_time = int(float(row[0])*1000)  # Convert epoch time to float
            tcp_seq = int(row[1])       # Convert TCP sequence number to int
            tcp_ack = int(row[2])       # Convert TCP acknowledgment number to int
            parsed_data.append((epoch_time, tcp_seq, tcp_ack))
    return parsed_data

# Match packets from sender and receiver
def map_packets(sender, receiver):
    # Create a dictionary to store sender packets by tcp_seq
    sender_dict = {}
    for send_time, tcp_seq, tcp_ack in sender:
        if tcp_seq in sender_dict:
            if send_time > sender_dict[tcp_seq][0]:
                continue
        sender_dict[tcp_seq] = (send_time, tcp_ack)
    # sender_dict = {tcp_seq: (send_time, tcp_ack) for send_time, tcp_seq, tcp_ack in sender}
    # Create a list to store the result
    result = [("seq", "ack", "send_ts", "recv_ts")]
    # Iterate through receiver packets and match using tcp_seq
    seen = set()
    for receive_time, tcp_seq, tcp_ack in receiver:
        if tcp_seq in sender_dict:
            send_time, sender_ack = sender_dict[tcp_seq]
            if tcp_ack != sender_ack:
                print("Error: tcp ack unmatched but seq match")
                print(tcp_seq, tcp_ack, sender_ack)
            else:
                if tcp_seq not in seen:
                    result.append((tcp_seq, tcp_ack, send_time, receive_time))
                    seen.add(tcp_seq)
    return result

# Compute jitter and transit times
def compute_jitter_and_transit(df_matched):
    results = []
    prev_transit_time = None
    jitter = 0

    for i,r in df_matched.iterrows():
        transit_time = r.rts - r.sts
        if transit_time < 0:
            print("ERROR: Receive earlier before sent!")
            continue
        if prev_transit_time is not None:
            jitter += (abs(transit_time - prev_transit_time) - jitter) / 16
        results.append((r.sts, transit_time, jitter))
        prev_transit_time = transit_time

    return results

# Save results to CSV
def save_to_csv(results, output_file):
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(results)

# Main workflow
if __name__ == "__main__":
    output_csv = "matched.csv"
    serverlog = "./packet.log"
    clientlog = "./client_arrival.csv"

    # server_ts = parse_serverts(serverlog)
    # print("server done")
    # client_ts = parse_clientts(clientlog)
    # print("client done")

    # matched_packets = map_packets(server_ts, client_ts)
    # save_to_csv(matched_packets, output_csv)

    df = pd.read_csv(output_csv)
    df["sts"] = df.send_ts - df.send_ts[0]
    df["rts"] = df.recv_ts - df.send_ts[0]
    df.sort_values("sts", inplace=True)

    # x,y = [],[]
    # for i,r in df.iterrows():
    #     if r["rts"] > r["sts"]:
    #         x.append(r["sts"])
    #         y.append(r["rts"] - r["sts"])
    # plt.scatter(x, y)

    # plt.plot(df.sts, df.rts - df.sts)
    # plt.savefig("test.png")
    # code.interact(local=locals())

    results = compute_jitter_and_transit(df)
    save_to_csv(results, "jitter.csv")
    
    # x = [row[0] for row in results]
    # y = [row[2] for row in results]
    # plt.scatter(x, y, s=1)
    # plt.savefig("jitter.png")
    # code.interact(local=locals())
