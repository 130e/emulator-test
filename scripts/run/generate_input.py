# Emulator has the ability to execute commands before emulation
# This script concatenate commands to file
# Note that no comma allowed in command
import os
import re
import argparse


def process_files(regex, directory="."):
    # Compile the regex pattern
    pattern = re.compile(regex)

    # Iterate over files in the specified directory
    for filename in os.listdir(directory):
        if pattern.match(filename):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                generate_trace(filepath, "test.log")


def generate_trace(input_trace, output_trace, extras):
    try:
        with open(input_trace, "r") as file:
            lines = file.readlines()

        if len(lines) >= 3:
            # read execution time
            for line in lines:
                tokens = line.split(",")
                # print(tokens)
                if tokens[1] == "INIT":
                    execution_time = int(tokens[-1])
                    break
            execution_time /= 1000
            execution_time -= 5
            execution_time = int(execution_time)

            # Ensure linebreak at the end of file
            if lines[-1][-1] != "\n":
                lines[-1] = f"{lines[-1]}\n"

            # FIXME: default to 5257
            # Iperf3
            logname = extras[0]
            cmd = f"2000,CMD,iperf3 -c 10.0.0.2 -p 5257 -t {execution_time} -i 0.1 -J --logfile {logname} &\n"
            lines.append(cmd)

            # monitor
            logname = extras[1]
            execution_time += 1
            exe="/data/ztliu/emulator-test/scripts/run/monitor.sh"
            cmd = f"1000,CMD,{exe} {logname} {execution_time} &\n"
            lines.append(cmd)

            # Write the modified content to the new file
            with open(output_trace, "w") as file:
                file.writelines(lines)

            print(f"Processed file: {input_trace} -> {output_trace}")
        else:
            print(f"File {input_trace} has fewer than 3 lines; skipping.")

    except Exception as e:
        print(f"Error processing file {input_trace}: {e}")


# Example usage
# Update the regex pattern as needed
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate input")
    parser.add_argument("input", help="Path to the input trace")
    parser.add_argument("output", help="Path to the generated trace")
    parser.add_argument("iperf_log")
    parser.add_argument("ss_log")

    # Parse arguments
    args = parser.parse_args()

    extras = [args.iperf_log, args.ss_log]
    generate_trace(args.input, args.output, extras)

    # Batch processing
    # regex_pattern = r"^.*trace-[0-9]+\.csv$"
    # process_files(regex_pattern, directory="../../input/")
