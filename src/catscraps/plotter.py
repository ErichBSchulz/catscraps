import matplotlib.pyplot as plt
import numpy as np
from typing import List
from .models import BenchmarkData


def create_plot(
    benchmark_data_list: List[BenchmarkData],
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
) -> None:
    """
    Create a horizontal bar chart showing pass rate ranges.

    Args:
        benchmark_data_list: List of BenchmarkData objects (one per run)
        show_cost: Whether to display cost labels on bars
        output_file: Path to save the output image
    """
    # Get all unique model names from the first run
    first_run = benchmark_data_list[0]
    model_names = first_run.get_model_names()

    # Prepare data arrays
    all_pass1 = []
    all_pass2 = []
    all_costs = []

    for benchmark_data in benchmark_data_list:
        pass1 = []
        pass2 = []
        costs = []
        for model_name in model_names:
            try:
                result = benchmark_data.get_model_result(model_name)
                pass1.append(result.pass_rate_1)
                pass2.append(result.pass_rate_2)
                costs.append(result.total_cost)
            except KeyError:
                # Model not in this run
                pass1.append(0.0)
                pass2.append(0.0)
                costs.append(0.0)
        all_pass1.append(pass1)
        all_pass2.append(pass2)
        all_costs.append(costs)

    # Plotting
    fig, ax = plt.subplots(figsize=(14, len(model_names) * 0.8))

    y_pos = np.arange(len(model_names))
    bar_width = 0.35
    num_runs = len(benchmark_data_list)

    # Calculate bar positions
    bar_positions = []
    for i in range(num_runs):
        offset = (i - (num_runs - 1) / 2) * bar_width
        bar_positions.append(y_pos + offset)

    # Plot bars for each run
    bars_list = []
    colors = ["#a0cbe8", "#ffb366", "#59a14f", "#edc949"][:num_runs]

    for i in range(num_runs):
        bars = ax.barh(
            bar_positions[i],
            [all_pass2[i][j] - all_pass1[i][j] for j in range(len(model_names))],
            bar_width,
            left=all_pass1[i],
            label=benchmark_data_list[i].run_name,
            color=colors[i],
            edgecolor="black",
        )
        bars_list.append(bars)

        # Add cost labels if requested
        if show_cost:
            add_cost_labels(ax, bars, all_costs[i], bar_positions[i])

    # Set y-ticks to model names
    ax.set_yticks(y_pos)
    ax.set_yticklabels(model_names)
    ax.set_xlabel("Pass Rate (%)")

    title = "Model Pass Rates: Range Bars (Pass 1 start, Pass 2 end)"
    if show_cost:
        title += " with Cost"
    ax.set_title(title)

    ax.legend()
    ax.grid(axis="x", linestyle="--", alpha=0.7)

    # Add horizontal lines to separate model groups
    for y in y_pos:
        ax.axhline(y + 0.5, color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file)


def add_cost_labels(ax, bars, costs, y_positions):
    """Add cost labels to bars."""
    for bar, cost, y in zip(bars, costs, y_positions):
        if cost <= 0:
            continue
        x = bar.get_x() + bar.get_width()
        y_pos = bar.get_y() + bar.get_height() / 2
        label = f"${cost:.4f}"
        ax.text(
            x + 0.5,
            y_pos,
            label,
            va="center",
            fontsize=8,
            color="black",
            fontweight="bold",
        )
