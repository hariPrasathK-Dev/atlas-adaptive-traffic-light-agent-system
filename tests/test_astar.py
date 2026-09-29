"""
Tests for A* Search Algorithm
"""

import pytest
from src.environment.road_network import generate_grid_network
from src.ai.astar import (
    find_route,
    find_route_avoiding,
    verify_route,
    get_route_cost,
    manhattan_distance
)


@pytest.fixture
def network_3x3():
    """Create a 3x3 test network."""
    return generate_grid_network(size=3)


@pytest.mark.unit
class TestManhattanDistance:
    """Test Manhattan distance heuristic."""
    
    def test_same_node(self):
        """Distance from node to itself should be 0."""
        assert manhattan_distance("I0", "I0", 3) == 0
    
    def test_adjacent_horizontal(self):
        """Distance between horizontal neighbors should be 1."""
        assert manhattan_distance("I0", "I1", 3) == 1
        assert manhattan_distance("I1", "I2", 3) == 1
    
    def test_adjacent_vertical(self):
        """Distance between vertical neighbors should be 1."""
        assert manhattan_distance("I0", "I3", 3) == 1
        assert manhattan_distance("I3", "I6", 3) == 1
    
    def test_diagonal(self):
        """Distance to diagonal should be 2 (Manhattan, not Euclidean)."""
        assert manhattan_distance("I0", "I4", 3) == 2
    
    def test_opposite_corners(self):
        """Distance between opposite corners should be 4."""
        assert manhattan_distance("I0", "I8", 3) == 4


@pytest.mark.unit
class TestFindRoute:
    """Test A* pathfinding."""
    
    def test_same_location(self, network_3x3):
        """Route from node to itself."""
        route = find_route("I0", "I0", network_3x3, grid_size=3)
        assert route == ["I0"]
    
    def test_adjacent_nodes(self, network_3x3):
        """Route between adjacent nodes."""
        route = find_route("I0", "I1", network_3x3, grid_size=3)
        assert route is not None
        assert route[0] == "I0"
        assert route[-1] == "I1"
        assert len(route) == 2
    
    def test_shortest_path(self, network_3x3):
        """Route should find shortest path."""
        route = find_route("I0", "I8", network_3x3, grid_size=3)
        assert route is not None
        assert route[0] == "I0"
        assert route[-1] == "I8"
        # Shortest path in 3x3 grid from corner to corner is 5 nodes
        assert len(route) == 5
    
    def test_blocked_road(self, network_3x3):
        """Should route around blocked road."""
        # Block direct path
        network_3x3.block_road("I0", "I1")
        
        route = find_route("I0", "I2", network_3x3, grid_size=3)
        assert route is not None
        # Should find alternate route
        assert "I1" not in route or route.index("I1") != 1
    
    def test_no_route(self, network_3x3):
        """Should return None if no route exists."""
        # Block all exits from I0
        network_3x3.block_road("I0", "I1")
        network_3x3.block_road("I0", "I3")
        
        route = find_route("I0", "I8", network_3x3, grid_size=3)
        assert route is None
    
    def test_invalid_nodes(self, network_3x3):
        """Should handle invalid node IDs."""
        route = find_route("I99", "I0", network_3x3, grid_size=3)
        assert route is None
        
        route = find_route("I0", "I99", network_3x3, grid_size=3)
        assert route is None


@pytest.mark.unit
class TestRouteUtilities:
    """Test route utility functions."""
    
    def test_verify_route_valid(self, network_3x3):
        """Verify a valid route."""
        route = ["I0", "I1", "I2"]
        assert verify_route(route, network_3x3) is True
    
    def test_verify_route_blocked(self, network_3x3):
        """Invalid route with blocked road."""
        network_3x3.block_road("I0", "I1")
        route = ["I0", "I1", "I2"]
        assert verify_route(route, network_3x3) is False
    
    def test_verify_route_invalid_edge(self, network_3x3):
        """Invalid route with non-existent edge."""
        route = ["I0", "I8"]  # No direct connection
        assert verify_route(route, network_3x3) is False
    
    def test_get_route_cost(self, network_3x3):
        """Calculate route cost."""
        route = ["I0", "I1", "I2"]
        cost = get_route_cost(route, network_3x3)
        assert cost > 0
        # Cost should be sum of road lengths (default 100 each)
        assert cost >= 200
    
    def test_find_route_avoiding(self, network_3x3):
        """Find route while avoiding specific nodes."""
        avoid = {"I1"}
        route = find_route_avoiding("I0", "I2", network_3x3, avoid, grid_size=3)
        assert route is not None
        assert "I1" not in route


@pytest.mark.integration
def test_rerouting_scenario(network_3x3):
    """Test complete rerouting scenario."""
    # Find initial route
    route1 = find_route("I0", "I8", network_3x3, grid_size=3)
    assert route1 is not None
    
    # Verify route is valid
    assert verify_route(route1, network_3x3)
    
    # Block a road on the route
    if len(route1) >= 2:
        network_3x3.block_road(route1[0], route1[1])
        
        # Original route should now be invalid
        assert not verify_route(route1, network_3x3)
        
        # Find new route
        route2 = find_route("I0", "I8", network_3x3, grid_size=3)
        
        # Should find alternate route
        assert route2 is not None
        assert verify_route(route2, network_3x3)
        assert route2 != route1
