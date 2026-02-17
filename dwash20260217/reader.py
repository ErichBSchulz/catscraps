import re
from typing import List
from .models import BenchmarkData, ModelResult

def read_dwash20260217_file(filepath: str, run_name: str) -> BenchmarkData:
    """
    Read a dwash20260217 format file.
    
    Format:
    === openrouter-model-name ===
    pass_rate_1: 0.123
    pass_rate_2: 0.456
    total_cost: 0.789
    """
    pattern = re.compile(
        r"===\s+.*?openrouter-(.*?)\s+===\n\s+pass_rate_1:\s+([\d.]+)\n\s+pass_rate_2:\s+([\d.]+)\n\s+total_cost:\s+([\d.]+)"
    )
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    matches = pattern.findall(content)
    results = []
    
    for m in matches:
        name = m[0].replace("primary-variation-", "")
        result = ModelResult(
            name=name,
            pass_rate_1=float(m[1]),
            pass_rate_2=float(m[2]),
            total_cost=float(m[3])
        )
        results.append(result)
    
    return BenchmarkData(run_name=run_name, results=results)
