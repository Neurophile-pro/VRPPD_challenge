# SCIP Solver Implementation for VRPPD

This directory contains SCIP-based versions of the VRP with Pickup and Delivery solving scripts.

## Files Created

### New Scripts:
- **main_scip.py**: Main entry point using SCIP solver (equivalent to main.py but using SCIP)
- **src/mip_scip.py**: RoutingMIPSolverSCIP class implementing the MIP model using SCIP

### Differences from Xpress Version:
1. **Solver**: Uses SCIP (pyscipopt) instead of xpress
2. **Output files**: Solutions are saved with "_scip" suffix (e.g., `instance_name_scip.csv`)
3. **Internal formulation**: Uses big-M constraints instead of indicator constraints (SCIP doesn't have native indicator constraints)
4. **Logging**: Prints solution edge information for debugging

## Requirements

The SCIP solver requires:
```bash
pip install pyscipopt
```

Or if using conda:
```bash
conda install -c conda-forge pyscipopt
```

## Running

### Step 1: Activate conda environment
```bash
conda activate VRPPD
```

### Step 2: Run the SCIP solver
```bash
python main_scip.py <path_to_instances_folder>
```

Example:
```bash
python main_scip.py ./VRPPD_challenge/
```

### Step 3: Check results
Solutions will be saved in the `solutions/` directory with `_scip` suffix.

## Comparison Notes

- Both main.py (xpress) and main_scip.py use the same one-pass heuristic initially
- MIP model structure is equivalent between xpress and SCIP versions
- SCIP may have different performance characteristics and solution quality compared to xpress
- Solution files are saved separately with different suffixes for easy comparison

## Parameters

Both solvers use:
- Time limit: 60 seconds per instance
- Same constraints and objective function
- Same data models (Courier, Delivery)

## Troubleshooting

If pyscipopt is not available:
1. Ensure you're in the VRPPD conda environment
2. Check if SCIP is installed: `python -c "import pyscipopt"`
3. Install if missing: `pip install pyscipopt`

If you encounter version conflicts, you may need to rebuild the environment or use a compatible pyscipopt version.
