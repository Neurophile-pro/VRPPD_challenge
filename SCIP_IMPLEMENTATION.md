# SCIP Solver Implementation Summary

## Overview
Created a complete SCIP-based implementation of the VRP with Pickup and Delivery (VRPPD) solver as an alternative to the existing xpress-based solution.

## Files Created

### Core Implementation Files
1. **`src/mip_scip.py`** 
   - Implements `RoutingMIPSolverSCIP` class
   - Equivalent to the xpress-based `RoutingMIPSolver`
   - Uses PySCIPOpt (python-scip) library
   - Formulates same MIP model with big-M constraints instead of indicator constraints
   - Time limit: 60 seconds per instance
   - Same objective function and constraints

2. **`main_scip.py`**
   - Main entry point for SCIP solver version
   - Processes all instances in parallel structure
   - Outputs solutions with "_scip" suffix for comparison
   - Same workflow as original main.py

### Helper Scripts

3. **`check_scip_setup.py`**
   - Verifies pyscipopt installation
   - Attempts automatic installation if missing
   - Tests all imports and dependencies
   - Usage: `python check_scip_setup.py`

4. **`run_solvers.py`**
   - Unified interface to run either solver
   - Displays comparison between xpress and SCIP
   - Usage examples:
     ```bash
     python run_solvers.py --compare          # Show comparison
     python run_solvers.py --scip ./data/    # Run SCIP only
     python run_solvers.py --both ./data/    # Run both solvers
     ```

5. **`setup_scip.sh`**
   - Bash script to setup SCIP environment
   - Activates conda environment
   - Installs pyscipopt if needed

### Documentation

6. **`README_SCIP.md`**
   - Detailed documentation about SCIP implementation
   - Installation instructions
   - Running guides
   - Troubleshooting

## Key Differences from Xpress Version

| Aspect | Xpress | SCIP |
|--------|--------|------|
| **License** | Proprietary | Open-source |
| **Installation** | Requires xpauth.xpr | `pip install pyscipopt` |
| **Main Script** | `main.py` | `main_scip.py` |
| **Solver Class** | `RoutingMIPSolver` | `RoutingMIPSolverSCIP` |
| **Output Files** | `instance_name.csv` | `instance_name_scip.csv` |
| **Indicator Constraints** | Native support | Converted to big-M |
| **Library** | `xpress` | `pyscipopt` |

## Implementation Details

### Constraint Formulation
SCIP doesn't have native indicator constraints like xpress, so the implementation uses big-M method:

**Xpress (original):**
```python
model.addIndicator(next_node[i,j]==1, time[j] >= time[i] + transit_time)
```

**SCIP (new):**
```python
# If next_node[i,j] = 1, then constraint must hold
# If next_node[i,j] = 0, constraint is relaxed using big-M
model.addCons(time[j] >= time[i] + transit_time - (big_M) * (1 - next_node[i,j]))
```

### Variable Creation
SCIP uses dictionary-based variable access instead of indexed xpress arrays, allowing more flexible constraint formulation.

## Quick Start

### Option 1: Using the setup script
```bash
conda activate VRPPD
cd /mnt/home2/home/chhavi/10_OptiTech_solutions/Solutions\ 2/coatwork-vrp-challenge/
bash setup_scip.sh
python main_scip.py <path_to_instances>
```

### Option 2: Direct approach
```bash
conda activate VRPPD
cd /mnt/home2/home/chhavi/10_OptiTech_solutions/Solutions\ 2/coatwork-vrp-challenge/
pip install pyscipopt  # if not already installed
python main_scip.py <path_to_instances>
```

### Option 3: Using the unified runner
```bash
cd /mnt/home2/home/chhavi/10_OptiTech_solutions/Solutions\ 2/coatwork-vrp-challenge/
python run_solvers.py --scip <path_to_instances>
```

## TMux Usage

To use in your existing tmux session:
```bash
tmux send-keys -t 0 "cd /mnt/home2/home/chhavi/10_OptiTech_solutions/Solutions\\ 2/coatwork-vrp-challenge && conda activate VRPPD && python main_scip.py <instances_path>" ENTER
```

## Shared Components

Both xpress and SCIP versions share:
- `src/one_pass.py` - Heuristic start solution
- `src/read_data.py` - Data loading and processing
- `src/data_models/` - Data structures (Courier, Delivery)
- `feasibility_checker.py` - Solution verification

This ensures identical problem formulation and input handling across both solvers.

## Solution Comparison

After running both solvers, you can compare solutions:
```
solutions/instance_name.csv      ← Xpress results
solutions/instance_name_scip.csv ← SCIP results
```

Both files have the same format, making side-by-side comparison easy.

## Parameters

Both solvers use identical parameters:
- **Time limit:** 60 seconds
- **Objective:** Minimize total delivery completion time
- **Constraints:** All constraints from the VRPPD formulation are preserved

## Troubleshooting

**Issue: `ModuleNotFoundError: No module named 'pyscipopt'`**
- Solution: Run `pip install pyscipopt`
- Or: `python check_scip_setup.py` (auto-install)

**Issue: Solutions not improving after heuristic**
- Check that time limit isn't too short
- Verify instances are being loaded correctly
- Check solver logs for feasibility issues

**Issue: Different solutions from xpress**
- Both solvers might find different local optima
- SCIP may find better solutions due to different search strategies
- Compare objective values in CSV files

## Next Steps

1. Run setup: `python check_scip_setup.py`
2. Test with a small instance: `python main_scip.py <small_instance_path>`
3. Compare with xpress: `python run_solvers.py --both <instances_path>`
4. Review solutions in `solutions/` directory

## Support

For issues with:
- **SCIP solver:** Check [PySCIPOpt documentation](https://github.com/scipopt/PySCIPOpt)
- **Implementation:** Review `src/mip_scip.py` comments and constraint formulations
- **Data handling:** Both versions use identical data models from `src/data_models/`
