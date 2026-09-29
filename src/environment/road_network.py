"""
Road Network Module
Defines roads, intersections, and graph structure for ATLAS
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import networkx as nx
import numpy as np


@dataclass
class Road:
    """
    Represents a directed road segment between two intersections.
    
    Attributes:
        source: Starting intersection ID
        destination: Ending intersection ID
        length: Road length in meters
        capacity: Maximum vehicles the road can hold
        speed_limit: Speed limit in km/h
        blocked: Whether the road is blocked (incident)
        vehicles: List of vehicle IDs currently on this road
    """
    source: str
    destination: str
    length: float = 100.0
    capacity: int = 20
    speed_limit: float = 50.0
    blocked: bool = False
    vehicles: List[str] = field(default_factory=list)
    
    @property
    def congestion_ratio(self) -> float:
        """Calculate current congestion as ratio of vehicles to capacity."""
        return len(self.vehicles) / max(self.capacity, 1)
    
    @property
    def is_full(self) -> bool:
        """Check if road has reached capacity."""
        return len(self.vehicles) >= self.capacity
    
    @property
    def travel_time(self) -> float:
        """
        Calculate travel time considering congestion.
        Returns time in simulation timesteps.
        """
        # Base travel time = length / speed
        base_time = (self.length / 1000.0) / (self.speed_limit / 3600.0)
        
        # Increase travel time based on congestion
        congestion_factor = 1.0 + (2.0 * self.congestion_ratio)
        
        return base_time * congestion_factor
    
    def add_vehicle(self, vehicle_id: str) -> bool:
        """
        Add a vehicle to this road.
        
        Args:
            vehicle_id: Unique vehicle identifier
            
        Returns:
            True if vehicle was added, False if road is full or blocked
        """
        if self.blocked or self.is_full:
            return False
        
        if vehicle_id not in self.vehicles:
            self.vehicles.append(vehicle_id)
        return True
    
    def remove_vehicle(self, vehicle_id: str) -> bool:
        """
        Remove a vehicle from this road.
        
        Args:
            vehicle_id: Vehicle identifier to remove
            
        Returns:
            True if vehicle was removed, False if not found
        """
        if vehicle_id in self.vehicles:
            self.vehicles.remove(vehicle_id)
            return True
        return False
    
    def get_edge_cost(self) -> float:
        """
        Calculate edge cost for pathfinding (A*).
        Higher cost for congested roads.
        
        Returns:
            Cost value considering length and congestion
        """
        if self.blocked:
            return float('inf')
        
        # Cost = length * (1 + congestion_ratio)
        return self.length * (1.0 + self.congestion_ratio)


class RoadNetwork:
    """
    Manages the urban road network as a directed graph.
    
    The network is represented as a NetworkX DiGraph where:
    - Nodes are intersections
    - Edges are roads with associated Road objects
    """
    
    def __init__(self):
        """Initialize an empty road network."""
        self.graph = nx.DiGraph()
        self.roads: Dict[Tuple[str, str], Road] = {}
        self.intersections: List[str] = []
    
    def add_intersection(self, intersection_id: str, x: float = 0, y: float = 0):
        """
        Add an intersection to the network.
        
        Args:
            intersection_id: Unique intersection identifier (e.g., "I1")
            x: X coordinate for visualization
            y: Y coordinate for visualization
        """
        if intersection_id not in self.graph:
            self.graph.add_node(intersection_id, x=x, y=y)
            self.intersections.append(intersection_id)
    
    def add_road(self, road: Road):
        """
        Add a road (directed edge) to the network.
        
        Args:
            road: Road object to add
        """
        # Ensure intersections exist
        if road.source not in self.graph:
            self.add_intersection(road.source)
        if road.destination not in self.graph:
            self.add_intersection(road.destination)
        
        # Add edge with Road object as attribute
        self.graph.add_edge(
            road.source,
            road.destination,
            road=road,
            weight=road.get_edge_cost()
        )
        
        # Store road reference
        self.roads[(road.source, road.destination)] = road
    
    def get_road(self, source: str, destination: str) -> Optional[Road]:
        """
        Get road between two intersections.
        
        Args:
            source: Source intersection ID
            destination: Destination intersection ID
            
        Returns:
            Road object if exists, None otherwise
        """
        return self.roads.get((source, destination))
    
    def get_neighbors(self, intersection_id: str) -> List[str]:
        """
        Get neighboring intersections (outgoing connections).
        
        Args:
            intersection_id: Intersection to get neighbors for
            
        Returns:
            List of neighbor intersection IDs
        """
        if intersection_id in self.graph:
            return list(self.graph.successors(intersection_id))
        return []
    
    def get_incoming_roads(self, intersection_id: str) -> List[Road]:
        """
        Get all roads leading into an intersection.
        
        Args:
            intersection_id: Target intersection
            
        Returns:
            List of incoming Road objects
        """
        roads = []
        if intersection_id in self.graph:
            for pred in self.graph.predecessors(intersection_id):
                road = self.get_road(pred, intersection_id)
                if road:
                    roads.append(road)
        return roads
    
    def get_outgoing_roads(self, intersection_id: str) -> List[Road]:
        """
        Get all roads leading out of an intersection.
        
        Args:
            intersection_id: Source intersection
            
        Returns:
            List of outgoing Road objects
        """
        roads = []
        if intersection_id in self.graph:
            for succ in self.graph.successors(intersection_id):
                road = self.get_road(intersection_id, succ)
                if road:
                    roads.append(road)
        return roads
    
    def update_edge_weights(self):
        """Update all edge weights based on current road costs."""
        for (source, dest), road in self.roads.items():
            if self.graph.has_edge(source, dest):
                self.graph[source][dest]['weight'] = road.get_edge_cost()
    
    def block_road(self, source: str, destination: str):
        """
        Block a road (simulate incident).
        
        Args:
            source: Source intersection
            destination: Destination intersection
        """
        road = self.get_road(source, destination)
        if road:
            road.blocked = True
            self.update_edge_weights()
    
    def unblock_road(self, source: str, destination: str):
        """
        Unblock a previously blocked road.
        
        Args:
            source: Source intersection
            destination: Destination intersection
        """
        road = self.get_road(source, destination)
        if road:
            road.blocked = False
            self.update_edge_weights()
    
    def get_position(self, intersection_id: str) -> Tuple[float, float]:
        """
        Get visual position of an intersection.
        
        Args:
            intersection_id: Intersection identifier
            
        Returns:
            (x, y) coordinates
        """
        if intersection_id in self.graph:
            node_data = self.graph.nodes[intersection_id]
            return node_data.get('x', 0), node_data.get('y', 0)
        return (0.0, 0.0)
    
    def get_statistics(self) -> Dict:
        """
        Get network statistics.
        
        Returns:
            Dictionary with network metrics
        """
        total_vehicles = sum(len(road.vehicles) for road in self.roads.values())
        congested_roads = sum(1 for road in self.roads.values() if road.congestion_ratio > 0.7)
        blocked_roads = sum(1 for road in self.roads.values() if road.blocked)
        
        return {
            'num_intersections': len(self.intersections),
            'num_roads': len(self.roads),
            'total_vehicles_on_roads': total_vehicles,
            'congested_roads': congested_roads,
            'blocked_roads': blocked_roads,
            'avg_congestion': np.mean([road.congestion_ratio for road in self.roads.values()]) if self.roads else 0.0
        }


def generate_grid_network(
    size: int = 3,
    road_length: float = 100.0,
    road_capacity: int = 20,
    speed_limit: float = 50.0
) -> RoadNetwork:
    """
    Generate a square grid road network.
    
    Creates a size × size grid of intersections with bidirectional roads.
    Intersections are named I0, I1, I2, ..., I(size²-1).
    
    Args:
        size: Grid dimensions (size × size)
        road_length: Default length for all roads (meters)
        road_capacity: Maximum vehicles per road
        speed_limit: Speed limit for all roads (km/h)
        
    Returns:
        RoadNetwork with grid topology
        
    Example:
        3×3 grid creates 9 intersections:
        I0 - I1 - I2
        |    |    |
        I3 - I4 - I5
        |    |    |
        I6 - I7 - I8
    """
    network = RoadNetwork()
    
    # Create intersections with positions
    for row in range(size):
        for col in range(size):
            intersection_id = f"I{row * size + col}"
            x = col * 200.0  # Visual spacing
            y = row * 200.0
            network.add_intersection(intersection_id, x=x, y=y)
    
    # Create bidirectional roads
    for row in range(size):
        for col in range(size):
            current_id = f"I{row * size + col}"
            
            # Horizontal roads (East-West)
            if col < size - 1:
                east_id = f"I{row * size + col + 1}"
                
                # Road going East
                network.add_road(Road(
                    source=current_id,
                    destination=east_id,
                    length=road_length,
                    capacity=road_capacity,
                    speed_limit=speed_limit
                ))
                
                # Road going West
                network.add_road(Road(
                    source=east_id,
                    destination=current_id,
                    length=road_length,
                    capacity=road_capacity,
                    speed_limit=speed_limit
                ))
            
            # Vertical roads (North-South)
            if row < size - 1:
                south_id = f"I{(row + 1) * size + col}"
                
                # Road going South
                network.add_road(Road(
                    source=current_id,
                    destination=south_id,
                    length=road_length,
                    capacity=road_capacity,
                    speed_limit=speed_limit
                ))
                
                # Road going North
                network.add_road(Road(
                    source=south_id,
                    destination=current_id,
                    length=road_length,
                    capacity=road_capacity,
                    speed_limit=speed_limit
                ))
    
    return network


def get_direction(source: str, destination: str, grid_size: int = 3) -> Optional[str]:
    """
    Determine cardinal direction between two intersections in a grid.
    
    Args:
        source: Source intersection ID (e.g., "I4")
        destination: Destination intersection ID (e.g., "I5")
        grid_size: Size of the grid
        
    Returns:
        Direction string: "north", "south", "east", "west", or None
    """
    try:
        source_idx = int(source[1:])
        dest_idx = int(destination[1:])
        
        diff = dest_idx - source_idx
        
        if diff == 1:  # Moving right
            return "east"
        elif diff == -1:  # Moving left
            return "west"
        elif diff == grid_size:  # Moving down
            return "south"
        elif diff == -grid_size:  # Moving up
            return "north"
        
    except (ValueError, IndexError):
        pass
    
    return None
