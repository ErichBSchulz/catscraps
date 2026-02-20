from typing import List, Optional, Any
from pydantic import BaseModel, Field, computed_field


class RunMetadata(BaseModel):
    """Metadata describing the benchmark execution context."""

    results_dir: str
    test_cases: int
    model: str
    edit_format: str
    commit_hash: str
    map_tokens: Optional[int] = None
    command: Optional[str] = None
    date: Optional[Any] = None
    versions: Optional[str] = None

    @computed_field
    def short_name(self) -> str:
        # trim the first word and hyphen/slash
        # e.g. openrouter/foo -> foo
        # e.g. openrouter-foo -> foo
        import logging

        logger = logging.getLogger(__name__)

        if "/" in self.model:
            result = self.model.split("/")[-1]
            logger.debug("short_name slash trim: '%s' -> '%s'", self.model, result)
            return result

        import re

        result = re.sub(r"^[^/-]+[/-]", "", self.model)
        logger.debug("short_name regex trim: '%s' -> '%s'", self.model, result)
        return result


class RunOutcomes(BaseModel):
    """Outcomes and metrics from the benchmark."""

    # Primary
    pass_rate_1: float
    pass_rate_2: float
    seconds_per_case: float

    # Totals to be converted to means or kept as totals
    total_cost: float
    completion_tokens: int
    prompt_tokens: int

    # Secondary / Counts
    percent_cases_well_formed: float
    error_outputs: int = 0
    num_malformed_responses: int = 0
    num_with_malformed_responses: int = 0
    user_asks: int = 0
    lazy_comments: int = 0
    syntax_errors: int = 0
    indentation_errors: int = 0
    exhausted_context_windows: int = 0
    test_timeouts: int = 0
    total_tests: int
    pass_num_1: int
    pass_num_2: int

    @computed_field
    def short_name(self) -> str:
        # trim the first word and hyphen/slash
        # e.g. openrouter/foo -> foo
        # e.g. openrouter-foo -> foo
        import logging

        logger = logging.getLogger(__name__)

        if "/" in self.model:
            result = self.model.split("/")[-1]
            logger.debug("short_name slash trim: '%s' -> '%s'", self.model, result)
            return result

        import re

        result = re.sub(r"^[^/-]+[/-]", "", self.model)
        logger.debug("short_name regex trim: '%s' -> '%s'", self.model, result)
        return result

    @computed_field
    def mean_cost(self) -> float:
        return self.total_cost / self.total_tests

    @computed_field
    def mean_completion_tokens(self) -> float:
        return self.completion_tokens / self.total_tests

    @computed_field
    def mean_prompt_tokens(self) -> float:
        return self.prompt_tokens / self.total_tests

    @computed_field
    def count_well_formed(self) -> int:
        return int((self.percent_cases_well_formed / 100.0) * self.total_tests)


class BenchmarkRun(BaseModel):
    """Complete record of a single benchmark run."""

    metadata: RunMetadata
    outcomes: RunOutcomes


# Legacy models support for existing plotter
class ModelResult(BaseModel):
    """Data for a single model from a single run."""

    name: str
    pass_rates: List[float]
    total_cost: float


class BenchmarkData(BaseModel):
    """Collection of model results from a single run."""

    run_name: str
    results: List[ModelResult]

    def get_model_names(self) -> List[str]:
        return [r.name for r in self.results]

    def get_model_result(self, model_name: str) -> ModelResult:
        for r in self.results:
            if r.name == model_name:
                return r
        raise KeyError(f"Model {model_name} not found in {self.run_name}")
