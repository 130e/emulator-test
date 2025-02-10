import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from pathlib import Path
from datetime import datetime


class MetricsPlotter:
    def __init__(self, csv_file):
        self.data = pd.read_csv(csv_file)

        # Set style TODO: More robust style choosing
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

    def plot_metric(self, metric, title=None, figsize=(12, 6), output=None):
        """Plot a single metric over time."""
        if metric not in self.data.columns:
            print(f"Error: Metric '{metric}' not found in data")
            print("Available metrics:", ", ".join(self.data.columns))
            return False

        plt.figure(figsize=figsize)
        plt.plot(self.data["timestamp"]/1e9, self.data[metric], linewidth=1)

        # Set title and labels
        plt.title(title or f"{metric} over Time")
        plt.xlabel("Time")
        plt.ylabel(metric)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)

        # Adjust layout to prevent label cutoff
        plt.tight_layout()

        # Save or show
        if output:
            plt.savefig(output, dpi=300, bbox_inches="tight")
            print(f"Plot saved to {output}")
        else:
            plt.show()

        plt.close()
        return True

    def plot_multiple_metrics(self, metrics, title=None, figsize=(12, 6), output=None):
        """Plot multiple metrics on the same graph."""
        # Verify all metrics exist
        for metric in metrics:
            if metric not in self.data.columns:
                print(f"Error: Metric '{metric}' not found in data")
                print("Available metrics:", ", ".join(self.data.columns))
                return False

        plt.figure(figsize=figsize)

        # Plot each metric
        for metric in metrics:
            plt.plot(
                self.data["timestamp"]/1e9, self.data[metric], label=metric, linewidth=1
            )

        # Add legend
        plt.legend()

        # Set title and labels
        plt.title(title or "Multiple Metrics over Time")
        plt.xlabel("Time")
        plt.ylabel("Value")

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)

        # Adjust layout to prevent label cutoff
        plt.tight_layout()

        # Save or show
        if output:
            plt.savefig(output, dpi=300, bbox_inches="tight")
            print(f"Plot saved to {output}")
        else:
            plt.show()

        plt.close()
        return True

    def list_available_metrics(self):
        """Print all available metrics in the CSV file."""
        print("\nAvailable metrics:")
        for metric in sorted(self.data.columns):
            print(f"- {metric}")


def main():
    parser = argparse.ArgumentParser(description="Plot TCP metrics from CSV file")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument(
        "-m",
        "--metrics",
        nargs="+",
        help="Metrics to plot (space-separated). Example: bbr_bw delivery_rate",
    )
    parser.add_argument("-o", "--output", help="Output file for the plot (optional)")
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all available metrics in the CSV file",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        type=int,
        default=[12, 6],
        help="Figure size in inches (width height). Default: 12 6",
    )

    args = parser.parse_args()

    plotter = MetricsPlotter(args.csv_file)

    if args.list:
        plotter.list_available_metrics()
        return

    if not args.metrics:
        print("Error: Please specify at least one metric to plot using -m/--metrics")
        plotter.list_available_metrics()
        return

    if len(args.metrics) == 1:
        plotter.plot_metric(
            args.metrics[0], figsize=tuple(args.figsize), output=args.output
        )
    else:
        plotter.plot_multiple_metrics(
            args.metrics, figsize=tuple(args.figsize), output=args.output
        )


if __name__ == "__main__":
    main()
