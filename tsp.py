"""Simple travelling salesman problem on a circuit board."""
from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
# GPXpy Library
import gpxpy.geo


with open("quest_list.txt", 'r') as file:
    coordinates = [line.strip().split(',') for line in file.readlines()]
    coordinates = [(float(lat), float(lon)) for lat, lon in coordinates]

def create_data_model():
    """Stores the data for the problem."""

    data = {}
    # Locations in block units
    data['locations'] = [*coordinates]  # yapf: disable
    data['num_vehicles'] = 1
    data['depot'] = 1
    return data


def compute_euclidean_distance_matrix(locations):
    """Creates callback to return distance between points."""
    distances = {}
    for from_counter, from_node in enumerate(locations):
        distances[from_counter] = {}
        for to_counter, to_node in enumerate(locations):
            if from_counter == to_counter:
                distances[from_counter][to_counter] = 0
            else:
                # Euclidean distance
                # distances[from_counter][to_counter] = (int(math.hypot((from_node[0] - to_node[0]), (from_node[1] - to_node[1]))))
                # Harvesian distance
                distances[from_counter][to_counter] = (int(gpxpy.geo.haversine_distance(from_node[0], from_node[1], to_node[0], to_node[1])))
    return distances

def print_solution(manager, routing, assignment):
    """Prints assignment on console."""
    # print('Objective: {} miles'.format(assignment.ObjectiveValue()))
    index = routing.Start(0)
    plan_output = '\n'
    route_distance = 0
    with open('output.txt', 'w') as f:
        f.truncate(0)
    while not routing.IsEnd(index):
        plan_output += ' {} ->'.format(manager.IndexToNode(index))
        with open('output.txt', 'a') as f:
            f.write(str(coordinates[index][0]) + ',' + str(coordinates[index][1]) + '\n')

        previous_index = index
        index = assignment.Value(routing.NextVar(index))
        route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
    plan_output += ' {}\n'.format(manager.IndexToNode(index))
    plan_output += 'Route distance: {} meters\n'.format(route_distance)
    print(plan_output)

def main():
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model()

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['locations']), data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    distance_matrix = compute_euclidean_distance_matrix(data['locations'])

    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC)

    # Solve the problem.
    assignment = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if assignment:
        print_solution(manager, routing, assignment)


if __name__ == '__main__':
    main()
