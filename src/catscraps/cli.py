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

    # Check files exist
    valid_files = []
    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File '{f}' not found[/red]")
            # We continue checking other files to report all missing ones if needed,
            # but per strict fail-fast rules, maybe we should just crash?
            # The prompt says "Fail very loudly... unless explicitly told to catch them".
            # For CLI arguments, it's usually better to list missing files then exit.
            # But let's fail immediately on the first missing file to be strict.
            raise typer.Exit(1)
        valid_files.append(f)

    try:
        df = load_benchmarks(valid_files)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if df.empty:
        console.print("[yellow]No data found.[/yellow]")
        return

    # Normalize DataFrame for display
    # We rely on specific columns being present or we create them
    
    # Map 'model' to 'Model' but use Short Model for display values
    df["Model"] = df.get("Short Model", df.get("model", "Unknown"))
    
    # Calculate Cost/Case if not explicit
    # Logic: if 'mean_cost' exists use it, else calculate from total_cost / test_cases
    if "Cost/Case" not in df.columns:
        if "mean_cost" in df.columns:
            df["Cost/Case"] = df["mean_cost"]
        elif "total_cost" in df.columns and "test_cases" in df.columns:
            # handle potential non-numeric or zero division
            def _calc_cost(r):
                try:
                    tc = float(r["total_cost"])
                    n = float(r["test_cases"])
                    return tc / n if n > 0 else 0.0
                except (ValueError, TypeError):
                    return r.get("total_cost", 0.0) # Fallback
            df["Cost/Case"] = df.apply(_calc_cost, axis=1)
        elif "total_cost" in df.columns:
            # dwash format often puts total cost for the run, but reader puts it in 'total_cost'.
            # Without 'test_cases', we might just display total_cost as is, or 0.
            # But the table expects Cost/Case.
            df["Cost/Case"] = df["total_cost"]

    # Map other standard columns
    col_map = {
        "pass_rate_1": "Pass 1",
        "pass_rate_2": "Pass 2",
        "test_cases": "N",
        "edit_format": "Edit Format",
        "commit_hash": "Commit",
        "seconds_per_case": "Sec/Case"
    }
    
    for src, dst in col_map.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]

    # Handle Grouping
    if group_by:
        # If grouping, we aggregate numeric columns and first/unique for others
        # group_by is a list of column names
        valid_groups = [g for g in group_by if g in df.columns]
        if valid_groups:
            # Define aggregation rules
            # We want mean for pass rates and costs, sum for N?
            # Actually typically we want mean across the group for comparison.
            agg_rules = {
                "Pass 1": "mean",
                "Pass 2": "mean",
                "Cost/Case": "mean",
                "N": "sum", # Or mean? Usually N is sum of cases if splitting, or if repeated runs, maybe sum.
                            # But here we probably want mean metrics.
            }
            # Only use rules for columns that exist
            agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
            
            df = df.groupby(valid_groups, as_index=False).agg(agg_rules)

    # Prepare Table
    table = Table(title="Benchmark Results")

    # Determine columns to show
    # Standard columns
    std_cols = ["File", "Model", "Edit Format", "Commit", "N", "Pass 1", "Pass 2", "Cost/Case", "Sec/Case"]
    
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

    # Process group_by if needed for plot
    # The plotter expects data structured by run/file usually.
    # If grouping, we likely want to aggregate data across the groups.
    # For plotting, usually we want to see Models vs Pass Rates.
    # If group_by is set, we might be grouping by Model (aggregating runs) 
    # OR grouping by Run (aggregating models? unlikely).
    # The previous logic seemed to create one 'Aggregated' run containing the grouped results.
    
    if group_by:
        valid_groups = [g for g in group_by if g in df.columns]
        if valid_groups:
             # Aggregate numeric fields
             agg_rules = {
                "pass_rate_1": "mean",
                "pass_rate_2": "mean",
                "total_cost": "mean",
                # We need a model name for the plot
                "Short Model": "first" if "Short Model" not in valid_groups else None
             }
             # Only existing columns
             agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns and v is not None}
             
             df = df.groupby(valid_groups, as_index=False).agg(agg_rules)
             
             # If we grouped, we effectively have one "set" of results (one run)
             df["File"] = "Aggregated"
             
             # If the model name was part of the group, we might want to construct a composite name
             # if 'Short Model' wasn't preserved or is ambiguous.
             if "Short Model" not in df.columns:
                 # Construct name from groups
                 df["Short Model"] = df[valid_groups].apply(lambda x: " ".join(x.astype(str)), axis=1)

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
