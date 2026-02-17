import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import subprocess
import sys
import os
from pathlib import Path

from catscraps.reader import read_file
from catscraps.plotter import create_plot

app = typer.Typer(help="Benchmark visualization tool")
console = Console()


@app.command()
def plot(
    files: list[str] = typer.Argument(..., help="List of benchmark files to plot"),
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
    if not files:
        console.print("[red]Error: At least one file must be provided[/red]")
        raise typer.Exit(1)

    # Read all benchmark files
    benchmark_data_list = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Reading benchmark files...", total=len(files))

        for i, filepath in enumerate(files):
            run_name = f"Run {i+1}"
            if not Path(filepath).exists():
                console.print(f"[red]Error: File '{filepath}' not found[/red]")
                raise typer.Exit(1)

            try:
                benchmark_data = read_file(filepath, run_name, format=input_format)
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
