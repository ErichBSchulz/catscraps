import logging
from typing import List, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


def group_and_aggregate(
    data: List[Dict[str, Any]], group_by: List[str]
) -> List[Dict[str, Any]]:
    """
    Groups data by specified fields and calculates weighted averages for metrics.
    Weights are based on 'N' (test cases).
    """
    if not data:
        return []

    grouped = defaultdict(list)

    for row in data:
        # Create a tuple key for grouping
        key = tuple(str(row.get(k, "N/A")) for k in group_by)
        grouped[key].append(row)

    results = []

    # Metrics to aggregate (Metric Name, Weight Field)
    metrics = [
        ("Pass 1", "N"),
        ("Pass 2", "N"),
        ("Cost/Case", "N"),
        ("Tok/Case", "N"),
        ("Sec/Case", "N"),
    ]

    for key_tuple, rows in grouped.items():
        # Reconstruct the grouping keys
        new_row = dict(zip(group_by, key_tuple))

        # Aggregate metrics
        for metric, weight_field in metrics:
            weighted_sum = 0.0
            total_weight = 0.0
            valid_count = 0

            for r in rows:
                val = r.get(metric)
                weight = r.get(weight_field)

                if val is None:
                    continue

                # If N is missing/None, treat as 1.0 weight for the average
                if weight is None or weight == "N/A":
                    weight = 1.0

                try:
                    val = float(val)
                    weight = float(weight)
                    weighted_sum += val * weight
                    total_weight += weight
                    valid_count += 1
                except (ValueError, TypeError):
                    continue

            if valid_count > 0 and total_weight > 0:
                new_row[metric] = weighted_sum / total_weight
            else:
                new_row[metric] = None

        # Determine _Short Model if Model is in group_by for table display
        if "Model" in new_row:
            import re

            new_row["_Short Model"] = re.sub(r"^[^/-]+[/-]", "", new_row["Model"])

        results.append(new_row)

    return results
