import re
import yaml
import logging
import pandas as pd
from typing import List, Dict, Any, Union
from pathlib import Path
from .models import BenchmarkData, ModelResult, BenchmarkRun, RunMetadata, RunOutcomes

logger = logging.getLogger(__name__)


def load_benchmarks(files: List[Path], query: str = None) -> pd.DataFrame:
    """
    Load benchmark data from multiple files into a unified pandas DataFrame.
    """
    all_rows = []

    for filepath in files:
        # Skip meta files if they are passed directly
        if filepath.name.endswith("_meta.yml"):
            continue

        file_rows = []
        if filepath.suffix in [".yml", ".yaml"]:
            # Classic format
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            # Handle dictionary of dictionaries format
            if isinstance(data, dict):
                # Convert to list of dictionaries, adding the key as a field
                converted_data = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Add the key as a field
                        entry = value.copy()
                        entry["key"] = key
                        converted_data.append(entry)
                    else:
                        # If value is not a dict, still add it as a field
                        entry = {"value": value, "key": key}
                        converted_data.append(entry)
                data = converted_data
            elif not isinstance(data, list):
                data = [data]

            for entry in data:
                entry["File"] = filepath.name
                file_rows.append(entry)
        else:
            # dwash format
            dwash_rows = _read_dwash20260217_file_raw(str(filepath))
            for r in dwash_rows:
                r["File"] = filepath.name
                file_rows.append(r)

        # Apply sidecar metadata *after* loading data
        meta_path = filepath.with_name(filepath.name + "_meta.yml")
        if meta_path.exists():
            with open(meta_path, "r") as f:
                sidecar_meta = yaml.safe_load(f) or {}

            for row in file_rows:
                for k, v in sidecar_meta.items():
                    row[k] = v

        # Process each row to handle avg_cost and avg_duration
        for row in file_rows:
            # Determine n from available fields
            n_val = None
            if 'n' in row:
                n_val = row['n']
            elif 'test_cases' in row:
                n_val = row['test_cases']
            elif 'total_tests' in row:
                n_val = row['total_tests']
            
            # Convert avg_cost to total_cost if present
            if 'avg_cost' in row:
                avg_cost = row['avg_cost']
                if n_val is not None:
                    try:
                        row['total_cost'] = float(avg_cost) * float(n_val)
                    except (ValueError, TypeError):
                        # If conversion fails, set to 0.0 and log a warning
                        logger.warning("Could not convert avg_cost %s or n %s to float", avg_cost, n_val)
                        row['total_cost'] = 0.0
                else:
                    logger.warning("avg_cost present but n not found in row, cannot compute total_cost")
                    row['total_cost'] = 0.0
                # Remove avg_cost to avoid confusion
                del row['avg_cost']
            
            # Map avg_duration to seconds_per_case if present
            if 'avg_duration' in row:
                row['seconds_per_case'] = row['avg_duration']
                del row['avg_duration']
            
            # Ensure n is set for later use
            if n_val is not None:
                row['n'] = n_val
        
        all_rows.extend(file_rows)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)

    # Standardize 'n' column if not present but 'test_cases' or 'total_tests' is
    if "n" not in df.columns:
        if "test_cases" in df.columns:
            df["n"] = df["test_cases"]
        elif "total_tests" in df.columns:
            df["n"] = df["total_tests"]

    # Apply shortname logic
    df = add_short_model_name(df)

    if query:
        initial_count = len(df)
        try:
            df = df.query(query)
            final_count = len(df)
            logger.info(
                "Query '%s' filtered records from %d to %d",
                query,
                initial_count,
                final_count,
            )
        except Exception as e:
            # We fail fast as per conventions
            raise ValueError(f"Invalid query string '{query}': {e}")

    return df


def add_short_model_name(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a 'Short Model' column based on specific logic."""
    if "model" not in df.columns:
        df["Short Model"] = "Unknown"
        return df

    def _get_short_name(name):
        if not isinstance(name, str):
            return str(name)

        if "/" in name:
            return name.split("/")[-1]
        elif len(name) > 10 and "-" in name:
            return "-".join(name.split("-")[1:])
        return name

    df["Short Model"] = df["model"].apply(_get_short_name)
    return df


def _read_dwash20260217_file_raw(filepath: str) -> List[Dict[str, Any]]:
    """
    Read a dwash20260217 format file into a list of dicts.
    """
    with open(filepath, "r") as f:
        content = f.read()

    # Split by model headers, capturing the model name
    parts = re.split(r"===\s+.*?openrouter-(.*?)\s+===", content)
    rows = []

    # parts[0] is preamble, then name, body, name, body...
    for i in range(1, len(parts), 2):
        name = parts[i].replace("primary-variation-", "").strip()
        body = parts[i + 1]

        # Extract all pass rates in order
        pass_rates = [float(m) for m in re.findall(r"pass_rate_\d+:\s+([\d.]+)", body)]

        # Extract total cost
        cost_match = re.search(r"total_cost:\s+([\d.]+)", body)
        cost = float(cost_match.group(1)) if cost_match else 0.0

        p1 = pass_rates[0] if len(pass_rates) > 0 else 0.0
        p2 = pass_rates[1] if len(pass_rates) > 1 else p1

        rows.append(
            {
                "model": name,
                "pass_rate_1": p1,
                "pass_rate_2": p2,
                "total_cost": cost,
                # We don't have other metrics in this format usually
            }
        )

    return rows


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
