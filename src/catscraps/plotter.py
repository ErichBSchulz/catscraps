import matplotlib.pyplot as plt
import numpy as np
from typing import List
from .models import BenchmarkData


def create_plot(
    benchmark_data_list: List[BenchmarkData],
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
    plot_type: str = "A",
) -> None:
    """
    Create a visualization of benchmark results.

    Args:
        benchmark_data_list: List of BenchmarkData objects (one per run)
        show_cost: Whether to display cost labels on bars
        output_file: Path to save the output image
        plot_type: "A" for horizontal bars (pass rate), "B" for vertical bars (cost vs pass rate)
    """
    if plot_type == "B":
        _create_plot_b(benchmark_data_list, show_cost, output_file)
    else:
        _create_plot_a(benchmark_data_list, show_cost, output_file)


def _create_plot_a(
    benchmark_data_list: List[BenchmarkData],
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
) -> None:
    """
    Create a horizontal bar chart showing pass rate ranges.
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
    # Fallback for more runs
    if len(colors) < num_runs:
        colors = plt.cm.tab10(np.linspace(0, 1, num_runs))

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


def _create_plot_b(
    benchmark_data_list: List[BenchmarkData],
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
) -> None:
    """
    Create a scatter/bar plot where X is passrate and Y is cost.
    Each model is represented as a vertical bar from pass1 to pass2 (width) at a specific cost height.
    """
    # Get all unique model names from the first run
    first_run = benchmark_data_list[0]
    model_names = first_run.get_model_names()
    num_runs = len(benchmark_data_list)

    # Prepare data
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
                pass1.append(0.0)
                pass2.append(0.0)
                costs.append(0.0)
        all_pass1.append(pass1)
        all_pass2.append(pass2)
        all_costs.append(costs)

    # Plotting
    fig, ax = plt.subplots(figsize=(14, 10))

    colors = ["#a0cbe8", "#ffb366", "#59a14f", "#edc949"][:num_runs]
    # Fallback for more runs
    if len(colors) < num_runs:
        colors = plt.cm.tab10(np.linspace(0, 1, num_runs))

    # We need to manage the legend manually since we are plotting many bars
    legend_handles = []

    for i in range(num_runs):
        run_color = colors[i]
        run_name = benchmark_data_list[i].run_name

        # Create a proxy artist for the legend
        legend_handles.append(
            plt.Rectangle((0, 0), 1, 1, fc=run_color, edgecolor="black", label=run_name)
        )

        for j, model_name in enumerate(model_names):
            p1 = all_pass1[i][j]
            p2 = all_pass2[i][j]
            cost = all_costs[i][j]

            if cost <= 0:
                continue

            width = p2 - p1
            # If width is effectively 0, make it visible but small or just a line
            if width < 0.5:
                width = 0.5

            # Height of the bar representing the "model"
            # We want a vertical bar for the model, but X is passrate.
            # Wait, the requirement says "Each model should be represented as vertical bar from pass1 to pass2."
            # And "X is passrate and Y is cost."
            # That implies a HORIZONTAL bar if X is passrate.
            # But the user said "vertical bar".
            # If X is passrate, pass1 to pass2 is a horizontal range.
            # If Y is cost, then the bar is located at Y=cost.
            # So it must be a horizontal bar located at height Y.
            # Let's assume the user meant a bar spanning the passrate range, positioned at the cost.

            # Thickness of the bar in Y dimension
            bar_height = cost * 0.05  # Scale relative to cost? or fixed visual size?
            # Fixed visual size might be better to compare pass rates.
            # But costs vary wildly.
            # Let's try plotting a horizontal bar at y=cost.

            # To make them visible if costs are similar, we might have overlap issues.
            # But let's follow the prompt: "X is passrate and Y is cost".

            # We use errorbar or hlines or rectangle. Rectangle is best for "bar".
            # X start = p1, width = p2-p1. Y center = cost.

            # Let's define a fixed height for the bar in plot coordinates or data coordinates.
            # Since Y is cost, data coordinates matter.
            # Let's make the bar height proportional to the cost range, or just a fixed visual element.
            # Actually, typically "vertical bar from pass1 to pass2" with X=passrate implies the bar is along X.
            # That is a HORIZONTAL bar in plot terminology.

            # Using broken_barh is good for this.
            # ranges = [(start, width)]
            # yranges = (ymin, height)

            # Let's assume a fixed height for visibility, but centered on the actual cost.
            # However, if costs are small (0.01) vs large (5.0), a fixed height might distort.
            # Let's try plotting lines with markers first, or thin rectangles.
            # Requirement: "vertical bar from pass1 to pass2" -> This is contradictory with X=Passrate.
            # If X is passrate, a range [p1, p2] is horizontal.
            # Maybe they mean the bar represents the range, and it is plotted.
            # I will assume: Horizontal bar spanning p1 to p2, located at y=cost.
            # The "vertical bar" might refer to the visual marker if they rotated the plot mentally?
            # Or maybe X=Passrate, Y=Cost, and the "bar" connects p1 and p2? Yes, horizontal.

            ax.hlines(
                y=cost,
                xmin=p1,
                xmax=p2,
                colors=run_color,
                linewidth=4,
                label=run_name if j == 0 else "",
            )

            # Add markers at ends
            ax.plot(p1, cost, "|", color=run_color, markersize=10)
            ax.plot(p2, cost, "|", color=run_color, markersize=10)

            # Label the model
            ax.text(
                (p1 + p2) / 2,
                cost,
                f" {model_name}",
                va="bottom",
                ha="center",
                fontsize=8,
                color="black",
            )

    ax.set_xlabel("Pass Rate (%)")
    ax.set_ylabel("Cost ($)")
    ax.set_title("Cost vs. Pass Rate Range")
    ax.legend(handles=legend_handles)
    ax.grid(True, linestyle="--", alpha=0.5)

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
