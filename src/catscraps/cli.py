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
from catscraps.stats import get_ci
from catscraps.panda_utils import expand_column_globs, validate_columns_exist

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


def parse_extras_csv(ctx, param, value):
    """Parse CSV string of extra columns into a list."""
    if value:
        # Split by comma, strip whitespace, filter empty strings
        return [col.strip() for col in value.split(",") if col.strip()]
    return None


@app.callback()
def main():
    """
    Catscraps: Benchmark visualization and analysis tool.

    Load benchmark data from various file formats, filter with pandas queries,
    group results, and visualize them via tables or plots.
    """
    pass


@app.command()
def table(
    files: list[Path] = typer.Argument(None, help="List of benchmark files to display"),
    query: str = typer.Option(
        None, "--query", "-Q", help="Pandas query string to filter data"
    ),
    group_by: str = typer.Option(
        None,
        "--group-by",
        "-g",
        help="Comma separated fields to group by. Use 'default' for standard grouping.",
        callback=parse_group_by,
    ),
    extras: str = typer.Option(
        None,
        "--extras",
        "-x",
        help="Comma-separated list of extra columns to display. Supports glob patterns (*, ?, []).",
        callback=parse_extras_csv,
    ),
    show_ci: bool = typer.Option(
        False, "--show-ci", help="Display confidence intervals for pass rates"
    ),
    alpha: float = typer.Option(
        0.05, "--alpha", help="Alpha value for confidence intervals (default 0.05)"
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
        df = load_benchmarks(files, query=query)
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

    # Handle extra columns
    extra_display_cols = []
    if extras:
        # Expand glob patterns against available columns
        expanded_extras = expand_column_globs(list(df.columns), extras)
        
        # Validate which columns exist
        existing_extras, missing_extras = validate_columns_exist(list(df.columns), expanded_extras)
        
        if missing_extras:
            # Get all available columns for error message
            all_columns = sorted(list(df.columns))
            console.print(f"[red]Error: The following columns were not found:[/red]")
            for missing in missing_extras:
                console.print(f"  [red]{missing}[/red]")
            console.print(f"\n[yellow]Available columns:[/yellow]")
            # Display in columns for readability
            col_width = max(len(col) for col in all_columns) + 2
            cols_per_line = 4
            for i in range(0, len(all_columns), cols_per_line):
                line_cols = all_columns[i:i + cols_per_line]
                console.print("  " + "".join(f"{col:<{col_width}}" for col in line_cols))
            raise typer.Exit(1)
        
        extra_display_cols = existing_extras

    # Prepare Table
    table = Table(title="Benchmark Results")

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

    # Add extra columns at the end
    for extra in extra_display_cols:
        if extra not in display_cols:
            display_cols.append(extra)

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
                try:
                    val_float = float(val)
                    display_val = val_float
                    if val_float <= 1.0 and val_float > 0:
                        # Likely a rate 0-1, convert to %
                        display_val = val_float * 100

                    if show_ci and "n" in row and row["n"] not in [None, "N/A", 0]:
                        n_val = float(row["n"])
                        # Count for CI calculation
                        count = int((display_val / 100.0) * n_val)
                        low, high = get_ci(count, n_val, alpha=alpha)
                        formatted_row.append(
                            f"{display_val:.1f}% [{low*100:.1f}-{high*100:.1f}]%"
                        )
                    else:
                        formatted_row.append(f"{display_val:.1f}%")
                except (ValueError, TypeError):
                    formatted_row.append(str(val))

            elif col == "Cost/Case":
                formatted_row.append(f"${float(val):.4f}")
            elif col == "Sec/Case":
                formatted_row.append(f"{float(val):.1f}")
            elif col == "N":
                formatted_row.append(str(int(val)))
            else:
                # Generic formatting for extra columns
                # Try to format numbers nicely, otherwise string representation
                try:
                    if isinstance(val, (int, float)):
                        # Check if it's an integer-like float
                        if float(val).is_integer():
                            formatted_row.append(str(int(val)))
                        else:
                            # Format floats with reasonable precision
                            formatted_row.append(f"{float(val):.2f}")
                    else:
                        formatted_row.append(str(val))
                except (ValueError, TypeError):
                    formatted_row.append(str(val))
        table.add_row(*formatted_row)

    console.print(table)


@app.command()
def plot(
    files: list[Path] = typer.Argument(None, help="List of benchmark files to plot"),
    query: str = typer.Option(
        None, "--query", "-Q", help="Pandas query string to filter data"
    ),
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
        df = load_benchmarks(all_files, query=query)
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
def info(
    files: list[Path] = typer.Argument(None, help="List of benchmark files to analyze"),
    query: str = typer.Option(
        None, "--query", "-Q", help="Pandas query string to filter data"
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
    Show standard pandas info and structure of the unified dataset.
    """
    configure_logging(verbose, quiet)

    if not files:
        console.print("[red]Error: At least one file must be provided[/red]")
        raise typer.Exit(1)

    try:
        df = load_benchmarks(files, query=query)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if df.empty:
        console.print("[yellow]No data found.[/yellow]")
        return

    # Primary Output: Info, Shape, Dtypes
    console.print("\n[bold]Dataframe Info:[/bold]")
    import io

    buffer = io.StringIO()
    df.info(buf=buffer)
    console.print(buffer.getvalue())

    console.print(f"\n[bold]Shape:[/bold] {df.shape}")

    console.print("\n[bold]Data Types:[/bold]")
    console.print(df.dtypes.to_string())

    # Verbose Output: Describe
    if verbose > 0:
        console.print("\n[bold]Statistical Description:[/bold]")
        description = df.describe()
        console.print(description.to_string())


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
