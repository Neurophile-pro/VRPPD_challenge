# Main function to loop through all instance folders (SCIP version)
import argparse
import os
from datetime import datetime, timedelta

import numpy as np

from src.data_models.courier import Courier
from src.data_models.delivery import Delivery
# from src.mip_scip import RoutingMIPSolverSCIP
from src.mip_scip_valid_arcs import RoutingMIPSolverSCIP
from src.one_pass import one_pass
from src.read_data import process_instance_folder


def is_instance_folder(folder_path):
    """Check if a folder contains the required instance files"""
    return (os.path.isfile(os.path.join(folder_path, 'couriers.csv')) and
            os.path.isfile(os.path.join(folder_path, 'deliveries.csv')) and
            os.path.isfile(os.path.join(folder_path, 'traveltimes.csv')))


def process_all_instances(parent_folder):
    all_instances = []
    
    # Check if the provided folder is itself an instance
    if is_instance_folder(parent_folder):
        print(f"Processing single instance: {os.path.basename(parent_folder)}")
        try:
            couriers, deliveries, travel_time = process_instance_folder(parent_folder)
            all_instances.append({
                'instance_name': os.path.basename(parent_folder),
                'couriers': couriers,
                'deliveries': deliveries,
                'travel_time': travel_time
            })
            return all_instances
        except Exception as e:
            print(f"Error processing instance: {e}")
            return all_instances

    # Otherwise, loop through each instance folder in the parent directory
    print(f"Processing multiple instances from: {parent_folder}")
    for instance_folder in os.listdir(parent_folder):
        instance_folder_path = os.path.join(parent_folder, instance_folder)

        # Check if it's a directory containing instance files
        if os.path.isdir(instance_folder_path) and is_instance_folder(instance_folder_path):
            print(f"Processing instance: {instance_folder}")
            try:
                couriers, deliveries, travel_time = process_instance_folder(instance_folder_path)

                # Add this instance's couriers, deliveries, and travel time matrix to the overall list
                all_instances.append({
                    'instance_name': instance_folder,
                    'couriers': couriers,
                    'deliveries': deliveries,
                    'travel_time': travel_time
                })
            except Exception as e:
                print(f"Error processing instance {instance_folder}: {e}")

    return all_instances



def write_solution_to_csv(inst, solution: dict[Courier, list[Delivery]], override=False):
    # Ensure solutions directory exists
    os.makedirs('solutions', exist_ok=True)
    
    mode = "w" if override else "x"
    output_file = f"solutions/{inst['instance_name']}_scip.csv"
    
    try:
        with open(output_file, mode) as csv_file:
            csv_file.write('ID\n')
            if solution is None:
                return
            for courier in solution:
                route = ','.join([str(delivery.delivery_id) for delivery in solution[courier]])
                if route:
                    csv_file.write(f'{courier.courier_id},{route}\n')
                else:
                    csv_file.write(f'{courier.courier_id}\n')
    except FileExistsError:
        print(f"  (Heuristic solution already exists, will be overwritten on optimization)")
    except Exception as e:
        print(f"  Error writing solution: {e}")

# Entry point of the script
def main():
    import sys
    
    total_time = 3000
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=total_time)

    # Parse the command-line arguments
    parser = argparse.ArgumentParser(description="Process couriers, deliveries, and travel time matrices from multiple instances using SCIP solver.")
    parser.add_argument('parent_folder', type=str, help='Path to the parent folder containing all instance folders or a single instance folder')

    args = parser.parse_args()
    
    print("="*70)
    print("SCIP VRP Solver")
    print("="*70)
    print(f"Input path: {args.parent_folder}")
    print()
    sys.stdout.flush()

    # Process all instances
    all_instance_data = process_all_instances(args.parent_folder)
    
    if not all_instance_data:
        print("ERROR: No instances found!")
        print(f"  Expected: {args.parent_folder} to be an instance folder or contain instance folders")
        print(f"  Instance folders must contain: couriers.csv, deliveries.csv, traveltimes.csv")
        return
    
    print(f"Found {len(all_instance_data)} instance(s)")
    print()
    sys.stdout.flush()

    # Sort instances by increasing size
    all_instance_data.sort(key=lambda inst: len(inst['couriers']) + len(inst['deliveries']))

    # try to find feasible start solution for all instances using one-pass heuristic
    print("Step 1: Finding feasible solutions using one-pass heuristic...")
    print("-"*70)
    for inst in all_instance_data:
        instance_size = len(inst['couriers']) + len(inst['deliveries'])
        print(f"  {inst['instance_name']} (size: {instance_size})", end="", flush=True)
        solution = one_pass(inst['couriers'], inst['deliveries'], inst['travel_time'])
        inst['solution'] = solution
        if solution is None:
            print(" - INFEASIBLE")
        else:
            write_solution_to_csv(inst, solution, override=False)
            total_deliveries = sum(len(route) for route in solution.values())
            print(f" - OK ({total_deliveries} deliveries assigned)")
        sys.stdout.flush()

    print()
    print("Step 2: Optimizing using SCIP solver (60 seconds per instance)...")
    print("-"*70)

    # try to find solution using MIP with SCIP solver
    for inst in all_instance_data:
        instance_size = len(inst['couriers']) + len(inst['deliveries'])
        print(f"  {inst['instance_name']} (size: {instance_size})", end="", flush=True)
        try:
            optimizer = RoutingMIPSolverSCIP(couriers=inst['couriers'], deliveries=inst['deliveries'],transit_times=inst['travel_time'])
            print(" - Model created, optimizing...", end="", flush=True)
            solution = optimizer.optimize()
            write_solution_to_csv(inst, solution, override=True)
            if solution:
                total_deliveries = sum(len(route) for route in solution.values())
                print(f" - OK ({total_deliveries} deliveries assigned)")
            else:
                print(" - INFEASIBLE")
        except Exception as e:
            print(f" - ERROR: {e}")
        sys.stdout.flush()
    
    print()
    print("="*70)
    print("✓ Solver completed!")
    print("="*70)
    print(f"Results saved in: solutions/")
    print()
    sys.stdout.flush()


# Main execution
if __name__ == "__main__":
    main()
