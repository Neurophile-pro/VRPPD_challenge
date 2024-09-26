from src.data_models.courier import Courier
from src.data_models.delivery import Delivery

import numpy as np


def one_pass(couriers: list[Courier], deliveries: list[Delivery], travel_times: np.matrix):
    deliveries.sort(key=lambda delivery: delivery.time_window_start)

    earliest_available = {courier: 0 for courier in couriers}
    last_location = {courier: courier.location for courier in couriers}
    routes = {courier: [] for courier in couriers}

    for delivery in deliveries:
        courier_candidates = [courier for courier in couriers if courier.capacity >= delivery.capacity]
        courier_candidates = [c for c in courier_candidates if len(routes[c]) <= 3]
        arrival_times = {courier: earliest_available[courier] + travel_times[last_location[courier], delivery.pickup_loc]
                         for courier in courier_candidates}
        courier_candidates = [c for c in courier_candidates if arrival_times[c] + travel_times[delivery.pickup_loc, delivery.dropoff_loc] <= 180]

        if not courier_candidates:
            return None

        selected_courier = min(courier_candidates, key=lambda courier: abs(arrival_times[courier] - delivery.time_window_start))
        routes[selected_courier].append(delivery)
        routes[selected_courier].append(delivery)
        earliest_available[selected_courier] = delivery.time_window_start + travel_times[delivery.pickup_loc, delivery.dropoff_loc]
        last_location[selected_courier] = delivery.dropoff_loc

    return routes
