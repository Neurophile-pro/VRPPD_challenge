class Courier:
    def __init__(self, courier_id, location, capacity):
        self.courier_id = courier_id
        self.location = location - 1
        self.capacity = capacity

    def __repr__(self):
        return f"Courier(ID={self.courier_id}, Location={self.location}, Capacity={self.capacity})"

    def __hash__(self):
        return hash(self.courier_id)