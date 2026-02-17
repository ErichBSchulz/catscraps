import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple
from .models import BenchmarkData

# Tableau 10 color palette for a professional look
COLORS = [
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC949",
    "#AF7AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
]


def _get_data(
    benchmark_data_list: List[BenchmarkData],
) -> Tuple[List[str], List[List[float]], List[List[float]], List[List[float]]]:
    """Extracts model names and metrics across all runs."""
    model_names = []
    for bd in benchmark_data_list:
        for name in bd.get_model_names():
            if name not in model_names:
                model_names.append(name)

    all_p1, all_p2, all_costs = [], [], []
    for bd in benchmark_data_list:
        p1, p2, costs = [], [], []
        for name in model_names:
            try:
                res = bd.get_model_result(name)
                p1.append(res.pass_rate_1)
                p2.append(res.pass_rate_2)
                costs.append(res.total_cost)
            except KeyError:
                p1.append(0.0)
                p2.append(0.0)
                costs.append(0.0)
        all_p1.append(p1)
        all_p2.append(p2)
        all_costs.append(costs)
    return model_names, all_p1, all_p2, all_costs


def create_plot(
    benchmark_data_list: List[BenchmarkData],
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
    plot_type: str = "A",
) -> None:
    """Create a visualization of benchmark results."""
    if not benchmark_data_list:
        return
    model_names, all_p1, all_p2, all_costs = _get_data(benchmark_data_list)
    if plot_type == "B":
        _create_plot_b(
            benchmark_data_list, model_names, all_p1, all_p2, all_costs, output_file
        )
    else:
        _create_plot_a(
            benchmark_data_list,
            model_names,
            all_p1,
            all_p2,
            all_costs,
            show_cost,
            output_file,
        )


def _create_plot_a(
    benchmark_data_list, model_names, all_p1, all_p2, all_costs, show_cost, output_file
):
    num_runs = len(benchmark_data_list)
    fig, ax = plt.subplots(figsize=(12, max(5, len(model_names) * 0.7)))
    y_pos = np.arange(len(model_names))
    bar_height = 0.8 / num_runs

    for i, bd in enumerate(benchmark_data_list):
        offset = (i - (num_runs - 1) / 2) * bar_height
        widths = [all_p2[i][j] - all_p1[i][j] for j in range(len(model_names))]
        bars = ax.barh(
            y_pos + offset,
            widths,
            bar_height,
            left=all_p1[i],
            label=bd.run_name,
            color=COLORS[i % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )
        if show_cost:
            for j, bar in enumerate(bars):
                if all_costs[i][j] > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() + 0.5,
                        bar.get_y() + bar.get_height() / 2,
                        f"${all_costs[i][j]:.4f}",
                        va="center",
                        fontsize=8,
                        color="#555555",
                    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(model_names)
    ax.set_xlabel("Pass Rate (%)")
    ax.set_title("Model Pass Rates: Range (Pass 1 to Pass 2)")
    ax.set_xlim(0, 105)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    for y in y_pos:
        ax.axhline(y + 0.5, color="gray", linestyle="-", linewidth=0.5, alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()


def _create_plot_b(
    benchmark_data_list, model_names, all_p1, all_p2, all_costs, output_file
):
    fig, ax = plt.subplots(figsize=(10, 7))

    # Add Best/Worst markers
    ax.text(
        0.05,
        0.95,
        "Worst",
        transform=ax.transAxes,
        fontsize=40,
        color="gray",
        alpha=0.1,
        ha="left",
        va="top",
        fontweight="bold",
    )
    ax.text(
        0.95,
        0.05,
        "Best",
        transform=ax.transAxes,
        fontsize=40,
        color="gray",
        alpha=0.1,
        ha="right",
        va="bottom",
        fontweight="bold",
    )

    for i, bd in enumerate(benchmark_data_list):
        color = COLORS[i % len(COLORS)]
        for j, name in enumerate(model_names):
            p1, p2, cost = all_p1[i][j], all_p2[i][j], all_costs[i][j]
            if cost <= 0:
                continue

            display_name = name
            if len(name) > 10 and "-" in name:
                display_name = "-".join(name.split("-")[1:])

            ax.hlines(cost, p1, p2, colors=color, linewidth=6, alpha=0.6)
            ax.plot([p1, p2], [cost, cost], "|", color=color, markersize=8)
            ax.text(
                (p1 + p2) / 2,
                cost,
                f" {display_name}",
                va="bottom",
                ha="center",
                fontsize=14,
                alpha=0.7,
            )

    ax.set_xlabel("Pass Rate (%)")
    ax.set_ylabel("Cost ($)")
    ax.set_title("Cost vs. Pass Rate Range")
    ax.grid(True, linestyle=":", alpha=0.4)
    from matplotlib.lines import Line2D

    handles = [
        Line2D([0], [0], color=COLORS[i % len(COLORS)], lw=4, label=bd.run_name)
        for i, bd in enumerate(benchmark_data_list)
    ]
    ax.legend(handles=handles)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
