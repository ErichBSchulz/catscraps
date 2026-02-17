#!/usr/bin/env python3
"""
Legacy wrapper for the new CLI tool.
This file is kept for backward compatibility.
"""

import sys
import subprocess
import os


def main():
    """Run the new CLI tool with default arguments."""
    # Default to run1.txt and run2.txt if no arguments provided
    files = ["run1.txt", "run2.txt"]

    # Check if files exist
    import os

    existing_files = [f for f in files if os.path.exists(f)]

    if not existing_files:
        print("Error: No benchmark files found.")
        print(
            "Please provide files as arguments or ensure run1.txt and run2.txt exist."
        )
        sys.exit(1)

    # Build command for the new CLI
    cmd = [sys.executable, "-m", "catscraps.cli", "plot"] + existing_files

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: New CLI tool not found. Please install the package properly.")
        sys.exit(1)


if __name__ == "__main__":
    main()
