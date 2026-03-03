import fnmatch
from typing import List, Tuple


def expand_column_globs(df_columns: List[str], column_patterns: List[str]) -> List[str]:
    """
    Expand glob patterns against available DataFrame columns.

    Args:
        df_columns: List of column names in the DataFrame
        column_patterns: List of column names or glob patterns

    Returns:
        List of matched column names
    """
    expanded = []
    for pattern in column_patterns:
        # If pattern contains wildcards, expand it
        if "*" in pattern or "?" in pattern or "[" in pattern:
            matches = fnmatch.filter(df_columns, pattern)
            if not matches:
                # Keep the pattern as-is if no matches, will be caught by validation
                expanded.append(pattern)
            else:
                expanded.extend(matches)
        else:
            # Exact column name
            expanded.append(pattern)

    # Remove duplicates while preserving order
    seen = set()
    unique_expanded = []
    for col in expanded:
        if col not in seen:
            seen.add(col)
            unique_expanded.append(col)

    return unique_expanded


def validate_columns_exist(
    df_columns: List[str], requested_columns: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Validate which requested columns exist in the DataFrame.

    Args:
        df_columns: List of column names in the DataFrame
        requested_columns: List of column names to check

    Returns:
        Tuple of (existing_columns, missing_columns)
    """
    existing = []
    missing = []

    for col in requested_columns:
        if col in df_columns:
            existing.append(col)
        else:
            missing.append(col)

    return existing, missing
