"""
A* Search Algorithm for ATLAS
Congestion-aware pathfinding for vehicle routing
"""

from typing import List, Optional, Dict, Tuple, Set
import heapq
import networkx as nx


def manhattan_distance(node1: str, node2: str, grid_size: int = 3) -> float:
    """
    Calculate Manhattan distance heuristic for grid network.
    
    For a grid where nodes are named I0, I1, ..., I(n²-1):
    - Row = index // grid_size
    - Col = index % grid_size
    - Distance = |row1 - row2| + |col1 - col2|
    
    Args:
        node1: Source node ID (e.g., "I0")
        node2: Destination node ID (e.g., "I8")
        grid_size: Size of the grid (default 3 for 3×3)
        
    Returns:
        Manhattan distance in grid units
    """
    try:
        # Extract numeric indices
        idx1 = int(node1[1:])
        idx2 = int(node2[1:])
        
        # Calculate row and column
        row1, col1 = divmod(idx1, grid_size)
        row2, col2 = divmod(idx2, grid_size)
        
        # Manhattan distance
        return abs(row1 - row2) + abs(col1 - col2)
    
    except (ValueError, IndexError):
        # Fallback to 0 if node format is unexpected
        return 0.0


def find_route(
    start: str,
    goal: str,
    network,
    grid_size: int = 3,
    max_iterations: int = 10000
) -> Optional[List[str]]:
    """
    Find shortest path using A* search with congestion-aware costs.
    
    The algorithm uses:
    - g(n): Actual cost from start to node n (sum of edge costs)
    - h(n): Heuristic estimate from n to goal (Manhattan distance)
    - f(n) = g(n) + h(n): Total estimated cost
    
    Edge costs include both distance and current congestion, so vehicles
    prefer less congested routes.
    
    Args:
        start: Starting intersection ID
        goal: Goal intersection ID
        network: RoadNetwork instance with current state
        grid_size: Grid size for heuristic calculation
        max_iterations: Safety limit on search iterations
        
    Returns:
        List of intersection IDs forming the path, or None if no route exists
        
    Example:
        >>> route = find_route("I0", "I8", network)
        >>> print(route)
        ['I0', 'I1', 'I4', 'I7', 'I8']
    """
    # Validate inputs
    if start not in network.graph or goal not in network.graph:
        return None
    
    if start == goal:
        return [start]
    
    # Priority queue: (f_score, counter, node, path)
    # Counter ensures FIFO ordering for equal f_scores
    counter = 0
    open_set = [(0.0, counter, start, [start])]
    
    # Track best g_score for each node
    g_scores: Dict[str, float] = {start: 0.0}
    
    # Track visited nodes
    closed_set: Set[str] = set()
    
    iterations = 0
    
    while open_set and iterations < max_iterations:
        iterations += 1
        
        # Pop node with lowest f_score
        f_score, _, current, path = heapq.heappop(open_set)
        
        # Skip if already processed
        if current in closed_set:
            continue
        
        # Goal test
        if current == goal:
            return path
        
        # Mark as visited
        closed_set.add(current)
        
        # Expand neighbors
        for neighbor in network.get_neighbors(current):
            if neighbor in closed_set:
                continue
            
            # Get road and calculate edge cost
            road = network.get_road(current, neighbor)
            if road is None or road.blocked:
                continue
            
            # g(neighbor) = g(current) + edge_cost
            edge_cost = road.get_edge_cost()
            tentative_g = g_scores[current] + edge_cost
            
            # Update if this is a better path
            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                
                # Calculate heuristic
                h_score = manhattan_distance(neighbor, goal, grid_size)
                
                # f(neighbor) = g(neighbor) + h(neighbor)
                f_score_neighbor = tentative_g + h_score
                
                # Add to open set
                counter += 1
                new_path = path + [neighbor]
                heapq.heappush(open_set, (f_score_neighbor, counter, neighbor, new_path))
    
    # No path found
    return None


