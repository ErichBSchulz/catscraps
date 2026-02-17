from dataclasses import dataclass
from typing import List

@dataclass
class ModelResult:
    """Data for a single model from a single run."""
    name: str
    pass_rate_1: float
    pass_rate_2: float
    total_cost: float

@dataclass
class BenchmarkData:
    """Collection of model results from multiple runs."""
    run_name: str
    results: List[ModelResult]
    
    def get_model_names(self) -> List[str]:
        return [r.name for r in self.results]
    
    def get_model_result(self, model_name: str) -> ModelResult:
        for r in self.results:
            if r.name == model_name:
                return r
        raise KeyError(f"Model {model_name} not found in {self.run_name}")
