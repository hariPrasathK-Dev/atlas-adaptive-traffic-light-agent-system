"""
ATLAS Simulation Engine
Core simulation controller using Mesa framework
"""

from typing import Dict, List, Optional, Any
import random
from mesa import Model
import numpy as np

from .road_network import RoadNetwork, generate_grid_network


class ATLASSimulation(Model):
    """
    Main simulation model for ATLAS.
    
    Manages the simulation clock, agent scheduling, and global state.
    Uses Mesa's Model class for agent-based simulation framework.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        random_seed: Optional[int] = None
    ):
        """
        Initialize ATLAS simulation.
        
        Args:
            config: Configuration dictionary with simulation parameters
            random_seed: Random seed for reproducibility
        """
        super().__init__()
        
        # Configuration
        self.config = config
        self.grid_size = config.get('simulation', {}).get('grid_size', 3)
        self.duration = config.get('simulation', {}).get('duration', 300)
        
        # Random seed for reproducibility
        if random_seed is not None:
            self.random_seed = random_seed
            random.seed(random_seed)
            np.random.seed(random_seed)
        else:
            self.random_seed = config.get('simulation', {}).get('random_seed', 42)
            random.seed(self.random_seed)
            np.random.seed(self.random_seed)
        
        # Simulation state
        self.current_step = 0
        self.running = True
        self.paused = False
        
        # Generate road network
        road_config = config.get('road', {})
        self.network = generate_grid_network(
            size=self.grid_size,
            road_length=road_config.get('default_length', 100.0),
            road_capacity=road_config.get('default_capacity', 20),
            speed_limit=road_config.get('default_speed_limit', 50.0)
        )
        
        # Agent collections (Mesa 3.x manages agents directly)
        self.signal_agents = {}  # intersection_id -> SignalAgent
        self.vehicle_agents = {}  # vehicle_id -> VehicleAgent
        
        # Communication
        from ..communication.message_bus import MessageBus
        self.message_bus = MessageBus()
        
        # Metrics and logging
        from ..metrics.collector import MetricsCollector
        from ..metrics.decision_log import DecisionLogger
        self.metrics = MetricsCollector()
        self.decision_log = DecisionLogger()
        
        # Controller type
        self.controller_type = "fixed"  # "fixed" or "adaptive"
        
        # Initialize signal agents
        self._initialize_signals()
        
        # Vehicle generation
        self.arrival_rate = config.get('traffic', {}).get('normal_arrival_rate', 1.0)
        self.vehicle_counter = 0
        
        # Scenario state
        self.scenario_name = "normal"
        self.incidents: List[Dict] = []
        self.sensor_failures: List[str] = []
        self.comm_failures: List[tuple] = []
        
        # Statistics
        self.completed_vehicles = []
        self.total_vehicles_spawned = 0
        
    def reset(self):
        """Reset simulation to initial state."""
        # Reset timing
        self.current_step = 0
        self.running = True
        self.paused = False
        
        # Reset random seed
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
        
        # Remove all agents via Mesa 3.x API, then clear dicts
        for agent in list(self.signal_agents.values()):
            agent.remove()
        for agent in list(self.vehicle_agents.values()):
            agent.remove()
        self.signal_agents.clear()
        self.vehicle_agents.clear()
        
        # Regenerate network
        road_config = self.config.get('road', {})
        self.network = generate_grid_network(
            size=self.grid_size,
            road_length=road_config.get('default_length', 100.0),
            road_capacity=road_config.get('default_capacity', 20),
            speed_limit=road_config.get('default_speed_limit', 50.0)
        )
        
        # Reinitialize signals
        self._initialize_signals()
        
        # Reset stats
        self.vehicle_counter = 0
        self.completed_vehicles.clear()
        self.total_vehicles_spawned = 0
        
        # Reset metrics and logs
        self.metrics.reset()
        self.decision_log.reset()
        self.message_bus.clear_all()
        self.message_bus.reset_statistics()
        
        # Clear scenario events
        self.incidents.clear()
        self.sensor_failures.clear()
        self.comm_failures.clear()
    
    def step(self):
        """
        Execute one simulation timestep.
        
        Order of operations:
        1. Generate new vehicles (stochastic arrivals)
        2. Update road edge weights (congestion)
        3. Step all agents (signals decide, vehicles move)
        4. Process scenario events
        5. Update metrics
        6. Advance time
        """
        if not self.running or self.paused:
            return
        
        # Generate vehicles based on arrival rate
        self._spawn_vehicles()
        
        # Update road costs for pathfinding
        self.network.update_edge_weights()
        
        # Step all agents (Mesa 3.x direct iteration)
        # First step signal agents, then vehicle agents
        for agent in list(self.signal_agents.values()):
            agent.step()
        for agent in list(self.vehicle_agents.values()):
            agent.step()
        
        # Collect metrics
        self.metrics.collect(self)
        
        # Process scheduled events
        self._process_events()
        
        # Advance time
        self.current_step += 1
        
        # Check termination
        if self.current_step >= self.duration:
            self.running = False
    
    def _spawn_vehicles(self):
        """Generate new vehicles based on arrival rate."""
        # Poisson arrival process
        num_arrivals = np.random.poisson(self.arrival_rate)
        
        for _ in range(num_arrivals):
            self._create_vehicle()
    
    def _initialize_signals(self):
        """Create signal agents for all intersections."""
        from ..agents.signal_agent import SignalAgent
        from ..ai.fixed_controller import FixedTimeController
        from ..ai.adaptive_controller import AdaptiveController
        
        # Choose controller type
        if self.controller_type == "adaptive":
            controller_class = AdaptiveController
        else:
            controller_class = FixedTimeController
        
        # Create signal for each intersection
        for intersection_id in self.network.intersections:
            controller = controller_class(self.config)
            
            signal = SignalAgent(
                model=self,
                unique_id=f"Signal_{intersection_id}",
                intersection_id=intersection_id,
                controller=controller,
                config=self.config
            )
            
            self.add_signal_agent(signal)
    
    def set_controller_type(self, controller_type: str):
        """
        Change controller type and reinitialize signals.
        
        Args:
            controller_type: "fixed" or "adaptive"
        """
        if controller_type not in ["fixed", "adaptive"]:
            raise ValueError("Controller type must be 'fixed' or 'adaptive'")
        
        self.controller_type = controller_type
        
        # Reinitialize signals with new controller
        self.signal_agents.clear()
        self._initialize_signals()
    
    def _create_vehicle(self) -> Optional[str]:
        """
        Create a new vehicle agent.
        
        Returns:
            Vehicle ID if created, None if failed
        """
        from ..agents.vehicle_agent import VehicleAgent
        
        # Select random source and destination
        intersections = self.network.intersections
        if len(intersections) < 2:
            return None
        
        source = random.choice(intersections)
        destination = random.choice([i for i in intersections if i != source])
        
        vehicle_id = f"V{self.vehicle_counter}"
        self.vehicle_counter += 1
        self.total_vehicles_spawned += 1
        
        # Create vehicle agent
        vehicle = VehicleAgent(
            model=self,
            unique_id=vehicle_id,
            source=source,
            destination=destination
        )
        
        # Add to simulation
        self.add_vehicle_agent(vehicle)
        
        return vehicle_id
    
    def _process_events(self):
        """Process scheduled scenario events (incidents, failures)."""
        # Check for incidents scheduled at current timestep
        for incident in self.incidents:
            if incident.get('timestep') == self.current_step:
                source = incident.get('source')
                destination = incident.get('destination')
                if source and destination:
                    self.network.block_road(source, destination)
        
        # Apply sensor failures
        for intersection_id in self.sensor_failures:
            if intersection_id in self.signal_agents:
                self.signal_agents[intersection_id].disable_sensor()
        
        # Apply communication failures
        for (sender, receiver) in self.comm_failures:
            self.message_bus.disable_link(sender, receiver)
    
    def add_signal_agent(self, agent):
        """
        Register a traffic signal agent.
        
        Args:
            agent: SignalAgent instance
        """
        self.signal_agents[agent.intersection_id] = agent
        # Mesa 3.x auto-registers agents when created with model reference
    
    def add_vehicle_agent(self, agent):
        """
        Register a vehicle agent.
        
        Args:
            agent: VehicleAgent instance
        """
        self.vehicle_agents[agent.vehicle_id] = agent
        # Mesa 3.x auto-registers agents when created with model reference
    
    def remove_vehicle_agent(self, vehicle_id: str):
        """
        Remove a vehicle agent (completed journey or stuck).
        
        Args:
            vehicle_id: Vehicle identifier
        """
        if vehicle_id in self.vehicle_agents:
            agent = self.vehicle_agents[vehicle_id]
            agent.remove()  # Mesa 3.x API
            del self.vehicle_agents[vehicle_id]
    
    def mark_vehicle_completed(self, vehicle_agent):
        """
        Mark a vehicle as having completed its journey.
        
        Args:
            vehicle_agent: VehicleAgent that reached destination
        """
        self.completed_vehicles.append({
            'vehicle_id': vehicle_agent.vehicle_id,
            'source': vehicle_agent.source,
            'destination': vehicle_agent.destination,
            'travel_time': vehicle_agent.total_travel_time,
            'waiting_time': vehicle_agent.waiting_time,
            'completed_at': self.current_step
        })
        
        # Record in metrics
        self.metrics.record_completed_vehicle(
            vehicle_agent.waiting_time,
            vehicle_agent.total_travel_time
        )
    
    def load_scenario(self, scenario_name: str):
        """
        Configure simulation for a specific scenario.
        
        Args:
            scenario_name: One of 'normal', 'heavy', 'unequal', 'incident',
                          'sensor_failure', 'comm_failure'
        """
        self.scenario_name = scenario_name
        traffic_config = self.config.get('traffic', {})
        
        if scenario_name == 'normal':
            self.arrival_rate = traffic_config.get('normal_arrival_rate', 1.0)
            
        elif scenario_name == 'heavy':
            self.arrival_rate = traffic_config.get('heavy_arrival_rate', 2.5)
            
        elif scenario_name == 'unequal':
            # This will need special handling in vehicle generation
            # to bias source/destination distribution
            self.arrival_rate = traffic_config.get('normal_arrival_rate', 1.0)
            
        elif scenario_name == 'incident':
            self.arrival_rate = traffic_config.get('normal_arrival_rate', 1.0)
            # Schedule a road blockage midway through simulation
            mid_time = self.duration // 2
            self.incidents.append({
                'timestep': mid_time,
                'source': 'I4',  # Center intersection
                'destination': 'I5',  # Block road to the east
                'type': 'incident'
            })
            
        elif scenario_name == 'sensor_failure':
            self.arrival_rate = traffic_config.get('normal_arrival_rate', 1.0)
            # Disable sensor at one intersection
            self.sensor_failures.append('I4')
            
        elif scenario_name == 'comm_failure':
            self.arrival_rate = traffic_config.get('normal_arrival_rate', 1.0)
            # Disable communication between specific intersections
            self.comm_failures.extend([
                ('I3', 'I4'),
                ('I4', 'I5')
            ])
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current simulation state.
        
        Returns:
            Dictionary with current state information
        """
        return {
            'current_step': self.current_step,
            'running': self.running,
            'paused': self.paused,
            'scenario': self.scenario_name,
            'num_vehicles': len(self.vehicle_agents),
            'num_signals': len(self.signal_agents),
            'completed_vehicles': len(self.completed_vehicles),
            'total_spawned': self.total_vehicles_spawned,
            'network_stats': self.network.get_statistics()
        }
    
    def pause(self):
        """Pause the simulation."""
        self.paused = True
    
    def resume(self):
        """Resume the simulation."""
        self.paused = False
    
    def stop(self):
        """Stop the simulation."""
        self.running = False
