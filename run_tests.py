#!/usr/bin/env python
"""
Test runner script for Hawaii Appleseed Dashboard.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    """Run tests for the Hawaii Appleseed Dashboard."""
    parser = argparse.ArgumentParser(description="Run tests for Hawaii Appleseed Dashboard")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    args = parser.parse_args()
    
    # Set default if no specific test type is specified
    if not (args.unit or args.integration):
        args.all = True
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])
    
    # Add test selection
    if args.all:
        cmd.append("tests/")
    else:
        if args.unit:
            cmd.append("tests/unit/")
        if args.integration:
            cmd.append("tests/integration/")
    
    # Run the tests
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    # Return exit code
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
