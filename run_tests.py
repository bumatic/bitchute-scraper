#!/usr/bin/env python
"""
Test runner script for BitChute scraper
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED")
    else:
        print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run BitChute scraper tests')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'performance', 'quick'],
                        default='quick', help='Type of tests to run')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--failfast', '-x', action='store_true', help='Stop on first failure')
    parser.add_argument('--marker', '-m', help='Run tests matching given mark expression')
    parser.add_argument('--keyword', '-k', help='Run tests matching given keyword expression')
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ['pytest']
    
    if args.verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    if args.failfast:
        cmd.append('-x')
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(['--cov=bitchute', '--cov-report=term-missing', '--cov-report=html'])
    
    # Test type selection
    if args.type == 'all':
        cmd.append('tests/')
    elif args.type == 'unit':
        cmd.extend(['-m', 'unit', 'tests/'])
    elif args.type == 'integration':
        cmd.extend(['-m', 'integration', 'tests/'])
    elif args.type == 'performance':
        cmd.extend(['-m', 'performance', 'tests/'])
    elif args.type == 'quick':
        cmd.extend(['-m', 'not slow and not integration and not performance', 'tests/'])
    
    # Add custom marker if provided
    if args.marker:
        cmd.extend(['-m', args.marker])
    
    # Add keyword filter if provided
    if args.keyword:
        cmd.extend(['-k', args.keyword])
    
    print("🧪 BitChute Scraper Test Runner")
    print("=" * 60)
    
    # Run tests
    exit_code = run_command(cmd, f"Running {args.type} tests")
    
    # Run additional checks if all tests
    if args.type == 'all' and exit_code == 0:
        print("\n" + "="*60)
        print("🔍 Running additional checks...")
        print("="*60)
        
        # Run linting
        lint_code = run_command(['flake8', 'bitchute', 'tests'], "Linting")
        
        # Run type checking
        type_code = run_command(['mypy', 'bitchute', '--ignore-missing-imports'], "Type checking")
        
        # Summary
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print(f"Tests: {'PASSED' if exit_code == 0 else 'FAILED'}")
        print(f"Linting: {'PASSED' if lint_code == 0 else 'FAILED'}")
        print(f"Type checking: {'PASSED' if type_code == 0 else 'FAILED'}")
        
        # Overall result
        overall = exit_code + lint_code + type_code
        if overall == 0:
            print("\n✅ All checks passed!")
        else:
            print(f"\n❌ Some checks failed (failures: {overall})")
        
        return overall
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())