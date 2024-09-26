import os
import csv
import numpy as np

from src.data_models.courier import Courier
from src.data_models.delivery import Delivery

# Function to load couriers from CSV using the csv module
def load_couriers_from_csv(filepath: str) -> list[Courier]:
    couriers = []
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            courier = Courier(
                courier_id=int(row['ID']),
                location=int(row['Location']),
                capacity=int(row['Capacity'])
            )
            couriers.append(courier)
    return couriers


# Function to load deliveries from CSV using the csv module
def load_deliveries_from_csv(filepath: str) -> list[Delivery]:
    deliveries = []
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            delivery = Delivery(
                delivery_id=int(row['ID']),
                capacity=int(row['Capacity']),
                pickup_loc=int(row['Pickup Loc']),
                time_window_start=int(row['Time Window Start']),
                pickup_stacking_id=int(row['Pickup Stacking_Id']),
                dropoff_loc=int(row['Dropoff Loc'])
            )
            deliveries.append(delivery)
    return deliveries


# Function to load travel time matrix from CSV
def load_travel_time_from_csv(filepath) -> np.ndarray:
    travel_time = []
    with open(filepath, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == 'Locations':
                travel_time.append([val for val in row])
            else:
                travel_time.append([int(val) for val in row][1:])  # Convert the row values to integers, skip the location index (first column)
    return np.array(travel_time[1:])


# Function to process each instance folder and look for couriers.csv, deliveries.csv, and traveltime.csv
def process_instance_folder(instance_folder_path):
    couriers_file = None
    deliveries_file = None
    travel_time_file = None

    # Search for files in the instance folder
    for filename in os.listdir(instance_folder_path):
        if 'couriers.csv' in filename:
            couriers_file = os.path.join(instance_folder_path, filename)
        elif 'deliveries.csv' in filename:
            deliveries_file = os.path.join(instance_folder_path, filename)
        elif 'traveltimes.csv' in filename:
            travel_time_file = os.path.join(instance_folder_path, filename)

    # Ensure all necessary files are found
    if not couriers_file:
        raise FileNotFoundError(f"Missing couriers.csv file in folder: {instance_folder_path}")

    if not deliveries_file:
        raise FileNotFoundError(f"Missing deliveries.csv file in folder: {instance_folder_path}")

    if not travel_time_file:
        raise FileNotFoundError(f"Missing traveltimes.csv file in folder: {instance_folder_path}")


    # Load couriers, deliveries, and travel time matrix from the instance
    couriers = load_couriers_from_csv(couriers_file)
    deliveries = load_deliveries_from_csv(deliveries_file)
    travel_time = load_travel_time_from_csv(travel_time_file)

    return couriers, deliveries, travel_time


