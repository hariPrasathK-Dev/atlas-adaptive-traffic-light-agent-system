"""
Traffic Signal Agent for ATLAS
Autonomous intersection controller with safe phase transitions
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from mesa import Agent
from collections import defaultdict


class SignalPhase(Enum):
    """Traffic signal phases following safe transition rules."""
    NS_GREEN = "ns_green"           # North-South has green
    NS_YELLOW = "ns_yellow"         # North-South yellow transition
    ALL_RED_NS = "all_red_ns"       # All-red clearance after NS
    EW_GREEN = "ew_green"           # East-West has green
    EW_YELLOW = "ew_yellow"         # East-West yellow transition
    ALL_RED_EW = "all_red_ew"       # All-red clearance after EW


# Safe phase transition rules
PHASE_TRANSITIONS = {
    SignalPhase.NS_GREEN: SignalPhase.NS_YELLOW,
    SignalPhase.NS_YELLOW: SignalPhase.ALL_RED_NS,
    SignalPhase.ALL_RED_NS: SignalPhase.EW_GREEN,
    SignalPhase.EW_GREEN: SignalPhase.EW_YELLOW,
    SignalPhase.EW_YELLOW: SignalPhase.ALL_RED_EW,
    SignalPhase.ALL_RED_EW: SignalPhase.NS_GREEN
}


class SignalAgent(Agent):
    """
    Autonomous traffic signal agent.
    
    PEAS for Signal Agent:
    - Performance: Minimize wait time, queue length, maximize throughput
    - Environment: Intersection, incoming roads, vehicles, neighbor signals
    - Actuators: Change signal phase (with safety constraints)
    - Sensors: Queue lengths, waiting times, neighbor messages
    
    The agent:
    1. Observes local traffic (queues, wait times)
    2. Receives messages from neighbor intersections
    3. Uses a controller (Fixed or Adaptive) to decide actions
    4. Changes phases following safety rules
    5. Sends state updates to neighbors
    """
    
    def __init__(
        self,
        model,
        unique_id: str,
        intersection_id: str,
        controller,
        config: Dict[str, Any]
    ):
        """
        Initialize traffic signal agent.
        
        Args:
            model: ATLASSimulation instance
            unique_id: Unique agent identifier
            intersection_id: Intersection this signal controls
            controller: Controller instance (Fixed or Adaptive)
            config: Configuration dictionary
        """
        super().__init__(model)
        
        # Identity
        self.intersection_id = intersection_id
        
        # Controller
        self.controller = controller
        
        # Configuration
        signal_config = config.get('signal', {})
        self.min_green_time = signal_config.get('min_green', 10)
        self.max_green_time = signal_config.get('max_green', 45)
        self.yellow_time = signal_config.get('yellow', 3)
        self.all_red_time = signal_config.get('all_red', 1)
        
        # Signal state
        self.current_phase = SignalPhase.NS_GREEN
        self.phase_elapsed = 0
        
        # Traffic observations
        self.queue_state: Dict[str, int] = defaultdict(int)
        self.wait_state: Dict[str, List[float]] = defaultdict(list)
        
        # Neighbor coordination
        self.neighbors = model.network.get_neighbors(intersection_id)
        self.neighbor_states: Dict[str, Dict] = {}
        
        # Failure simulation
        self.sensor_enabled = True
        self.communication_enabled = True
        
        # Statistics
        self.phase_changes = 0
        self.total_vehicles_served = 0
    
    def can_vehicle_move(self, direction: str) -> bool:
        """
        Check if vehicles can move in a given direction.
        
        Args:
            direction: Cardinal direction ("north", "south", "east", "west")
            
        Returns:
            True if direction has green light, False otherwise
        """
        if direction in ["north", "south"]:
            return self.current_phase == SignalPhase.NS_GREEN
        elif direction in ["east", "west"]:
            return self.current_phase == SignalPhase.EW_GREEN
        return False
    
    def _update_observations(self):
        """Update traffic observations from environment."""
        if not self.sensor_enabled:
            # Sensor failure: use cached/estimated values
            return
        
        # Reset observations
        self.queue_state.clear()
        for direction in self.wait_state:
            self.wait_state[direction].clear()
        
        # Get incoming roads
        incoming_roads = self.model.network.get_incoming_roads(self.intersection_id)
        
        for road in incoming_roads:
            # Determine direction
            from ..environment.road_network import get_direction
            direction = get_direction(road.source, road.destination, self.model.grid_size)
            
            if direction:
                # Count vehicles waiting on this road
                self.queue_state[direction] = len(road.vehicles)
                
                # Collect waiting times
                for vehicle_id in road.vehicles:
                    if vehicle_id in self.model.vehicle_agents:
                        vehicle = self.model.vehicle_agents[vehicle_id]
                        self.wait_state[direction].append(vehicle.waiting_time)
    
    def _get_average_wait(self, direction: str) -> float:
        """
        Get average waiting time for a direction.
        
        Args:
            direction: Cardinal direction
            
        Returns:
            Average waiting time in timesteps
        """
        waits = self.wait_state.get(direction, [])
        if not waits:
            return 0.0
        return sum(waits) / len(waits)
    
    def _get_ns_pressure(self) -> float:
        """Calculate combined North-South pressure."""
        ns_queue = self.queue_state.get('north', 0) + self.queue_state.get('south', 0)
        ns_wait = (self._get_average_wait('north') + self._get_average_wait('south')) / 2
        return ns_queue * ns_wait
    
    def _get_ew_pressure(self) -> float:
        """Calculate combined East-West pressure."""
        ew_queue = self.queue_state.get('east', 0) + self.queue_state.get('west', 0)
        ew_wait = (self._get_average_wait('east') + self._get_average_wait('west')) / 2
        return ew_queue * ew_wait
    
    def _build_observation(self) -> Dict[str, Any]:
        """
        Build observation dictionary for controller.
        
        Returns:
            Dictionary with all relevant observations
        """
        observation = {
            'intersection_id': self.intersection_id,
            'current_phase': self.current_phase.value,
            'phase_elapsed': self.phase_elapsed,
            
            # Timing constraints
            'min_green': self.min_green_time,
            'max_green': self.max_green_time,
            'yellow_time': self.yellow_time,
            'all_red_time': self.all_red_time,
            
            # Local observations
            'ns_queue': self.queue_state.get('north', 0) + self.queue_state.get('south', 0),
            'ew_queue': self.queue_state.get('east', 0) + self.queue_state.get('west', 0),
            'ns_avg_wait': (self._get_average_wait('north') + self._get_average_wait('south')) / 2,
            'ew_avg_wait': (self._get_average_wait('east') + self._get_average_wait('west')) / 2,
            
            # Neighbor coordination (if available)
            'ns_downstream_pressure': self._get_neighbor_pressure(['north', 'south']),
            'ew_downstream_pressure': self._get_neighbor_pressure(['east', 'west']),
        }
        
        return observation
    
    def _get_neighbor_pressure(self, directions: List[str]) -> Optional[float]:
        """
        Get downstream pressure from neighbors in given directions.
        
        Args:
            directions: List of directions to check
            
        Returns:
            Average pressure from neighbors, or None if no data
        """
        if not self.communication_enabled:
            return None
        
        pressures = []
        for neighbor_id, state in self.neighbor_states.items():
            # Check if this neighbor is in one of the relevant directions
            from ..environment.road_network import get_direction
            direction = get_direction(self.intersection_id, neighbor_id, self.model.grid_size)
            
            if direction in directions:
                pressure = state.get('pressure', 0.0)
                pressures.append(pressure)
        
        if not pressures:
            return None
        
        return sum(pressures) / len(pressures)
    
    def _execute_action(self, action: str):
        """
        Execute controller action.
        
        Args:
            action: One of "MAINTAIN", "EXTEND", or "SWITCH"
        """
        if action == "SWITCH":
            # Transition to next phase
            next_phase = PHASE_TRANSITIONS[self.current_phase]
            self.current_phase = next_phase
            self.phase_elapsed = 0
            self.phase_changes += 1
        else:
            # MAINTAIN or EXTEND: just increment time
            self.phase_elapsed += 1
    
    def _send_state_to_neighbors(self):
        """Send current state to neighboring intersections."""
        if not self.communication_enabled:
            return
        
        # Get message bus (will be implemented in task 6)
        # For now, directly update neighbor states
        message = {
            'sender': self.intersection_id,
            'timestamp': self.model.current_step,
            'phase': self.current_phase.value,
            'pressure': self._get_ns_pressure() + self._get_ew_pressure(),
            'ns_queue': self.queue_state.get('north', 0) + self.queue_state.get('south', 0),
            'ew_queue': self.queue_state.get('east', 0) + self.queue_state.get('west', 0)
        }
        
        # Store for neighbors to access
        for neighbor_id in self.neighbors:
            if neighbor_id in self.model.signal_agents:
                neighbor = self.model.signal_agents[neighbor_id]
                neighbor.neighbor_states[self.intersection_id] = message
    
    def step(self):
        """
        Execute one simulation step.
        
        Agent behavior:
        1. Update observations (sense)
        2. Build observation for controller
        3. Get action from controller (deliberate)
        4. Execute action (act)
        5. Send state to neighbors (communicate)
        """
        # Sense: Update observations
        self._update_observations()
        
        # Deliberate: Get controller decision
        observation = self._build_observation()
        action = self.controller.get_action(observation)
        
        # Act: Execute action
        self._execute_action(action)
        
        # Communicate: Send state to neighbors
        self._send_state_to_neighbors()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current signal status.
        
        Returns:
            Dictionary with signal information
        """
        return {
            'intersection_id': self.intersection_id,
            'phase': self.current_phase.value,
            'phase_elapsed': self.phase_elapsed,
            'ns_queue': self.queue_state.get('north', 0) + self.queue_state.get('south', 0),
            'ew_queue': self.queue_state.get('east', 0) + self.queue_state.get('west', 0),
            'phase_changes': self.phase_changes,
            'sensor_enabled': self.sensor_enabled,
            'communication_enabled': self.communication_enabled,
            'neighbors': len(self.neighbors)
        }
    
    def get_queue_info(self) -> Dict[str, int]:
        """Get detailed queue information by direction."""
        return dict(self.queue_state)
    
    def disable_sensor(self):
        """Simulate sensor failure."""
        self.sensor_enabled = False
    
    def enable_sensor(self):
        """Re-enable sensor."""
        self.sensor_enabled = True
    
    def disable_communication(self):
        """Simulate communication failure."""
        self.communication_enabled = False
    
    def enable_communication(self):
        """Re-enable communication."""
        self.communication_enabled = True
