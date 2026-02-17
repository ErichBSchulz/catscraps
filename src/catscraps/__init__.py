"""Catscraps benchmark visualization package."""

from .models import BenchmarkData, ModelResult
from .reader import read_file
from .plotter import create_plot

__all__ = ["BenchmarkData", "ModelResult", "read_file", "create_plot"]

__version__ = "0.1.0"
