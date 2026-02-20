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
from catscraps.reader import read_file, load_benchmarks
from catscraps.plotter import create_plot
from catscraps.grouper import group_and_aggregate
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
def main(
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
    Benchmark visualization tool.
    """
    configure_logging(verbose, quiet)


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
):
    """Display benchmark data in a table."""
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
        data = load_benchmarks(valid_files)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if group_by:
        data = group_and_aggregate(data, group_by)

    if not data:
        console.print("[yellow]No data found.[/yellow]")
        return

    table = Table(title="Benchmark Results")

    # Define columns to display, substituting Model for _Short Model
    raw_cols = list(data[0].keys())

    # Prioritize group_by columns if set, otherwise standard order
    ordered_cols = []
    if group_by:
        ordered_cols = [c for c in group_by if c in raw_cols]

    # Add standard columns if they aren't in group_by
    for std in ["File", "Model", "Edit Format", "Commit", "N"]:
        if std not in ordered_cols and std in raw_cols:
            ordered_cols.append(std)

    remaining = [c for c in raw_cols if c not in ordered_cols and not c.startswith("_")]
    display_cols = ordered_cols + remaining

    for col in display_cols:
        justify = "right"
        if col in ["File", "Model", "Edit Format", "Commit"]:
            justify = "left"

        style = "dim" if col == "File" else ("cyan" if col == "Model" else None)
        table.add_column(col, justify=justify, style=style)

    for row in data:
        formatted_row = []
        for col in display_cols:
            val = (
                row["_Short Model"]
                if col == "Model" and "_Short Model" in row
                else row[col]
            )

            if val is None:
                formatted_row.append("N/A")
            elif col.startswith("Pass"):
                formatted_row.append(f"{val:.1f}%")
            elif col == "Cost/Case":
                formatted_row.append(f"${val:.4f}")
            elif col == "Sec/Case":
                formatted_row.append(f"{val:.1f}")
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
):
    """
    Create a visualization of benchmark results.

    The first file determines the model order.
    """
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

    # Read all benchmark files
    benchmark_data_list = []

    if group_by:
        # Load all flattened data
        try:
            flat_data = load_benchmarks(all_files)
        except Exception as e:
            console.print(f"[red]Error loading benchmarks: {e}[/red]")
            raise typer.Exit(1)

        grouped_data = group_and_aggregate(flat_data, group_by)

        # Convert to single BenchmarkData object
        results = []
        for row in grouped_data:
            # Construct a display name from group keys
            name_parts = [str(row.get(g, "")) for g in group_by]
            m_name = " ".join(name_parts)

            p1 = row.get("Pass 1", 0.0) or 0.0
            p2 = row.get("Pass 2", 0.0) or 0.0
            cost = row.get("Cost/Case", 0.0) or 0.0

            results.append(
                ModelResult(name=m_name, pass_rates=[p1, p2], total_cost=cost)
            )

        if results:
            benchmark_data_list.append(
                BenchmarkData(run_name="Aggregated", results=results)
            )

    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading benchmark files...", total=len(all_files))

            for filepath in all_files:
                run_name = filepath.stem.replace("_", " ")
                if not filepath.exists():
                    console.print(f"[red]Error: File '{filepath}' not found[/red]")
                    raise typer.Exit(1)

                try:
                    benchmark_data = read_file(
                        str(filepath), run_name, format=input_format
                    )
                    benchmark_data_list.append(benchmark_data)
                    progress.update(task, advance=1, description=f"Read {filepath}")
                except Exception as e:
                    console.print(f"[red]Error reading {filepath}: {e}[/red]")
                    raise typer.Exit(1)

    # Create the plot
    with console.status("[bold green]Creating plot...") as status:
        try:
            create_plot(
                benchmark_data_list=benchmark_data_list,
                show_cost=show_cost,
                output_file=output,
                plot_type=plot_type,
            )
            console.print(f"[green]✓ Graph saved to {output}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating plot: {e}[/red]")
            raise typer.Exit(1)

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
def version():
    """Show version information."""
    console.print("Benchmark Plotter v0.1.0")


if __name__ == "__main__":
    app()
