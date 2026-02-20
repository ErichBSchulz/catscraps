# Catscraps Benchmark Visualization

A tool for visualizing and analyzing benchmark results.

## Data & Contributions

**We want your data!**

Please see [data/README.md](data/README.md) for instructions
on how to structure and submit your benchmark results. We
encourage Pull Requests with new data to help build a
comprehensive view of model performance.

## Features

- **Multi-format Support**: Loads data from different YAML
  formats.
- **Flexible Loading**: Accepts multiple files or globs
  (handled by your shell).
- **Data Analysis**:
  - **Filtering**: Use standard pandas query strings via
    `--query` to include/exclude specific records.
  - **Grouping**: Aggregate results by fields like Model,
    Edit Format, or Commit using `--group-by`.
- **Visualization**:
  - **Table**: tabular view with confidence intervals.
  - **Plot**: Generate comparison plots (Pass Rate vs Cost,
    etc).
  - **Info**: Inspect the structure and schema of your
    loaded dataset.

## Installation

```bash
uv pip install -e .
```

## Usage

The tool provides several subcommands. Use `--help` on any
command for details.

### 1. Inspect Data Structure

See what columns and data types are available in your files:

```bash
catscraps info data/*.yml
```

### 2. Tabulate Results

View a text table of results. You can filter specific models
and group repeats:

```bash
# Basic table
catscraps table data/dwash/20260217/*.txt

# Filter and group
catscraps table data/**/*.yml --query "model.str.contains('claude')" --group-by default
```

### 3. Plotting

Generate visualizations comparing models or runs.

```bash
# Compare runs
catscraps plot run1.txt run2.txt --output comparison.png

# complex plot with filtering
catscraps plot data/**/*.yml \
    --query "total_cost < 5.0" \
    --group-by "model,edit_format" \
    --auto-open
```

## Architecture

The application loads disparate file formats into a unified
Pandas DataFrame.

1. **Reader**: Parses `dwash` text blocks and `classic` YAML
   lists into normalized records.
2. **Models**: Pydantic models enforce schema consistency
   for metadata and outcomes.
3. **Processing**: Pandas is used for querying, grouping,
   and aggregation.
4. **Output**: Rich text tables or Matplotlib charts.

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```
