This is the start of repo to collect results.

Ultimately we need a few thinsgs:

- respository for atomic level results (requirement cheap, open, append only)
- exchange format for both aggregate (summary counts), `test level summary`
  (results for every scenario), `full` (diffs and outcome for each scenario)
- standard definition of test metadata beyond ['model', 'coder hash',
  `scenerio/cat id`] we need to add [`settings`] (or hyperparameters) that
  influece (eg "diff format", "coder prompat", ?mcp config etc)

For now this is just a messy collection of results so far.

# Catscraps Benchmark Visualization

A tool for visualizing benchmark results in dwash20260217 format.

## Installation

```bash
uv pip install -e .
```

## Usage

### CLI Tool

```bash
# Basic usage with two files
plot-benchmark run1.txt run2.txt

# With options
plot-benchmark run1.txt run2.txt --auto-open --no-show-cost --output myplot.png

# Show help
plot-benchmark --help
```


## File Format

The current benchmark dwash20260217 format is deprecated:

```
=== openrouter-model-name ===
pass_rate_1: 0.123
pass_rate_2: 0.456
total_cost: 0.789
```

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```
