import enum
import os

os.environ.setdefault("GRB_LICENSE_FILE", "/mnt/home2/home/chhavi/gurobi.lic")

import numpy as np
from gurobipy import GRB, Model, quicksum

from src.read_data import Courier, Delivery


class NodeType(enum.Enum):
    DEPOT = enum.auto(),
    PICKUP = enum.auto(),
    DROPOFF = enum.auto()
    DUMMY_END = enum.auto()


class RoutingMIPSolverGurobi:
    # upper bound for total accumulated transit time on each route
    TRANSIT_TIME_UB = 180

    def __init__(self, couriers: list[Courier], deliveries: list[Delivery], transit_times: np.matrix):
        self.couriers = couriers
        self.pd_pairs = deliveries
        self.transit_times = transit_times
        self.num_couriers = len(couriers)
        self.num_pd_pairs = len(deliveries)
        self.num_nodes = 2 * self.num_pd_pairs + self.num_couriers + 1
        self.max_courier_capacity = max(courier.capacity for courier in self.couriers)
        self.max_delivery_capacity = max(delivery.capacity for delivery in self.pd_pairs)
        self.time_big_m = 2 * self.TRANSIT_TIME_UB
        self.delivery_big_m = self.num_pd_pairs + 1
        self.capacity_big_m = self.max_courier_capacity + self.max_delivery_capacity

    # get node type and pickup-delivery pair idx if applicable
    def get_node_info_from_index(self, index: int) -> (NodeType, int | None):
        if index < self.num_couriers:
            return NodeType.DEPOT, None
        if index < self.num_nodes - 1 and (index - self.num_couriers) % 2 == 0:
            return NodeType.PICKUP, (index - self.num_couriers) // 2
        if index < self.num_nodes - 1 and (index - self.num_couriers) % 2 == 1:
            return NodeType.DROPOFF, (index - self.num_couriers) // 2
        if index == self.num_nodes - 1:
            return NodeType.DUMMY_END, None

    def get_transit_time(self, from_index: int, to_index: int) -> int:
        from_node_type, from_pd_idx = self.get_node_info_from_index(from_index)
        to_node_type, to_pd_idx = self.get_node_info_from_index(to_index)

        if to_node_type == NodeType.DUMMY_END:
            return 0
        if from_node_type == NodeType.DEPOT and to_node_type == NodeType.PICKUP:
            from_location = self.couriers[from_index].location
            to_location = self.pd_pairs[to_pd_idx].pickup_loc
            return self.transit_times[from_location, to_location]
        if from_node_type == NodeType.PICKUP and to_node_type == NodeType.DROPOFF:
            from_location = self.pd_pairs[from_pd_idx].pickup_loc
            to_location = self.pd_pairs[to_pd_idx].dropoff_loc
            return self.transit_times[from_location, to_location]
        if from_node_type == NodeType.PICKUP and to_node_type == NodeType.PICKUP:
            from_location = self.pd_pairs[from_pd_idx].pickup_loc
            to_location = self.pd_pairs[to_pd_idx].pickup_loc
            return self.transit_times[from_location, to_location]
        if from_node_type == NodeType.DROPOFF and to_node_type == NodeType.PICKUP:
            from_location = self.pd_pairs[from_pd_idx].dropoff_loc
            to_location = self.pd_pairs[to_pd_idx].pickup_loc
            return self.transit_times[from_location, to_location]
        if from_node_type == NodeType.DROPOFF and to_node_type == NodeType.DROPOFF:
            from_location = self.pd_pairs[from_pd_idx].dropoff_loc
            to_location = self.pd_pairs[to_pd_idx].dropoff_loc
            return self.transit_times[from_location, to_location]

        return self.TRANSIT_TIME_UB + 1

    def get_capacity_delta(self, index: int) -> int:
        node_type, node_pd_idx = self.get_node_info_from_index(index)
        if node_type == NodeType.PICKUP:
            return self.pd_pairs[node_pd_idx].capacity
        if node_type == NodeType.DROPOFF:
            return -self.pd_pairs[node_pd_idx].capacity

        return 0

    def is_valid_arc(self, from_index: int, to_index: int) -> bool:
        from_node_type, _ = self.get_node_info_from_index(from_index)
        to_node_type, _ = self.get_node_info_from_index(to_index)

        if from_index == to_index:
            return False
        if to_node_type == NodeType.DUMMY_END:
            return True
        if from_node_type == NodeType.DEPOT and to_node_type == NodeType.PICKUP:
            return True
        if from_node_type == NodeType.PICKUP and to_node_type in (NodeType.PICKUP, NodeType.DROPOFF):
            return True
        if from_node_type == NodeType.DROPOFF and to_node_type in (NodeType.PICKUP, NodeType.DROPOFF):
            return True
        return False

    def create_model(self):
        model = Model()

        # Variables
        couriers = {}
        for i in range(self.num_nodes):
            for c in range(self.num_couriers):
                couriers[i, c] = model.addVar(vtype=GRB.BINARY, name=f"couriers_{i}_{c}")
        self.courier_vars = couriers

        next_node = {}
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                next_node[i, j] = model.addVar(vtype=GRB.BINARY, name=f"next_node_{i}_{j}")
        self.next_node_vars = next_node

        time = {}
        for i in range(self.num_nodes):
            time[i] = model.addVar(lb=0, ub=self.TRANSIT_TIME_UB, name=f"time_{i}")

        deliveries = {}
        for i in range(self.num_nodes):
            deliveries[i] = model.addVar(lb=0, ub=4, name=f"deliveries_{i}")

        capacity = {}
        for i in range(self.num_nodes):
            capacity[i] = model.addVar(lb=0, ub=self.max_courier_capacity, name=f"capacity_{i}")

        # Constraints
        for i in range(self.num_nodes):
            model.addConstr(next_node[i, i] == 0)

        for i in range(self.num_couriers):
            for j in range(self.num_couriers):
                model.addConstr(next_node[i, j] == 0)

        for i in range(self.num_nodes - 1):
            model.addConstr(quicksum(next_node[i, j] for j in range(self.num_nodes)) == 1)

        for j in range(self.num_couriers, self.num_nodes - 1):
            model.addConstr(quicksum(next_node[i, j] for i in range(self.num_nodes)) == 1)

        for i in range(self.num_nodes):
            model.addConstr(next_node[self.num_nodes - 1, i] == 0)

        for i in range(self.num_couriers):
            model.addConstr(couriers[i, i] == 1)

        for i in range(self.num_nodes - 1):
            model.addConstr(quicksum(couriers[i, c] for c in range(self.num_couriers)) == 1)

        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i == j:
                    continue
                for c in range(self.num_couriers):
                    model.addConstr(couriers[j, c] >= couriers[i, c] - (1 - next_node[i, j]))
                    model.addConstr(couriers[i, c] >= couriers[j, c] - (1 - next_node[i, j]))

        for i in range(self.num_couriers, self.num_nodes - 2, 2):
            for c in range(self.num_couriers):
                model.addConstr(couriers[i, c] == couriers[i + 1, c])

        for i in range(self.num_couriers, self.num_nodes - 1, 2):
            model.addConstr(time[i] <= time[i + 1])

        for i in range(self.num_couriers):
            model.addConstr(deliveries[i] == 0)

        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i == j:
                    continue
                if not self.is_valid_arc(i, j):
                    model.addConstr(next_node[i, j] == 0)
                    continue
                node_type, _ = self.get_node_info_from_index(j)
                if node_type == NodeType.DROPOFF:
                    model.addConstr(deliveries[j] >= deliveries[i] + 1 - self.delivery_big_m * (1 - next_node[i, j]))
                    model.addConstr(deliveries[j] <= deliveries[i] + 1 + self.delivery_big_m * (1 - next_node[i, j]))
                else:
                    model.addConstr(deliveries[i] >= deliveries[j] - self.delivery_big_m * (1 - next_node[i, j]))
                    model.addConstr(deliveries[i] <= deliveries[j] + self.delivery_big_m * (1 - next_node[i, j]))

        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i == j:
                    continue
                transit_time = self.get_transit_time(i, j)
                if not self.is_valid_arc(i, j):
                    model.addConstr(next_node[i, j] == 0)
                    continue
                model.addConstr(time[j] >= time[i] + transit_time - self.time_big_m * (1 - next_node[i, j]))

        for i in range(self.num_nodes):
            node_type, pd_pair_idx = self.get_node_info_from_index(i)
            if node_type == NodeType.PICKUP:
                model.addConstr(time[i] >= self.pd_pairs[pd_pair_idx].time_window_start)

        for i in range(self.num_couriers):
            model.addConstr(capacity[i] == 0)

        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i == j:
                    continue
                if not self.is_valid_arc(i, j):
                    model.addConstr(next_node[i, j] == 0)
                    continue
                capacity_delta = self.get_capacity_delta(j)
                model.addConstr(capacity[j] >= capacity[i] + capacity_delta - self.capacity_big_m * (1 - next_node[i, j]))
                model.addConstr(capacity[j] <= capacity[i] + capacity_delta + self.capacity_big_m * (1 - next_node[i, j]))

        for i in range(self.num_nodes - 1):
            model.addConstr(
                capacity[i] <= quicksum(self.couriers[c].capacity * couriers[i, c] for c in range(self.num_couriers))
            )

        model.setObjective(
            quicksum(time[i] for i in range(self.num_nodes) if self.get_node_info_from_index(i)[0] == NodeType.DROPOFF),
            GRB.MINIMIZE,
        )

        return model, couriers, next_node, time, deliveries, capacity

    def optimize(self):
        model, couriers, next_node, time, deliveries, capacity = self.create_model()
        model.setParam("TimeLimit", 1800)
        model.optimize()
        return self.get_solution(model, next_node)

    def get_solution(self, model, next_node_vars):
        courier_routes = dict()

        next_node_sol = {}
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                var = next_node_vars[i, j]
                next_node_sol[i, j] = var.X if var is not None and model.SolCount > 0 else 0

        for courier in range(self.num_couriers):
            route = []
            curidx = courier
            while curidx != self.num_nodes - 1:
                found = False
                for next_idx in range(self.num_nodes):
                    if next_node_sol.get((curidx, next_idx), 0) >= 0.5:
                        pd_id = self.get_node_info_from_index(next_idx)[1]
                        if pd_id is not None:
                            route.append(self.pd_pairs[pd_id])
                        curidx = next_idx
                        found = True
                        break
                if not found:
                    break
            courier_routes[self.couriers[courier]] = route
        return courier_routes