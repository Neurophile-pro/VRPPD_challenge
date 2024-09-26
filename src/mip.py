import enum

import numpy as np
import xpress as xp

from src.read_data import Courier, Delivery



class NodeType(enum.Enum):
    DEPOT = enum.auto(),
    PICKUP = enum.auto(),
    DROPOFF = enum.auto()
    DUMMY_END = enum.auto()

class RoutingMIPSolver:
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

    # noinspection PyArgumentList
    def create_model(self):
        model = xp.problem()

        # Variables

        # couriers_ic = 1, iff node i is covered by courier c
        couriers = model.addVariables(self.num_nodes, self.num_couriers, vartype=xp.binary, name='couriers')
        self.courier_vars = couriers
        # next_ij = 1, iff edge (i,j) is traversed in some route
        next_node = model.addVariables(self.num_nodes, self.num_nodes, vartype=xp.binary, name='next_node')
        self.next_node_vars = next_node
        # time_n = time point in min, at which node n is visited
        time = model.addVariables(self.num_nodes, lb=0, ub=self.TRANSIT_TIME_UB,
                                  name='time')
        # deliveries_n = number of delivieries performed on subroute to node n
        deliveries = model.addVariables(self.num_nodes, vartype=xp.continuous, lb=0, ub=4, name='deliveries')
        # capacity_n = accumulated capacity on subroute to node n
        capacity = model.addVariables(self.num_nodes, vartype=xp.continuous, lb=0, ub=self.max_courier_capacity,
                                      name='capacity')

        # Constraints
        # remove loops from network
        model.addConstraint(next_node[i,i] == 0 for i in range(self.num_nodes))
        # remove edges between depots
        model.addConstraint(next_node[i,j] == 0 for i in range(self.num_couriers) for j in range(self.num_couriers))
        # require all nodes except for dummy end node to have exactly one outgoing edge on their route
        model.addConstraint(
            xp.Sum(next_node[i, j] for j in range(self.num_nodes)) == 1 for i in range(self.num_nodes - 1)
        )
        # require all nodes except for dummy end node and depot nodes to have exactly one incoming edge
        model.addConstraint(
            xp.Sum(next_node[i, j] for i in range(self.num_nodes)) == 1
            for j in range(self.num_couriers, self.num_nodes - 1)
        )
        # require dummy end node to have no outgoing edge
        model.addConstraint(next_node[self.num_nodes - 1, i] == 0 for i in range(self.num_nodes))
        # define courier start nodes
        model.addConstraint(couriers[i,i] == 1 for i in range(self.num_couriers))
        # exactly one courier used for each node other than dummy end node
        model.addConstraint(
            xp.Sum(couriers[i,c] for c in range(self.num_couriers)) == 1 for i in range(self.num_nodes - 1)
        )

        # same courier is used for nodes (i,j) if next_ij = 1 except if j is dummy end node
        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i==j: continue
                for c in range(self.num_couriers):
                    model.addIndicator(next_node[i,j]==1, couriers[i,c] == couriers[j,c])


        # require pickup/dropoff pairs to be visited by same courier
        for i in range(self.num_couriers, self.num_nodes - 2, 2):
            model.addConstraint(couriers[i, c] == couriers[i+1, c] for c in range(self.num_couriers))

        # require pickups to happen before dropoff
        model.addConstraint(time[i] <= time[i+1] for i in range(self.num_couriers, self.num_nodes - 1, 2))

        # define delivery counter variables
        model.addConstraint(deliveries[i] == 0 for i in range(self.num_couriers))
        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i==j: continue
                node_type, _ = self.get_node_info_from_index(j)
                if node_type == NodeType.DROPOFF:
                    model.addIndicator(next_node[i,j]==1, deliveries[j] == deliveries[i] + 1)
                else:
                    model.addIndicator(next_node[i,j]==1, deliveries[i] == deliveries[j])

        #define transit times
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i==j: continue
                transit_time = self.get_transit_time(i,j)
                model.addIndicator(next_node[i,j]==1, time[j] >= time[i] + transit_time)


        # add time window constraints
        for i in range(self.num_nodes):
            node_type, pd_pair_idx = self.get_node_info_from_index(i)
            if node_type == NodeType.PICKUP:
                model.addConstraint(time[i] >= self.pd_pairs[pd_pair_idx].time_window_start)

        # set initial capacities to 0
        for i in range(self.num_couriers):
            model.addConstraint(capacity[i] == 0)


        # define capacity changes on routes (ignoring edges to dummy end node)
        for i in range(self.num_nodes):
            for j in range(self.num_nodes - 1):
                if i==j: continue
                model.addIndicator(next_node[i,j]==1, capacity[j] == capacity[i] + self.get_capacity_delta(j))

    
        # define capacity limits on nodes
        for i in range(self.num_nodes - 1):
            model.addConstraint(
                capacity[i] <= xp.Sum(self.couriers[c].capacity * couriers[i,c] for c in range(self.num_couriers))
            )

        # set objective
        model.setObjective(
            xp.Sum(time[i] for i in range(self.num_nodes) if self.get_node_info_from_index(i)[0] == NodeType.DROPOFF)
        )

        return model


    def optimize(self):
        model = self.create_model()
        model.optimize()
        return self.get_solution(model)

    def get_solution(self, model):
        courier_routes = dict()
        print(model.getSolution(self.next_node_vars))
        for courier in range(self.num_couriers):
            route = []
            curidx = courier
            while curidx != self.num_nodes - 1:
                for next_idx in range(self.num_nodes):
                    if model.getSolution(self.next_node_vars[curidx, next_idx]) >= 0.97:

                        pd_id = self.get_node_info_from_index(next_idx)[1]
                        if pd_id is not None:
                            route.append(self.pd_pairs[pd_id])
                        curidx = next_idx
                        break
            courier_routes[self.couriers[courier]]=route
        return courier_routes

