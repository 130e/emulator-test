import re
import csv
import argparse
from datetime import datetime
from pathlib import Path


class TCPLogParser:
    def __init__(self, log_file):
        self.log_file = log_file
        self.parsed_data = []

    def parse_bbr_info(self, bbr_str):
        """Parse the BBR information string into a dictionary."""
        # Extract content between parentheses
        bbr_match = re.search(r"\((.*?)\)", bbr_str)
        if not bbr_match:
            return {}

        bbr_params = {}
        # Split by comma and parse each parameter
        for param in bbr_match.group(1).split(","):
            if ":" not in param:
                continue
            key, value = param.split(":")
            # Remove 'bbr' prefix if present
            key = key.replace("bbr", "").strip()
            # Convert values to numeric where possible
            if "Mbps" in value:
                value = float(value.replace("Mbps", ""))
            elif value.replace(".", "").isdigit():
                value = float(value)
            bbr_params[key] = value
        return bbr_params

    def parse_line(self, line):
        """Parse a single log line into a dictionary of metrics."""
        # Extract timestamp
        time_match = re.search(r"time:(\d+)", line)
        if not time_match:
            return None

        timestamp = int(time_match.group(1))

        # Create a dictionary to store all metrics
        metrics = {
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(
                timestamp / 1e9
            ),  # Convert nanoseconds to datetime
        }

        # Handle BBR information separately first
        bbr_match = re.search(r"bbr:\((.*?)\)", line)
        if bbr_match:
            bbr_info = self.parse_bbr_info(bbr_match.group(0))
            metrics["bbr"] = bbr_info
            # Remove the BBR part from the line to avoid parsing conflicts
            line = line.replace(bbr_match.group(0), "")

        # Extract remaining key-value pairs
        pairs = re.findall(r"(\w+):([^ ]+)", line)
        for key, value in pairs:
            try:
                # Convert numeric values
                if value.replace(".", "").isdigit():
                    value = float(value)
                # Handle percentage values
                elif "%" in value:
                    value = float(value.replace("%", ""))
                # Handle Mbps values
                elif "Mbps" in value:
                    value = float(value.replace("Mbps", ""))
            except ValueError:
                # If conversion fails, keep the original string value
                pass

            metrics[key] = value

        return metrics

    def parse_file(self):
        """Parse the entire log file."""
        try:
            with open(self.log_file, "r") as f:
                for line_number, line in enumerate(f, 1):
                    try:
                        parsed_line = self.parse_line(line.strip())
                        if parsed_line:
                            self.parsed_data.append(parsed_line)
                    except Exception as e:
                        print(f"Warning: Error parsing line {line_number}: {e}")
                        print(f"Line content: {line.strip()}")
                        continue
        except FileNotFoundError:
            print(f"Error: Log file '{self.log_file}' not found")
            return False
        except Exception as e:
            print(f"Error parsing file: {e}")
            return False
        return True

    def save_csv(self, output_file):
        """Save parsed data to CSV file."""
        if not self.parsed_data:
            print("No data to save")
            return False

        # Flatten BBR metrics for CSV output
        flattened_data = []
        for entry in self.parsed_data:
            flat_entry = entry.copy()
            if "bbr" in flat_entry:
                bbr_data = flat_entry.pop("bbr")
                for k, v in bbr_data.items():
                    flat_entry[f"bbr_{k}"] = v
            flattened_data.append(flat_entry)

        # Get all unique keys for CSV headers
        headers = set()
        for entry in flattened_data:
            headers.update(entry.keys())

        try:
            with open(output_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=sorted(headers))
                writer.writeheader()
                writer.writerows(flattened_data)
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
        return True


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Parse TCP connection log files")
    parser.add_argument("log_file", help="Path to the input log file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output CSV file (default: parsed_<input_filename>.csv)",
        default=None,
    )

    # Parse arguments
    args = parser.parse_args()

    # If no output file specified, create default name
    if args.output is None:
        input_path = Path(args.log_file)
        args.output = f"parsed_{input_path.stem}.csv"

    # Create parser and process file
    parser = TCPLogParser(args.log_file)
    if parser.parse_file():
        if parser.save_csv(args.output):
            print(f"Successfully parsed log file and saved to {args.output}")
            # Print some basic statistics
            print(f"\nProcessed {len(parser.parsed_data)} log entries")
            if parser.parsed_data:
                first_entry = parser.parsed_data[0]["datetime"]
                last_entry = parser.parsed_data[-1]["datetime"]
                duration = last_entry - first_entry
                print(f"Time span: {duration}")
        else:
            print("Failed to save CSV file")
    else:
        print("Failed to parse log file")


if __name__ == "__main__":
    main()
