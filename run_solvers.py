#!/usr/bin/env python
"""
Comparison and execution script for Xpress vs SCIP solvers

This script allows you to:
1. Compare the features of both solvers
2. Run either solver
3. Compare results
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path

def compare_solvers():
    """Display comparison between solvers"""
    comparison = """
╔════════════════════════════════════════════════════════════════════════╗
║         VRP Solver Comparison: Xpress vs SCIP                         ║
╚════════════════════════════════════════════════════════════════════════╝

┌─ SOLVER PROPERTIES ─────────────────────────────────────────────────────┐
│                     Xpress          │ SCIP
├────────────────────────────────────┼──────────────────────────────────┤
│ License Type          Proprietary    │ Open-source (Apache 2.0)
│ Performance           Very fast      │ Fast
│ Commercial Support    Available      │ Community-driven
│ Installation          xpauth.xpr     │ pip install pyscipopt
│ Indicator Constraints Yes            │ No (uses big-M)
│ Python API Support    Excellent      │ Excellent
└────────────────────────────────────┴──────────────────────────────────┘

┌─ IMPLEMENTATION FILES ──────────────────────────────────────────────────┐
│
│ Xpress Version:
│   - main.py                (relies on xpauth.xpr license)
│   - src/mip.py             (uses xp.problem(), xp.binary, etc.)
│
│ SCIP Version:
│   - main_scip.py           (open-source alternative)
│   - src/mip_scip.py        (uses Model(), addVar(), addCons())
│
│ Shared:
│   - src/one_pass.py        (heuristic - same for both)
│   - src/read_data.py       (data loading - same for both)
│   - src/data_models/       (data structures - same for both)
│
└────────────────────────────────────────────────────────────────────────┘

┌─ SOLUTION FILES ───────────────────────────────────────────────────────┐
│ Xpress writes to:  solutions/<instance_name>.csv
│ SCIP writes to:    solutions/<instance_name>_scip.csv
│
│ This allows running both solvers and comparing results side-by-side
└────────────────────────────────────────────────────────────────────────┘
    """
    print(comparison)

def run_xpress(instances_path):
    """Run xpress solver"""
    print("\n" + "="*70)
    print("Running Xpress Solver (requires xpauth.xpr license)")
    print("="*70)
    
    cmd = [sys.executable, "main.py", instances_path]
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ Xpress solver completed")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Xpress solver failed: {e}")
        return False
    return True

def run_scip(instances_path):
    """Run SCIP solver"""
    print("\n" + "="*70)
    print("Running SCIP Solver (open-source, no license needed)")
    print("="*70)
    
    # First check if pyscipopt is installed
    try:
        import pyscipopt
        print("✓ pyscipopt is available\n")
    except ImportError:
        print("✗ pyscipopt not installed")
        print("  Install with: pip install pyscipopt\n")
        return False
    
    cmd = [sys.executable, "main_scip.py", instances_path]
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ SCIP solver completed")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ SCIP solver failed: {e}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Run and compare VRP solvers (Xpress vs SCIP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_solvers.py --compare              # Show comparison
  python run_solvers.py --scip ./data/         # Run SCIP solver
  python run_solvers.py --xpress ./data/       # Run Xpress solver
  python run_solvers.py --both ./data/         # Run both solvers
        """
    )
    
    parser.add_argument('--compare', action='store_true',
                       help='Show solver comparison')
    parser.add_argument('--scip', metavar='PATH',
                       help='Run SCIP solver on instances at PATH')
    parser.add_argument('--xpress', metavar='PATH',
                       help='Run Xpress solver on instances at PATH')
    parser.add_argument('--both', metavar='PATH',
                       help='Run both solvers on instances at PATH')
    
    args = parser.parse_args()
    
    if not any([args.compare, args.scip, args.xpress, args.both]):
        parser.print_help()
        sys.exit(1)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Show comparison
    if args.compare:
        compare_solvers()
        return
    
    # Run solvers
    if args.both:
        run_xpress(args.both)
        run_scip(args.both)
    elif args.xpress:
        run_xpress(args.xpress)
    elif args.scip:
        run_scip(args.scip)

if __name__ == "__main__":
    main()
