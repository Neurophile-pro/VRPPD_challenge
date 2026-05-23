#!/bin/bash
# Setup and run SCIP solver for VRPPD

set -e

echo "========================================"
echo "SCIP Solver Setup for VRPPD"
echo "========================================"

# Activate conda environment
echo "Activating conda environment: VRPPD"
conda activate VRPPD

# Check if pyscipopt is installed
echo "Checking for pyscipopt installation..."
if python -c "import pyscipopt" 2>/dev/null; then
    echo "✓ pyscipopt is already installed"
else
    echo "✗ pyscipopt not found, installing..."
    pip install pyscipopt
fi

# Navigate to project directory
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "Installation complete!"
echo "========================================"
echo ""
echo "To run the SCIP solver, use:"
echo "  python main_scip.py <path_to_instances>"
echo ""
echo "Example:"
echo "  python main_scip.py ./data/instances/"
echo ""
