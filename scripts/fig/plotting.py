import pandas as pd
import matplotlib.pyplot as plt
import argparse
from datetime import datetime, timedelta


class MetricsPlotter:
    def __init__(self, csv_file):
        # Read CSV file
        self.df = pd.read_csv(csv_file)
        # Convert timestamp to datetime
        self.df["datetime"] = pd.to_datetime(self.df["timestamp"], unit="ns")
        # Calculate time offset in seconds from first timestamp
        self.df["time_offset"] = (
            self.df["datetime"] - self.df["datetime"].iloc[0]
        ).dt.total_seconds()

    def filter_time_range(self, start_time=None, end_time=None):
        """Filter data based on time range in seconds from start"""
        filtered_df = self.df.copy()

        if start_time is not None:
            filtered_df = filtered_df[filtered_df["time_offset"] >= start_time]
        if end_time is not None:
            filtered_df = filtered_df[filtered_df["time_offset"] <= end_time]

        return filtered_df

    def plot_metric(self, metric_name, start_time=None, end_time=None, figsize=(12, 6)):
        """Plot a specific metric over time"""
        # Filter data based on time range
        plot_df = self.filter_time_range(start_time, end_time)

        if plot_df.empty:
            print("No data in specified time range")
            return

        if metric_name not in plot_df.columns:
            print(f"Metric '{metric_name}' not found in data. Available metrics:")
            print("\n".join(sorted(plot_df.columns)))
            return

        # Create the plot
        plt.figure(figsize=figsize)
        plt.plot(plot_df["time_offset"], plot_df[metric_name], color="blue", ls="-", marker=".", linewidth=1)

        # Add labels and title
        plt.xlabel("Time (seconds)")
        plt.ylabel(metric_name)
        plt.title(f"{metric_name} over Time")

        # Add grid
        plt.grid(True, linestyle="--", alpha=0.7)

        # Format plot
        plt.tight_layout()

        return plt

    def get_available_metrics(self):
        """Return list of available metrics"""
        return sorted(self.df.columns)


def parse_time(time_str):
    """Parse time string in format 'HH:MM:SS' to seconds"""
    if time_str is None:
        return None
    try:
        t = datetime.strptime(time_str, "%H:%M:%S")
        return t.hour * 3600 + t.minute * 60 + t.second
    except ValueError:
        try:
            # Try parsing as number of seconds
            return float(time_str)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Time must be in 'HH:MM:SS' format or number of seconds, not '{time_str}'"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Plot metrics from TCP connection log CSV"
    )
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("metric", help="Name of the metric to plot")
    parser.add_argument(
        "-s",
        "--start",
        type=parse_time,
        help="Start time (HH:MM:SS or seconds from start)",
    )
    parser.add_argument(
        "-e", "--end", type=parse_time, help="End time (HH:MM:SS or seconds from start)"
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (if not specified, shows plot)"
    )
    parser.add_argument(
        "-w", "--width", type=int, default=12, help="Plot width in inches"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=6, help="Plot height in inches"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List available metrics and exit"
    )

    args = parser.parse_args()

    # Create plotter
    plotter = MetricsPlotter(args.csv_file)

    # List metrics if requested
    if args.list:
        print("Available metrics:")
        for metric in plotter.get_available_metrics():
            print(f"  {metric}")
        return

    # Create plot
    plt = plotter.plot_metric(
        args.metric, args.start, args.end, figsize=(args.width, args.height)
    )

    if plt is None:
        return

    # Save or show plot
    if args.output:
        plt.savefig(args.output)
        print(f"Plot saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
