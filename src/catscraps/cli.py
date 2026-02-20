import typer
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
import subprocess
import sys
import os
from pathlib import Path

from rich.table import Table
import pandas as pd
from catscraps.reader import read_file, load_benchmarks
from catscraps.plotter import create_plot
from catscraps.models import BenchmarkData, ModelResult

# Configure logger
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("catscraps")

app = typer.Typer(help="Benchmark visualization tool")
console = Console()


def configure_logging(verbose: int, quiet: bool):
    """Configure logging level based on flags."""
    if quiet:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
    elif verbose >= 2:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


def parse_group_by(ctx, param, value):
    if value:
        if value.strip().lower() == "default":
            return ["Model", "Edit Format", "Commit"]
        return [x.strip() for x in value.split(",")]
    return None


@app.callback()
def main():
    """
    Benchmark visualization tool.
    """
    pass


@app.command()
def table(
    files: list[Path] = typer.Argument(None, help="List of benchmark files to display"),
    group_by: str = typer.Option(
        "Model,Edit Format,Commit",
        "--group-by",
        "-g",
        help="Comma separated fields to group by. Use 'default' for standard grouping.",
        callback=parse_group_by,
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (use -v for INFO, -vv for DEBUG)",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """Display benchmark data in a table."""
    configure_logging(verbose, quiet)

    if not files:
        console.print("[red]Error: At least one file must be provided[/red]")
        raise typer.Exit(1)

    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File '{f}' not found[/red]")
            raise typer.Exit(1)

    try:
        df = load_benchmarks(files)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if df.empty:
        console.print("[yellow]No data found.[/yellow]")
        return

    # Normalize DataFrame for display
    # Use "Short Model" for the "Model" column as requested
    df["Model"] = df.get("Short Model", "Unknown")

    # Calculate Cost/Case if not explicit
    if "Cost/Case" not in df.columns:

        def _calc_cost(r):
            try:
                tc = float(r.get("total_cost", 0))
                # Prefer 'n', fallback to 'test_cases' or 'total_tests'
                n = float(
                    r.get("n") or r.get("test_cases") or r.get("total_tests") or 0
                )
                # If total_cost is very small (e.g. < 5) and n is large, it might already be unit cost,
                # but let's trust the names: total_cost / n.
                return tc / n if n > 0 else 0.0
            except (ValueError, TypeError):
                return 0.0

        df["Cost/Case"] = df.apply(_calc_cost, axis=1)

    # Ensure "n" column exists for display
    if "n" not in df.columns:
        df["n"] = df.get("test_cases", df.get("total_tests", "N/A"))

    # Map other standard columns
    col_map = {
        "pass_rate_1": "Pass 1",
        "pass_rate_2": "Pass 2",
        "edit_format": "Edit Format",
        "commit_hash": "Commit",
    }
    for src, dst in col_map.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]

    # Handle Grouping
    if group_by:
        valid_groups = [g for g in group_by if g in df.columns]
        if valid_groups:
            agg_rules = {
                "Pass 1": "mean",
                "Pass 2": "mean",
                "Cost/Case": "mean",
                "n": "sum",
            }
            agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
            df = df.groupby(valid_groups, as_index=False).agg(agg_rules)

    # Prepare Table
    table = Table(title="Benchmark Results")

    # Columns to display: Groups first, then standard metrics
    display_cols = []

    # Priority columns
    std_cols = [
        "File",
        "Model",
        "Edit Format",
        "Commit",
        "n",
        "Pass 1",
        "Pass 2",
        "Cost/Case",
    ]
    
    # Columns to actually display
    display_cols = []
    
    # If grouping, put group columns first
    if group_by:
        for g in group_by:
            if g in df.columns and g not in display_cols:
                display_cols.append(g)

    # Add standard cols if present
    for c in std_cols:
        if c in df.columns and c not in display_cols:
            display_cols.append(c)

    for col in display_cols:
        justify = "right"
        if col in ["File", "Model", "Edit Format", "Commit"]:
            justify = "left"

        style = "dim" if col == "File" else ("cyan" if col == "Model" else None)
        table.add_column(col, justify=justify, style=style)

    for _, row in df.iterrows():
        formatted_row = []
        for col in display_cols:
            val = row[col]

            if pd.isna(val) or val == "N/A":
                formatted_row.append("N/A")
            elif col.startswith("Pass"):
                formatted_row.append(f"{float(val):.1f}%")
            elif col == "Cost/Case":
                formatted_row.append(f"${float(val):.4f}")
            elif col == "Sec/Case":
                formatted_row.append(f"{float(val):.1f}")
            elif col == "N":
                formatted_row.append(str(int(val)))
            else:
                formatted_row.append(str(val))
        table.add_row(*formatted_row)

    console.print(table)


@app.command()
def plot(
    files: list[Path] = typer.Argument(None, help="List of benchmark files to plot"),
    file_list: Path = typer.Option(
        None, "--file-list", "-l", help="File containing list of benchmark files"
    ),
    input_format: str = typer.Option(
        "dwash20260217", "--input-format", "-i", help="Input file format"
    ),
    auto_open: bool = typer.Option(
        False, "--auto-open", "-o", help="Open the graph after creation"
    ),
    show_cost: bool = typer.Option(
        True, "--show-cost/--no-show-cost", help="Display cost labels on bars"
    ),
    plot_type: str = typer.Option(
        "A", "--type", "-t", help="Plot type: A (standard) or B (pass-rate vs cost)"
    ),
    output: str = typer.Option(
        "benchmark_graph.png", "--output", "-f", help="Output file name"
    ),
    group_by: str = typer.Option(
        None,
        "--group-by",
        "-g",
        help="Comma separated fields to group by. Aggregates data if set.",
        callback=parse_group_by,
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (use -v for INFO, -vv for DEBUG)",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Create a visualization of benchmark results.

    The first file determines the model order.
    """
    configure_logging(verbose, quiet)

    all_files = list(files) if files else []
    if file_list:
        if not file_list.exists():
            console.print(f"[red]Error: File list '{file_list}' not found[/red]")
            raise typer.Exit(1)
        all_files.extend(
            [
                Path(line.strip())
                for line in file_list.read_text().splitlines()
                if line.strip()
            ]
        )

    if not all_files:
        console.print("[red]Error: At least one file must be provided[/red]")
        raise typer.Exit(1)

    # Read all benchmark files using pandas loader
    try:
        df = load_benchmarks(all_files)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if df.empty:
        console.print("[red]No data found to plot[/red]")
        raise typer.Exit(1)

    # Grouping logic for plot
    if group_by:
        valid_groups = [g for g in group_by if g in df.columns]
        if valid_groups:
            agg_rules = {
                "pass_rate_1": "mean",
                "pass_rate_2": "mean",
                "total_cost": "mean",
                "Short Model": "first",
            }
            agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
            df = df.groupby(valid_groups, as_index=False).agg(agg_rules)

            # If Short Model is lost or ambiguous, rebuild it
            if "Short Model" not in df.columns or df["Short Model"].isna().all():
                df["Short Model"] = df[valid_groups].apply(
                    lambda x: " ".join(x.astype(str)), axis=1
                )

            # Mark as aggregated run
            df["File"] = "Aggregated"

    # Create the plot
    with console.status("[bold green]Creating plot...") as status:
        try:
            create_plot(
                df=df,
                show_cost=show_cost,
                output_file=output,
                plot_type=plot_type,
            )
            console.print(f"[green]✓ Graph saved to {output}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating plot: {e}[/red]")
            # raise typer.Exit(1) # Fail fast?
            raise e

    # Auto-open if requested
    if auto_open:
        if sys.platform == "darwin":
            subprocess.run(["open", output])
        elif sys.platform == "win32":
            os.startfile(output)
        else:
            subprocess.run(["xdg-open", output])
        console.print(f"[blue]Opened {output}[/blue]")


@app.command()
def version(
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (use -v for INFO, -vv for DEBUG)",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """Show version information."""
    configure_logging(verbose, quiet)
    console.print("Benchmark Plotter v0.1.0")


if __name__ == "__main__":
    app()
