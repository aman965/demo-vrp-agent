from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def create_data_model(distance_matrix, demands, vehicle_count, vehicle_capacity):
    """
    Create the data model for the CVRP problem
    """
    data = {}
    data['distance_matrix'] = distance_matrix
    data['demands'] = demands
    data['vehicle_capacities'] = [vehicle_capacity] * vehicle_count
    data['num_vehicles'] = vehicle_count
    data['depot'] = 0
    return data


def solve_cvrp(distance_matrix, demands, vehicle_count, vehicle_capacity, extra_constraints=None):
    """
    Solve the CVRP problem using OR-Tools
    
    Args:
        distance_matrix: Matrix of distances between nodes
        demands: List of demands for each node
        vehicle_count: Number of vehicles
        vehicle_capacity: Base capacity for each vehicle
        extra_constraints: Optional list of additional constraints to apply
        
    Returns:
        dict: Solution data including routes, distances, and implementation notes
    """
    implementation_notes = []
    data = create_data_model(distance_matrix, demands, vehicle_count, vehicle_capacity)
    
    # Apply extra constraints if provided
    if extra_constraints:
        for constraint in extra_constraints:
            constraint_type = constraint.get('type')
            value = constraint.get('value')
            
            if constraint_type == 'capacity_limit':
                # Update vehicle capacities
                data['vehicle_capacities'] = [value] * vehicle_count
                implementation_notes.append(f"Set vehicle capacity to {value}")
            
            elif constraint_type == 'max_customers_per_vehicle':
                # Will be handled after routing model creation
                implementation_notes.append(f"Will cap customers per vehicle to {value}")
    
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']), 
        data['num_vehicles'], 
        data['depot']
    )
    
    routing = pywrapcp.RoutingModel(manager)
    
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    def demand_callback(from_index):
        """Returns the demand of the node."""
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity'
    )
    
    # Apply customer count constraints if specified
    if extra_constraints:
        for constraint in extra_constraints:
            if constraint.get('type') == 'max_customers_per_vehicle':
                def customer_callback(from_index):
                    """Returns 1 for each customer (non-depot) node."""
                    from_node = manager.IndexToNode(from_index)
                    return 1 if from_node != data['depot'] else 0
                
                customer_callback_index = routing.RegisterUnaryTransitCallback(customer_callback)
                routing.AddDimension(
                    customer_callback_index,
                    0,  # null capacity slack
                    constraint['value'],  # maximum customers per vehicle
                    True,  # start cumul to zero
                    'Customers'
                )
                implementation_notes.append(f"Added constraint: maximum {constraint['value']} customers per vehicle")
    
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30
    
    solution = routing.SolveWithParameters(search_parameters)
    
    if not solution:
        return None
    
    routes = []
    total_distance = 0
    
    for vehicle_id in range(data['num_vehicles']):
        route = []
        index = routing.Start(vehicle_id)
        route_distance = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            
        route.append(manager.IndexToNode(index))
        routes.append(route)
        total_distance += route_distance
    
    return {
        'routes': routes,
        'total_distance': total_distance,
        'solution': solution,
        'manager': manager,
        'routing': routing,
        'distance_matrix': data['distance_matrix'],
        'implementation_notes': implementation_notes
    }


def get_route_info(solution_data, df):
    """
    Get detailed information about each route
    """
    if solution_data is None:
        return None
        
    routes = solution_data['routes']
    solution = solution_data['solution']
    manager = solution_data['manager']
    routing = solution_data['routing']
    
    route_info = []
    
    for vehicle_id, route in enumerate(routes):
        route_details = {
            'vehicle_id': vehicle_id + 1,
            'stops': [],
            'total_distance': 0,
            'total_demand': 0,
            'route_text': f"Vehicle {vehicle_id + 1}: Depot"
        }
        
        route_distance = 0
        route_demand = 0
        
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            
            if from_node == 0 and to_node == 0:
                continue
                
            if to_node != 0:
                customer_id = df.iloc[to_node]['CustomerID']
                demand = df.iloc[to_node]['Demand']
                route_details['stops'].append({
                    'customer_id': customer_id,
                    'node_idx': to_node,
                    'demand': demand
                })
                route_details['route_text'] += f" → {customer_id}"
                route_demand += demand
            else:
                route_details['route_text'] += " → Depot"
                
            distance = solution_data['distance_matrix'][from_node][to_node]
            route_distance += distance
            
        route_details['total_distance'] = route_distance
        route_details['total_demand'] = route_demand
        
        if len(route_details['stops']) > 0:
            route_info.append(route_details)
    
    return route_info
