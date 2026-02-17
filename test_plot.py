#!/usr/bin/env python3
"""Test the new CLI tool."""
import subprocess
import sys

def test_cli():
    """Test basic CLI functionality."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "catscraps.cli", "--help"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ CLI tool works")
            print(result.stdout[:200])
            return True
        else:
            print("✗ CLI tool failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_cli()
    sys.exit(0 if success else 1)
