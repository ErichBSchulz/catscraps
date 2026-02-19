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
from catscraps.reader import read_file, read_classic_file
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

    logger.info("Processing %d file(s)", len(files))
    for f in files:
        logger.debug("Queueing file: %s (format: classic)", f)

    table = Table(title="Benchmark Results")

    # Add columns
    table.add_column("Model", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Pass 1", justify="right")
    table.add_column("Pass 2", justify="right")
    table.add_column("Cost/Case", justify="right")
    table.add_column("Tok/Case", justify="right")
    table.add_column("Sec/Case", justify="right")

    for filepath in files:
        if not filepath.exists():
            console.print(f"[red]Error: File '{filepath}' not found[/red]")
            continue

        try:
            # Currently assuming classic format for table view as it has the rich metadata
            runs = read_classic_file(str(filepath))
            for run in runs:
                m = run.metadata
                o = run.outcomes

                table.add_row(
                    m.model,
                    str(m.date),
                    f"{o.pass_rate_1:.1f}%",
                    f"{o.pass_rate_2:.1f}%",
                    f"${o.mean_cost:.4f}",
                    f"{int(o.mean_prompt_tokens + o.mean_completion_tokens)}",
                    f"{o.seconds_per_case:.1f}",
                )
        except Exception as e:
            console.print(f"[red]Error reading {filepath}: {e}[/red]")
            # Fail fast? Or continue for other files?
            # User guideline says fail fast unless explicitly told to catch.
            # But here we are iterating user inputs. I'll throw.
            raise typer.Exit(1)

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
