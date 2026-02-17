"""Test the CLI tool."""

import pytest
import subprocess
import sys
import tempfile
import os
from pathlib import Path


def test_cli_help():
    """Test that CLI help works."""
    result = subprocess.run(
        [sys.executable, "-m", "catscraps.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_cli_version():
    """Test version command."""
    result = subprocess.run(
        [sys.executable, "-m", "catscraps.cli", "version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Benchmark Plotter" in result.stdout


def test_plot_command_with_mock_files():
    """Test plot command with mock benchmark files."""
    # Create temporary directory with mock files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock run1.txt
        run1_content = """=== openrouter-model-a ===
pass_rate_1: 0.5
pass_rate_2: 0.8
total_cost: 0.1234
=== openrouter-model-b ===
pass_rate_1: 0.3
pass_rate_2: 0.6
total_cost: 0.5678
"""
        run1_path = Path(tmpdir) / "run1.txt"
        run1_path.write_text(run1_content)

        # Create mock run2.txt
        run2_content = """=== openrouter-model-a ===
pass_rate_1: 0.6
pass_rate_2: 0.9
total_cost: 0.2345
=== openrouter-model-b ===
pass_rate_1: 0.4
pass_rate_2: 0.7
total_cost: 0.6789
"""
        run2_path = Path(tmpdir) / "run2.txt"
        run2_path.write_text(run2_content)

        output_path = Path(tmpdir) / "output.png"

        # Run plot command
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "catscraps.cli",
                "plot",
                str(run1_path),
                str(run2_path),
                "--output",
                str(output_path),
                "--no-show-cost",
            ],
            capture_output=True,
            text=True,
        )

        # Check command succeeded
        assert result.returncode == 0
        # Check output file was created
        assert output_path.exists()
        # Check success message
        assert "Graph saved to" in result.stdout


def test_plot_command_missing_file():
    """Test plot command with missing file."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "catscraps.cli",
            "plot",
            "nonexistent.txt",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Error" in result.stderr or "Error" in result.stdout


def test_reader_module():
    """Test the reader module directly."""
    from dwash20260217.reader import read_dwash20260217_file
    from dwash20260217.models import BenchmarkData, ModelResult

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(
            """=== openrouter-test-model ===
pass_rate_1: 0.75
pass_rate_2: 0.95
total_cost: 1.2345
"""
        )
        f.flush()
        f.close()

        try:
            data = read_dwash20260217_file(f.name, "Test Run")
            assert isinstance(data, BenchmarkData)
            assert data.run_name == "Test Run"
            assert len(data.results) == 1
            result = data.results[0]
            assert isinstance(result, ModelResult)
            assert result.name == "test-model"
            assert result.pass_rate_1 == 0.75
            assert result.pass_rate_2 == 0.95
            assert result.total_cost == 1.2345
        finally:
            os.unlink(f.name)


def test_models():
    """Test model classes."""
    from dwash20260217.models import ModelResult, BenchmarkData

    mr = ModelResult(name="test", pass_rate_1=0.1, pass_rate_2=0.2, total_cost=0.3)
    assert mr.name == "test"
    assert mr.pass_rate_1 == 0.1
    assert mr.pass_rate_2 == 0.2
    assert mr.total_cost == 0.3

    bd = BenchmarkData(run_name="run1", results=[mr])
    assert bd.run_name == "run1"
    assert bd.get_model_names() == ["test"]
    assert bd.get_model_result("test") == mr

    with pytest.raises(KeyError):
        bd.get_model_result("nonexistent")
