import enum
import numpy as np
from pyscipopt import Model, quicksum

from src.read_data import Courier, Delivery


class NodeType(enum.Enum):
    DEPOT = enum.auto(),
    PICKUP = enum.auto(),
    DROPOFF = enum.auto()
    DUMMY_END = enum.auto()

class RoutingMIPSolverSCIP:
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
        if index < self.num_nodes - 1  and (index - self.num_couriers) % 2 == 0:
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

        # Build the arc list first so we only create variables and constraints
        # for transitions that are actually plausible for this instance.
        # This reduces model size before any SCIP variables are added.
        def node_earliest_time(index: int) -> int:
            node_type, pd_idx = self.get_node_info_from_index(index)
            if node_type == NodeType.DEPOT:
                return 0
            if node_type == NodeType.PICKUP:
                return self.pd_pairs[pd_idx].time_window_start
            if node_type == NodeType.DROPOFF:
                pickup_start = self.pd_pairs[pd_idx].time_window_start
                pickup_to_dropoff = self.transit_times[
                    self.pd_pairs[pd_idx].pickup_loc,
                    self.pd_pairs[pd_idx].dropoff_loc,
                ]
                return pickup_start + pickup_to_dropoff
            return 0

        valid_arcs = []
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i == j:
                    continue

                from_type, from_pd_idx = self.get_node_info_from_index(i)
                to_type, to_pd_idx = self.get_node_info_from_index(j)

                # Respect pickup/dropoff precedence by forbidding the reverse arc
                # of the same pickup-delivery pair.
                if from_type == NodeType.DROPOFF and to_type == NodeType.PICKUP and from_pd_idx == to_pd_idx:
                    continue

                transit_time = self.get_transit_time(i, j)

                # Skip arcs whose travel time already makes the route impossible.
                # If the earliest possible arrival at j already exceeds the global
                # route horizon, this arc can never be part of a feasible solution.
                if node_earliest_time(i) + transit_time > self.TRANSIT_TIME_UB:
                    continue

                # Keep all other arcs, including arcs into the dummy end node.
                valid_arcs.append((i, j))

        self.valid_arcs = valid_arcs

        # Variables

        # couriers_ic = 1, iff node i is covered by courier c
        couriers = {}
        for i in range(self.num_nodes):
            for c in range(self.num_couriers):
                couriers[i, c] = model.addVar(vtype='B', name=f'couriers_{i}_{c}')
        self.courier_vars = couriers
        
        # next_ij = 1, iff edge (i,j) is traversed in some route
        next_node = {}
        for i, j in valid_arcs:
            next_node[i, j] = model.addVar(vtype='B', name=f'next_node_{i}_{j}')
        self.next_node_vars = next_node
        
        # time_n = time point in min, at which node n is visited
        time = {}
        for i in range(self.num_nodes):
            time[i] = model.addVar(lb=0, ub=self.TRANSIT_TIME_UB, name=f'time_{i}')
        
        # deliveries_n = number of deliveries performed on subroute to node n
        deliveries = {}
        for i in range(self.num_nodes):
            deliveries[i] = model.addVar(lb=0, ub=4, name=f'deliveries_{i}')
        
        # capacity_n = accumulated capacity on subroute to node n
        capacity = {}
        for i in range(self.num_nodes):
            capacity[i] = model.addVar(lb=0, ub=self.max_courier_capacity, name=f'capacity_{i}')

        # Constraints
        # remove loops from network
        # Loops are not created at all, so no explicit constraint is needed.
        
        # remove edges between depots
        for i in range(self.num_couriers):
            for j in range(self.num_couriers):
                if (i, j) in next_node:
                    model.addCons(next_node[i, j] == 0)
        
        # require all nodes except for dummy end node to have exactly one outgoing edge on their route
        for i in range(self.num_nodes - 1):
            model.addCons(quicksum(next_node[i, j] for j in range(self.num_nodes) if (i, j) in next_node) == 1)
        
        # require all nodes except for dummy end node and depot nodes to have exactly one incoming edge
        for j in range(self.num_couriers, self.num_nodes - 1):
            model.addCons(quicksum(next_node[i, j] for i in range(self.num_nodes) if (i, j) in next_node) == 1)
        
        # require dummy end node to have no outgoing edge
        for i in range(self.num_nodes):
            if (self.num_nodes - 1, i) in next_node:
                model.addCons(next_node[self.num_nodes - 1, i] == 0)
        
        # define courier start nodes
        for i in range(self.num_couriers):
            model.addCons(couriers[i, i] == 1)
        
        # exactly one courier used for each node other than dummy end node
        for i in range(self.num_nodes - 1):
            model.addCons(quicksum(couriers[i, c] for c in range(self.num_couriers)) == 1)

        # same courier is used for nodes (i,j) if next_ij = 1 except if j is dummy end node
        # Using big M formulation since SCIP doesn't have indicator constraints like xpress
        for i, j in valid_arcs:
            if j == self.num_nodes - 1:
                continue
            if i == j:
                continue
            
            for c in range(self.num_couriers):
                # If next_node[i,j] = 1, then couriers[i,c] must equal couriers[j,c].
                # Two inequalities are enough to enforce equality when the arc is active.
                model.addCons(couriers[j, c] >= couriers[i, c] - (1 - next_node[i, j]))
                model.addCons(couriers[i, c] >= couriers[j, c] - (1 - next_node[i, j]))

        # require pickup/dropoff pairs to be visited by same courier
        for i in range(self.num_couriers, self.num_nodes - 2, 2):
            for c in range(self.num_couriers):
                model.addCons(couriers[i, c] == couriers[i + 1, c])

        # require pickups to happen before dropoff
        for i in range(self.num_couriers, self.num_nodes - 1, 2):
            model.addCons(time[i] <= time[i + 1])

        # define delivery counter variables
        for i in range(self.num_couriers):
            model.addCons(deliveries[i] == 0)
        
        for i, j in valid_arcs:
            if j == self.num_nodes - 1:
                continue
            node_type, _ = self.get_node_info_from_index(j)
            if node_type == NodeType.DROPOFF:
                # If next_node[i,j] = 1, then deliveries[j] = deliveries[i] + 1.
                model.addCons(deliveries[j] >= deliveries[i] + 1 - self.delivery_big_m * (1 - next_node[i, j]))
                model.addCons(deliveries[j] <= deliveries[i] + 1 + self.delivery_big_m * (1 - next_node[i, j]))
            else:
                # If next_node[i,j] = 1, then deliveries[i] = deliveries[j].
                model.addCons(deliveries[i] >= deliveries[j] - self.delivery_big_m * (1 - next_node[i, j]))
                model.addCons(deliveries[i] <= deliveries[j] + self.delivery_big_m * (1 - next_node[i, j]))

        # define transit times
        for i, j in valid_arcs:
            transit_time = self.get_transit_time(i, j)
            # If next_node[i,j] = 1, then time[j] >= time[i] + transit_time.
            model.addCons(time[j] >= time[i] + transit_time - self.time_big_m * (1 - next_node[i, j]))

        # add time window constraints
        for i in range(self.num_nodes):
            node_type, pd_pair_idx = self.get_node_info_from_index(i)
            if node_type == NodeType.PICKUP:
                model.addCons(time[i] >= self.pd_pairs[pd_pair_idx].time_window_start)

        # set initial capacities to 0
        for i in range(self.num_couriers):
            model.addCons(capacity[i] == 0)

        # define capacity changes on routes (ignoring edges to dummy end node)
        for i, j in valid_arcs:
            if j == self.num_nodes - 1:
                continue
            capacity_delta = self.get_capacity_delta(j)
            # If next_node[i,j] = 1, then capacity[j] = capacity[i] + capacity_delta.
            model.addCons(capacity[j] >= capacity[i] + capacity_delta - self.capacity_big_m * (1 - next_node[i, j]))
            model.addCons(capacity[j] <= capacity[i] + capacity_delta + self.capacity_big_m * (1 - next_node[i, j]))

        # define capacity limits on nodes
        for i in range(self.num_nodes - 1):
            model.addCons(
                capacity[i] <= quicksum(self.couriers[c].capacity * couriers[i, c] for c in range(self.num_couriers))
            )

        # set objective
        model.setObjective(
            quicksum(time[i] for i in range(self.num_nodes) if self.get_node_info_from_index(i)[0] == NodeType.DROPOFF)
        )

        return model, couriers, next_node, time, deliveries, capacity

    def optimize(self):
        model, couriers, next_node, time, deliveries, capacity = self.create_model()
        model.setParam('limits/time', 1200)  # set time limit, in seconds
        model.optimize()
        return self.get_solution(model, next_node)

    def get_solution(self, model, next_node_vars):
        courier_routes = dict()
        
        # Extract solution
        next_node_sol = {}
        for i, j in self.valid_arcs:
            val = model.getVal(next_node_vars[i, j])
            next_node_sol[i, j] = val if val is not None else 0
        
        # print("Solution extracted:")
        # for i, j in self.valid_arcs:
        #     if next_node_sol.get((i, j), 0) >= 0.5:
        #         print(f"Edge ({i}, {j}): {next_node_sol[i, j]}")
        
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