def find_route_avoiding(
    start: str,
    goal: str,
    network,
    avoid_nodes: Optional[Set[str]] = None,
    grid_size: int = 3
) -> Optional[List[str]]:
    """
    Find route while avoiding specific intersections.
    
    Useful for testing alternate routes or avoiding congested areas.
    
    Args:
        start: Starting intersection
        goal: Goal intersection
        network: RoadNetwork instance
        avoid_nodes: Set of intersection IDs to avoid
        grid_size: Grid size for heuristic
        
    Returns:
        Path avoiding specified nodes, or None if impossible
    """
    if avoid_nodes is None:
        avoid_nodes = set()
    
    # Validate that start and goal are not in avoid set
    if start in avoid_nodes or goal in avoid_nodes:
        return None
    
    # Similar to find_route but skip avoided nodes
    counter = 0
    open_set = [(0.0, counter, start, [start])]
    g_scores = {start: 0.0}
    closed_set: Set[str] = set()
    
    while open_set:
        _, _, current, path = heapq.heappop(open_set)
        
        if current in closed_set:
            continue
        
        if current == goal:
            return path
        
        closed_set.add(current)
        
        for neighbor in network.get_neighbors(current):
            # Skip avoided nodes
            if neighbor in avoid_nodes or neighbor in closed_set:
                continue
            
            road = network.get_road(current, neighbor)
            if road is None or road.blocked:
                continue
            
            edge_cost = road.get_edge_cost()
            tentative_g = g_scores[current] + edge_cost
            
            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                h_score = manhattan_distance(neighbor, goal, grid_size)
                f_score = tentative_g + h_score
                
                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor, path + [neighbor]))
    
    return None


def verify_route(route: List[str], network) -> bool:
    """
    Verify that a route is valid (all roads exist and are not blocked).
    
    Args:
        route: List of intersection IDs
        network: RoadNetwork instance
        
    Returns:
        True if route is currently valid, False otherwise
    """
    if not route or len(route) < 2:
        return len(route) == 1  # Single-node route is valid
    
    for i in range(len(route) - 1):
        current = route[i]
        next_node = route[i + 1]
        
        road = network.get_road(current, next_node)
        if road is None or road.blocked:
            return False
    
    return True


def get_route_cost(route: List[str], network) -> float:
    """
    Calculate total cost of a route.
    
    Args:
        route: List of intersection IDs
        network: RoadNetwork instance
        
    Returns:
        Sum of edge costs along the route
    """
    if not route or len(route) < 2:
        return 0.0
    
    total_cost = 0.0
    for i in range(len(route) - 1):
        current = route[i]
        next_node = route[i + 1]
        
        road = network.get_road(current, next_node)
        if road:
            total_cost += road.get_edge_cost()
    
    return total_cost


def find_alternate_routes(
    start: str,
    goal: str,
    network,
    num_routes: int = 3,
    grid_size: int = 3
) -> List[List[str]]:
    """
    Find multiple alternate routes between two points.
    
    Uses k-shortest paths approach: find shortest path, then find paths
    avoiding nodes from previous paths.
    
    Args:
        start: Starting intersection
        goal: Goal intersection
        network: RoadNetwork instance
        num_routes: Maximum number of alternate routes to find
        grid_size: Grid size for heuristic
        
    Returns:
        List of routes (each route is a list of intersection IDs)
    """
    routes = []
    used_nodes: Set[str] = set()
    
    # Find first (shortest) route
    route = find_route(start, goal, network, grid_size)
    if route:
        routes.append(route)
        # Add intermediate nodes (not start/goal) to used set
        if len(route) > 2:
            used_nodes.update(route[1:-1])
    
    # Find alternate routes
    for _ in range(num_routes - 1):
        if not used_nodes:
            break
        
        # Try to find route avoiding previously used nodes
        alt_route = find_route_avoiding(start, goal, network, used_nodes, grid_size)
        if alt_route and alt_route not in routes:
            routes.append(alt_route)
            if len(alt_route) > 2:
                used_nodes.update(alt_route[1:-1])
        else:
            break
    
    return routes
