#!/usr/bin/env python3
"""
Run Brahma Echo smoke tests.
Usage: python run_smoke_tests.py
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

def run():
    test_file = ROOT / "ui_modern" / "smoke_test.py"
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return 1

    # Run the smoke test
    result = subprocess.run([sys.executable, str(test_file)], cwd=ROOT)
    return result.returncode

if __name__ == "__main__":
    sys.exit(run())