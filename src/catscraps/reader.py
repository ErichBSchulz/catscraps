import re
from typing import List
from .models import BenchmarkData, ModelResult


def read_file(filepath: str, run_name: str, format: str) -> BenchmarkData:
    """Read a benchmark file in the specified format."""
    if format == "dwash20260217":
        return _read_dwash20260217_file(filepath, run_name)
    else:
        raise ValueError(f"Unknown format: {format}")


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
        pass_rates = [
            float(m) for m in re.findall(r"pass_rate_\d+:\s+([\d.]+)", body)
        ]

        # Extract total cost
        cost_match = re.search(r"total_cost:\s+([\d.]+)", body)
        cost = float(cost_match.group(1)) if cost_match else 0.0

        if pass_rates:
            results.append(
                ModelResult(name=name, pass_rates=pass_rates, total_cost=cost)
            )

    return BenchmarkData(run_name=run_name, results=results)
