"""
Vehicle Agent for ATLAS
Autonomous vehicle that plans routes and navigates the network
"""

from typing import Optional, List
from enum import Enum
from mesa import Agent

from ..ai.astar import find_route, verify_route


class VehicleState(Enum):
    """Vehicle operational states."""
    PLANNING = "planning"      # Planning initial route
    MOVING = "moving"          # Traveling along route
    WAITING = "waiting"        # Stopped at red signal
    REROUTING = "rerouting"    # Recalculating route due to blockage
    COMPLETED = "completed"    # Reached destination
    STUCK = "stuck"            # No valid route available


class VehicleAgent(Agent):
    """
    Autonomous vehicle agent that uses A* search for routing.
    
    The vehicle:
    1. Plans a route using A* when spawned
    2. Follows the route intersection by intersection
    3. Waits at red signals
    4. Reroutes if the path becomes blocked
    5. Completes when reaching the destination
    
    PEAS for Vehicle:
    - Performance: Minimize travel time, reach destination
    - Environment: Road network, traffic signals, other vehicles
    - Actuators: Move to next intersection
    - Sensors: Current position, route validity, signal state
    """
    
    def __init__(
        self,
        model,
        unique_id: str,
        source: str,
        destination: str,
        speed: float = 50.0  # km/h
    ):
        """
        Initialize vehicle agent.
        
        Args:
            model: ATLASSimulation instance
            unique_id: Unique vehicle identifier (e.g., "V0")
            source: Starting intersection ID
            destination: Goal intersection ID
            speed: Vehicle speed in km/h
        """
        super().__init__(model)
        
        # Identity
        self.vehicle_id = unique_id
        
        # Location
        self.source = source
        self.destination = destination
        self.current_node = source
        
        # Route planning
        self.route: Optional[List[str]] = None
        self.route_index = 0
        
        # State
        self.state = VehicleState.PLANNING
        self.speed = speed
        
        # Statistics
        self.waiting_time = 0
        self.total_travel_time = 0
        self.distance_traveled = 0.0
        self.reroute_count = 0
        
        # Current road
        self.current_road = None
        
        # Plan initial route
        self._plan_route()
    
    def _plan_route(self) -> bool:
        """
        Plan route from current position to destination using A*.
        
        Returns:
            True if route was found, False otherwise
        """
        self.route = find_route(
            self.current_node,
            self.destination,
            self.model.network,
            grid_size=self.model.grid_size
        )
        
        if self.route:
            self.route_index = 0
            self.state = VehicleState.MOVING
            return True
        else:
            self.state = VehicleState.STUCK
            return False
    
    def _reroute(self) -> bool:
        """
        Recalculate route due to blockage or invalid path.
        
        Returns:
            True if new route found, False if stuck
        """
        self.state = VehicleState.REROUTING
        self.reroute_count += 1
        
        success = self._plan_route()
        
        if not success:
            self.state = VehicleState.STUCK
        
        return success
    
    def _get_next_node(self) -> Optional[str]:
        """
        Get next intersection on the route.
        
        Returns:
            Next intersection ID, or None if at end of route
        """
        if not self.route or self.route_index >= len(self.route) - 1:
            return None
        
        return self.route[self.route_index + 1]
    
    def _can_move_to_next(self) -> bool:
        """
        Check if vehicle can move to next intersection.
        
        Considers:
        - Route validity
        - Road availability (not blocked, not at capacity)
        - Traffic signal state
        
        Returns:
            True if movement is allowed, False otherwise
        """
        next_node = self._get_next_node()
        if next_node is None:
            return False
        
        # Check if road exists and is not blocked
        road = self.model.network.get_road(self.current_node, next_node)
        if road is None or road.blocked:
            return False
        
        # Check road capacity
        if road.is_full:
            return False
        
        # Check traffic signal
        if self.current_node in self.model.signal_agents:
            signal = self.model.signal_agents[self.current_node]
            
            # Determine approach direction for traffic signal control.
            # Signal controls incoming approach roads. If vehicle is on an approach road,
            # check permission for that approach road's direction.
            from ..environment.road_network import get_direction
            if self.current_road:
                direction = get_direction(self.current_road.source, self.current_road.destination, self.model.grid_size)
            else:
                direction = get_direction(self.current_node, next_node, self.model.grid_size)
            
            if direction:
                # Check if signal allows movement in this direction
                if not signal.can_vehicle_move(direction):
                    return False
        
        return True
    
    def _move_to_next(self):
        """Execute movement to next intersection."""
        next_node = self._get_next_node()
        if next_node is None:
            return
        
        # Get road
        road = self.model.network.get_road(self.current_node, next_node)
        if road is None:
            return
        
        # Remove from current road if on one
        if self.current_road:
            self.current_road.remove_vehicle(self.vehicle_id)
        
        # Add to new road
        if road.add_vehicle(self.vehicle_id):
            self.current_road = road
            
            # Update statistics
            self.distance_traveled += road.length
            
            # Move to next node
            self.current_node = next_node
            self.route_index += 1
            
            # Check if reached destination
            if self.current_node == self.destination:
                self.state = VehicleState.COMPLETED
                self._complete_journey()
    
    def _complete_journey(self):
        """Handle journey completion."""
        # Remove from final road
        if self.current_road:
            self.current_road.remove_vehicle(self.vehicle_id)
            self.current_road = None
        
        # Notify simulation
        self.model.mark_vehicle_completed(self)
        
        # Remove from simulation
        self.model.remove_vehicle_agent(self.vehicle_id)
    
    def step(self):
        """
        Execute one simulation step.
        
        Vehicle behavior by state:
        - PLANNING: Plan initial route
        - MOVING: Try to move to next intersection
        - WAITING: Wait at red signal, increment wait time
        - REROUTING: Recalculate route
        - COMPLETED: Journey done, agent will be removed
        - STUCK: No valid route, agent is stuck
        """
        # Increment travel time
        self.total_travel_time += 1
        
        if self.state == VehicleState.PLANNING:
            self._plan_route()
        
        elif self.state == VehicleState.MOVING:
            # Verify route is still valid
            if not verify_route(self.route[self.route_index:], self.model.network):
                self._reroute()
                return
            
            # Try to move
            if self._can_move_to_next():
                self._move_to_next()
            else:
                # Blocked by signal or congestion
                self.state = VehicleState.WAITING
                self.waiting_time += 1
        
        elif self.state == VehicleState.WAITING:
            # Try to move again
            if self._can_move_to_next():
                self.state = VehicleState.MOVING
                self._move_to_next()
            else:
                # Still waiting
                self.waiting_time += 1
        
        elif self.state == VehicleState.REROUTING:
            # Already handled by _reroute()
            pass
        
        elif self.state == VehicleState.STUCK:
            # Try to reroute periodically
            if self.total_travel_time % 10 == 0:
                self._reroute()
        
        elif self.state == VehicleState.COMPLETED:
            # Should have been removed
            pass
    
    def get_status(self) -> dict:
        """
        Get current vehicle status.
        
        Returns:
            Dictionary with vehicle information
        """
        return {
            'vehicle_id': self.vehicle_id,
            'state': self.state.value,
            'current_node': self.current_node,
            'destination': self.destination,
            'route_progress': f"{self.route_index}/{len(self.route) if self.route else 0}",
            'waiting_time': self.waiting_time,
            'travel_time': self.total_travel_time,
            'distance': self.distance_traveled,
            'reroutes': self.reroute_count
        }
    
    def get_remaining_route(self) -> List[str]:
        """
        Get remaining portion of route.
        
        Returns:
            List of intersection IDs from current position to destination
        """
        if self.route and self.route_index < len(self.route):
            return self.route[self.route_index:]
        return []
