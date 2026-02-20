import re
import yaml
import logging
from typing import List, Dict, Any, Union
from pathlib import Path
from .models import BenchmarkData, ModelResult, BenchmarkRun, RunMetadata, RunOutcomes

logger = logging.getLogger(__name__)


def load_benchmarks(files: List[Path]) -> List[Dict[str, Any]]:
    """
    Load benchmark data from multiple files into a unified list of dictionaries.
    """
    all_data = []

    for filepath in files:
        # Skip meta files if they are passed directly
        if filepath.name.endswith("_meta.yml"):
            continue

        if filepath.suffix in [".yml", ".yaml"]:
            runs = _read_classic_file(str(filepath))
            for run in runs:
                row = {
                    "File": filepath.name,
                    "Model": run.metadata.model,
                    "_Short Model": run.metadata.short_name,
                    "Pass 1": run.outcomes.pass_rate_1,
                    "Pass 2": run.outcomes.pass_rate_2,
                    "Cost/Case": run.outcomes.mean_cost,
                    "Tok/Case": int(
                        run.outcomes.mean_prompt_tokens
                        + run.outcomes.mean_completion_tokens
                    ),
                    "Sec/Case": run.outcomes.seconds_per_case,
                    "Edit Format": run.metadata.edit_format,
                    "Commit": run.metadata.commit_hash,
                    "N": run.metadata.test_cases,
                }
                all_data.append(row)
        else:
            # dwash format
            run_name = filepath.stem.replace("_", " ")
            bd = _read_dwash20260217_file(str(filepath), run_name)

            # Look for sidecar metadata
            meta_path = filepath.with_name(filepath.name + "_meta.yml")
            meta_dict = {}
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    meta_dict = yaml.safe_load(f) or {}

            for res in bd.results:
                p1 = res.pass_rates[0] if len(res.pass_rates) > 0 else 0.0
                p2 = res.pass_rates[1] if len(res.pass_rates) > 1 else p1
                short_name = res.name.split("/")[-1] if "/" in res.name else res.name
                row = {
                    "File": filepath.name,
                    "Model": res.name,
                    "_Short Model": short_name,
                    "Pass 1": p1,
                    "Pass 2": p2,
                    "Cost/Case": res.total_cost,
                    "Tok/Case": None,
                    "Sec/Case": None,
                    "Edit Format": meta_dict.get("edit_format", "N/A"),
                    "Commit": meta_dict.get("commit_hash", "N/A"),
                    "N": meta_dict.get("test_cases", "N/A"),
                }
                all_data.append(row)

    return all_data


def read_file(filepath: str, run_name: str, format: str) -> BenchmarkData:
    """Read a benchmark file in the specified format."""
    if format == "dwash20260217":
        return _read_dwash20260217_file(filepath, run_name)
    elif format == "classic":
        # For legacy compatibility, we read the classic file but convert
        # the first entry to BenchmarkData for the plotter.
        # This is a stop-gap until the plotter uses the new models.
        runs = _read_classic_file(filepath)
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


def _read_classic_file(filepath: str) -> List[BenchmarkRun]:
    """Read a classic (YAML list) format file."""
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        data = [data]

    # Look for sidecar metadata
    path_obj = Path(filepath)
    meta_path = path_obj.with_name(path_obj.name + "_meta.yml")
    sidecar_meta = {}
    if meta_path.exists():
        with open(meta_path, "r") as f:
            sidecar_meta = yaml.safe_load(f) or {}

    runs = []
    for entry in data:
        # Apply sidecar overrides to the raw entry dictionary before validation
        for key, value in sidecar_meta.items():
            if key in entry and entry[key] != value:
                logger.debug("Overwriting %s in %s", key, filepath)
            entry[key] = value

        # Split entry into metadata and outcomes based on known fields
        # This is a bit manual but ensures strict separation

        # Filter keys for Metadata
        meta_keys = RunMetadata.model_fields.keys()
        meta_data = {k: v for k, v in entry.items() if k in meta_keys}

        # Filter keys for Outcomes
        outcome_keys = RunOutcomes.model_fields.keys()
        outcome_data = {k: v for k, v in entry.items() if k in outcome_keys}

        # Validation: Check for consistency between test_cases and total_tests
        test_cases = meta_data.get("test_cases")
        total_tests = outcome_data.get("total_tests")

        if test_cases is None and total_tests is None:
            raise ValueError("Neither 'test_cases' nor 'total_tests' found in data.")

        if test_cases is not None and total_tests is not None:
            if test_cases != total_tests:
                raise ValueError(
                    f"Inconsistent test counts: test_cases={test_cases}, total_tests={total_tests}"
                )

        # Ensure total_tests is populated for RunOutcomes
        if total_tests is None:
            outcome_data["total_tests"] = test_cases

        # Ensure test_cases is populated for RunMetadata
        if test_cases is None:
            meta_data["test_cases"] = total_tests

        # Fallback for date from directory name if missing
        if "date" not in meta_data or not meta_data["date"]:
            # Try to find a date-like string (YYYYMMDD or YYYY-MM-DD) in the path
            # The user example: data/dwash/20260217/hashline-more.yml
            path_parts = Path(filepath).parts
            for part in reversed(path_parts):
                if re.match(r"20\d{2}[-]?\d{2}[-]?\d{2}", part):
                    meta_data["date"] = part
                    break

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
