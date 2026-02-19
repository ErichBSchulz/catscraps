import re
import yaml
from typing import List, Dict, Any
from pathlib import Path
from .models import BenchmarkData, ModelResult, BenchmarkRun, RunMetadata, RunOutcomes


def read_file(filepath: str, run_name: str, format: str) -> BenchmarkData:
    """Read a benchmark file in the specified format."""
    if format == "dwash20260217":
        return _read_dwash20260217_file(filepath, run_name)
    elif format == "classic":
        # For legacy compatibility, we read the classic file but convert
        # the first entry to BenchmarkData for the plotter.
        # This is a stop-gap until the plotter uses the new models.
        runs = read_classic_file(filepath)
        if not runs:
            raise ValueError("No data found in file")

        # Convert first run to old format for plotting compatibility
        # This assumes one run per file for the plotter, or we take the first one
        run = runs[0]
        return BenchmarkData(
            run_name=run.metadata.model,  # Use model name as run name
            results=[
                ModelResult(
                    name=run.metadata.model,
                    pass_rates=[run.outcomes.pass_rate_1, run.outcomes.pass_rate_2],
                    total_cost=run.outcomes.total_cost,
                )
            ],
        )
    else:
        raise ValueError(f"Unknown format: {format}")


def read_classic_file(filepath: str) -> List[BenchmarkRun]:
    """Read a classic (YAML list) format file."""
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        data = [data]

    runs = []
    for entry in data:
        # Split entry into metadata and outcomes based on known fields
        # This is a bit manual but ensures strict separation

        # Filter keys for Metadata
        meta_keys = RunMetadata.model_fields.keys()
        meta_data = {k: v for k, v in entry.items() if k in meta_keys}

        # Filter keys for Outcomes
        outcome_keys = RunOutcomes.model_fields.keys()
        outcome_data = {k: v for k, v in entry.items() if k in outcome_keys}

        # Ensure total_tests is present if test_cases is there (alias)
        if "total_tests" not in outcome_data and "test_cases" in meta_data:
            outcome_data["total_tests"] = meta_data["test_cases"]

        try:
            metadata = RunMetadata(**meta_data)
            outcomes = RunOutcomes(**outcome_data)
            runs.append(BenchmarkRun(metadata=metadata, outcomes=outcomes))
        except Exception as e:
            # Fail fast as requested
            raise ValueError(f"Failed to parse run entry: {e}")

    return runs


def _read_dwash20260217_file(filepath: str, run_name: str) -> BenchmarkData:
    """
    Read a dwash20260217 format file.

    Format:
    === openrouter-model-name ===
    pass_rate_1: 0.123
    pass_rate_2: 0.456
    total_cost: 0.789
    """
    with open(filepath, "r") as f:
        content = f.read()

    # Split by model headers, capturing the model name
    parts = re.split(r"===\s+.*?openrouter-(.*?)\s+===", content)
    results = []

    # parts[0] is preamble, then name, body, name, body...
    for i in range(1, len(parts), 2):
        name = parts[i].replace("primary-variation-", "").strip()
        body = parts[i + 1]

        # Extract all pass rates in order
        pass_rates = [float(m) for m in re.findall(r"pass_rate_\d+:\s+([\d.]+)", body)]

        # Extract total cost
        cost_match = re.search(r"total_cost:\s+([\d.]+)", body)
        cost = float(cost_match.group(1)) if cost_match else 0.0

        if pass_rates:
            results.append(
                ModelResult(name=name, pass_rates=pass_rates, total_cost=cost)
            )

    return BenchmarkData(run_name=run_name, results=results)
