#!/usr/bin/env python3
"""
Test runner script for BitChute API scraper
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run all tests with coverage"""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print("❌ Tests directory not found!")
        return 1
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",
        "--cov=bitchute",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ]
    
    print("🧪 Running tests with coverage...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/")
    else:
        print("❌ Some tests failed!")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
