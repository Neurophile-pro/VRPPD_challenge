class Delivery:
    def __init__(self, delivery_id, capacity, pickup_loc, time_window_start, pickup_stacking_id, dropoff_loc):
        self.delivery_id = delivery_id
        self.capacity = capacity
        self.pickup_loc = pickup_loc - 1
        self.time_window_start = time_window_start
        self.pickup_stacking_id = pickup_stacking_id
        self.dropoff_loc = dropoff_loc - 1

    def __repr__(self):
        return f"Delivery(ID={self.delivery_id}, Capacity={self.capacity}, Pickup Loc={self.pickup_loc}, " \
               f"Time Window Start={self.time_window_start}, Pickup Stacking Id={self.pickup_stacking_id}, Dropoff Loc={self.dropoff_loc})"

    def __hash__(self):
        return hash(self.delivery_id)