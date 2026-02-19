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
        df = load_benchmarks(valid_files)
    except Exception as e:
        console.print(f"[red]Error loading benchmarks: {e}[/red]")
        raise typer.Exit(1)

    if df.empty:
        console.print("[yellow]No data found.[/yellow]")
        return

    table = Table(title="Benchmark Results")

    # Define columns to display (exclude internal columns starting with _)
    display_cols = [c for c in df.columns if not c.startswith("_")]

    for col in display_cols:
        justify = "right" if col not in ["File", "Model"] else "left"
        style = "dim" if col == "File" else ("cyan" if col == "Model" else None)
        table.add_column(col, justify=justify, style=style)

    for _, row in df.iterrows():
        table.add_row(*[str(row[c]) for c in display_cols])

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
                benchmark_data = read_file(str(filepath), run_name, format=input_format)
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
