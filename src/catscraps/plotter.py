import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple
import pandas as pd

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


def create_plot(
    df: pd.DataFrame,
    show_cost: bool = True,
    output_file: str = "benchmark_graph.png",
    plot_type: str = "A",
    diamond_field: str = None,
) -> None:
    """Create a visualization from a pandas DataFrame."""
    if df.empty:
        return

    # Determine Runs
    if "File" in df.columns:
        runs = df["File"].unique()
    else:
        runs = ["Aggregated"]
        df["File"] = "Aggregated"

    if "Short Model" not in df.columns:
        # Fallback if logic wasn't applied or column missing
        df["Short Model"] = df.get("model", "Unknown")

    model_names = sorted(df["Short Model"].dropna().unique().tolist())

    all_p1 = []
    all_p2 = []
    all_costs = []
    all_diamonds = [] if diamond_field else None

    for run in runs:
        run_df = df[df["File"] == run]
        p1_list = []
        p2_list = []
        cost_list = []
        diamond_list = [] if diamond_field else None

        for m in model_names:
            row = run_df[run_df["Short Model"] == m]
            if not row.empty:
                r = row.iloc[0]
                p1_list.append(r.get("pass_rate_1", 0.0))
                p2_list.append(r.get("pass_rate_2", 0.0))
                cost_list.append(r.get("total_cost", 0.0))
                if diamond_field and diamond_list is not None:
                    diamond_val = r.get(diamond_field)
                    # Convert to float if possible, otherwise use 0.0
                    try:
                        diamond_list.append(
                            float(diamond_val) if diamond_val is not None else 0.0
                        )
                    except (ValueError, TypeError):
                        diamond_list.append(0.0)
            else:
                p1_list.append(0.0)
                p2_list.append(0.0)
                cost_list.append(0.0)
                if diamond_field and diamond_list is not None:
                    diamond_list.append(0.0)

        all_p1.append(p1_list)
        all_p2.append(p2_list)
        all_costs.append(cost_list)
        if diamond_field and diamond_list is not None:
            all_diamonds.append(diamond_list)

    if plot_type == "B":
        _create_plot_b_arrays(runs, model_names, all_p1, all_p2, all_costs, output_file)
    else:
        _create_plot_a_arrays(
            runs,
            model_names,
            all_p1,
            all_p2,
            all_costs,
            all_diamonds,
            show_cost,
            output_file,
            diamond_field,
        )


def _create_plot_a_arrays(
    run_names,
    model_names,
    all_p1,
    all_p2,
    all_costs,
    all_diamonds,
    show_cost,
    output_file,
    diamond_field=None,
):
    num_runs = len(run_names)
    fig, ax = plt.subplots(figsize=(12, max(5, len(model_names) * 0.7)))
    y_pos = np.arange(len(model_names))
    bar_height = 0.8 / num_runs

    for i, run_name in enumerate(run_names):
        offset = (i - (num_runs - 1) / 2) * bar_height
        widths = [all_p2[i][j] - all_p1[i][j] for j in range(len(model_names))]
        bars = ax.barh(
            y_pos + offset,
            widths,
            bar_height,
            left=all_p1[i],
            label=run_name,
            color=COLORS[i % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )

        # Add diamond markers if diamond data is provided
        if all_diamonds is not None and i < len(all_diamonds):
            diamond_values = all_diamonds[i]
            for j, (bar, diamond_val) in enumerate(zip(bars, diamond_values)):
                if diamond_val > 0:
                    # Position diamond according to its actual value
                    # No longer clipping to bar bounds
                    diamond_x = diamond_val

                    # Add diamond marker
                    ax.plot(
                        diamond_x,
                        bar.get_y() + bar.get_height() / 2,
                        marker="D",
                        markersize=8,
                        color="white",
                        markeredgecolor="black",
                        markeredgewidth=1,
                        zorder=5,  # Ensure diamonds are on top of bars
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

    # Update title to include diamond field info if present
    title = "Model Pass Rates: Range (Pass 1 to Pass 2)"
    if all_diamonds is not None:
        if diamond_field:
            title += f" with {diamond_field} diamond markers"
        else:
            title += " with diamond markers"
    ax.set_title(title)

    ax.set_xlim(0, 105)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")
    for y in y_pos:
        ax.axhline(y + 0.5, color="gray", linestyle="-", linewidth=0.5, alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()


def _create_plot_b_arrays(
    run_names, model_names, all_p1, all_p2, all_costs, output_file
):
    fig, ax = plt.subplots(figsize=(10, 7))
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

    for i, run_name in enumerate(run_names):
        color = COLORS[i % len(COLORS)]
        for j, name in enumerate(model_names):
            p1, p2, cost = all_p1[i][j], all_p2[i][j], all_costs[i][j]
            if cost <= 0:
                continue

            # name is already "Short Model" from the DataFrame logic
            display_name = name

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
        Line2D([0], [0], color=COLORS[i % len(COLORS)], lw=4, label=run_name)
        for i, run_name in enumerate(run_names)
    ]
    ax.legend(handles=handles)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
