# Main function to loop through all instance folders
import argparse
import os
from datetime import datetime, timedelta

import numpy as np

from src.data_models.courier import Courier
from src.data_models.delivery import Delivery
from src.mip import RoutingMIPSolver
from src.one_pass import one_pass
from src.read_data import process_instance_folder


def process_all_instances(parent_folder):
    all_instances = []

    # Loop through each instance folder in the parent directory
    for instance_folder in os.listdir(parent_folder):
        instance_folder_path = os.path.join(parent_folder, instance_folder)

        # Check if it's a directory (instance folder)
        if os.path.isdir(instance_folder_path):
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
            except FileNotFoundError as e:
                print(e)

    return all_instances



def write_solution_to_csv(inst, solution: dict[Courier, list[Delivery]], override=False):
    mode = "w" if override else "x"
    with open(f"solutions/{inst['instance_name']}.csv", mode) as csv_file:
        csv_file.write('ID\n')
        if solution is None:
            return
        for courier in solution:
            route = ','.join([str(delivery.delivery_id) for delivery in solution[courier]])
            if route:
                csv_file.write(f'{courier.courier_id},{route}\n')
            else:
                csv_file.write(f'{courier.courier_id}\n')

# Entry point of the script
def main():

    total_time = 3000
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=total_time)

    # Parse the command-line arguments
    parser = argparse.ArgumentParser(description="Process couriers, deliveries, and travel time matrices from multiple instances.")
    parser.add_argument('parent_folder', type=str, help='Path to the parent folder containing all instance folders')

    args = parser.parse_args()

    # Process all instances
    all_instance_data = process_all_instances(args.parent_folder)

    # Sort instances by increasing size
    all_instance_data.sort(key=lambda inst: len(inst['couriers']) + len(inst['deliveries']))


    # try to find feasible start solution for all instances using one-pass heuristic
    for inst in all_instance_data:
        solution = one_pass(inst['couriers'], inst['deliveries'], inst['travel_time'])
        inst['solution'] = solution
        write_solution_to_csv(inst, solution, override=False)


    # try to find solution using MIP
    for inst in all_instance_data:
        instance_size = len(inst['couriers']) + len(inst['deliveries'])
        if instance_size:
            optimizer = RoutingMIPSolver(couriers=inst['couriers'], deliveries=inst['deliveries'],transit_times=inst['travel_time'])
            solution = optimizer.optimize()
            write_solution_to_csv(inst, solution, override=True)


import xpress as xp
xp.init('/workspaces/coatwork-vrp-challenge/xpauth.xpr')
# Main execution
if __name__ == "__main__":
    main()