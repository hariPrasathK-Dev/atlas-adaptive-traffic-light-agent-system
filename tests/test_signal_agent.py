"""
Tests for Traffic Signal Agent
"""

import pytest
from src.agents.signal_agent import SignalAgent, SignalPhase, PHASE_TRANSITIONS
from src.ai.fixed_controller import FixedTimeController
from src.ai.adaptive_controller import AdaptiveController
from src.environment.simulation import ATLASSimulation


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'simulation': {'duration': 100, 'random_seed': 42, 'grid_size': 3},
        'signal': {'min_green': 10, 'max_green': 45, 'yellow': 3, 'all_red': 1},
        'ai': {'coordination_weight': 0.30, 'phase_switch_threshold': 1.15},
        'traffic': {'normal_arrival_rate': 1.0},
        'road': {'default_length': 100, 'default_capacity': 20, 'default_speed_limit': 50}
    }


@pytest.fixture
def simulation(config):
    """Create test simulation."""
    return ATLASSimulation(config)


@pytest.mark.unit
class TestSignalPhaseTransitions:
    """Test signal phase state machine."""
    
    def test_phase_transitions_complete_cycle(self):
        """Verify complete cycle of phase transitions."""
        phases = [
            SignalPhase.NS_GREEN,
            SignalPhase.NS_YELLOW,
            SignalPhase.ALL_RED_NS,
            SignalPhase.EW_GREEN,
            SignalPhase.EW_YELLOW,
            SignalPhase.ALL_RED_EW
        ]
        
        for i, phase in enumerate(phases):
            next_phase = PHASE_TRANSITIONS[phase]
            expected_next = phases[(i + 1) % len(phases)]
            assert next_phase == expected_next
    
    def test_no_direct_green_to_green(self):
        """Cannot go directly from NS_GREEN to EW_GREEN."""
        assert PHASE_TRANSITIONS[SignalPhase.NS_GREEN] != SignalPhase.EW_GREEN
        assert PHASE_TRANSITIONS[SignalPhase.EW_GREEN] != SignalPhase.NS_GREEN


@pytest.mark.unit
class TestSignalAgent:
    """Test SignalAgent behavior."""
    
    def test_initialization(self, simulation, config):
        """Test signal agent initialization."""
        controller = FixedTimeController(config)
        signal = SignalAgent(simulation, "S1", "I0", controller, config)
        
        assert signal.intersection_id == "I0"
        assert signal.current_phase == SignalPhase.NS_GREEN
        assert signal.phase_elapsed == 0
        assert signal.sensor_enabled is True
        assert signal.communication_enabled is True
    
    def test_can_vehicle_move(self, simulation, config):
        """Test vehicle movement permission."""
        controller = FixedTimeController(config)
        signal = SignalAgent(simulation, "S1", "I0", controller, config)
        
        # NS_GREEN: north/south can move, east/west cannot
        signal.current_phase = SignalPhase.NS_GREEN
        assert signal.can_vehicle_move("north") is True
        assert signal.can_vehicle_move("south") is True
        assert signal.can_vehicle_move("east") is False
        assert signal.can_vehicle_move("west") is False
        
        # EW_GREEN: opposite
        signal.current_phase = SignalPhase.EW_GREEN
        assert signal.can_vehicle_move("north") is False
        assert signal.can_vehicle_move("south") is False
        assert signal.can_vehicle_move("east") is True
        assert signal.can_vehicle_move("west") is True
    
    def test_sensor_failure(self, simulation, config):
        """Test sensor failure handling."""
        controller = FixedTimeController(config)
        signal = SignalAgent(simulation, "S1", "I0", controller, config)
        
        assert signal.sensor_enabled is True
        signal.disable_sensor()
        assert signal.sensor_enabled is False
        signal.enable_sensor()
        assert signal.sensor_enabled is True
    
    def test_communication_failure(self, simulation, config):
        """Test communication failure handling."""
        controller = FixedTimeController(config)
        signal = SignalAgent(simulation, "S1", "I0", controller, config)
        
        assert signal.communication_enabled is True
        signal.disable_communication()
        assert signal.communication_enabled is False
        signal.enable_communication()
        assert signal.communication_enabled is True


@pytest.mark.unit
class TestFixedTimeController:
    """Test fixed-time controller."""
    
    def test_initialization(self, config):
        """Test controller initialization."""
        controller = FixedTimeController(config)
        assert controller.min_green == 10
        assert controller.max_green == 45
        assert controller.fixed_green_time == 27  # (10 + 45) // 2
    
    def test_minimum_green_time(self, config):
        """Must maintain phase for minimum time."""
        controller = FixedTimeController(config)
        
        observation = {
            'current_phase': 'ns_green',
            'phase_elapsed': 5,  # Below minimum
            'min_green': 10
        }
        
        action = controller.get_action(observation)
        assert action == "MAINTAIN"
    
    def test_switch_at_fixed_time(self, config):
        """Should switch at predetermined time."""
        controller = FixedTimeController(config)
        
        observation = {
            'current_phase': 'ns_green',
            'phase_elapsed': 27,  # At fixed time
            'min_green': 10
        }
        
        action = controller.get_action(observation)
        assert action == "SWITCH"
    
    def test_yellow_transition(self, config):
        """Yellow phase has fixed duration."""
        controller = FixedTimeController(config)
        
        observation = {
            'current_phase': 'ns_yellow',
            'phase_elapsed': 3,
            'yellow_time': 3
        }
        
        action = controller.get_action(observation)
        assert action == "SWITCH"


@pytest.mark.unit
class TestAdaptiveController:
    """Test adaptive controller."""
    
    def test_pressure_calculation(self, config):
        """Test traffic pressure calculation."""
        controller = AdaptiveController(config)
        
        # High queue + high wait = high pressure
        pressure1 = controller.calculate_local_pressure(queue_length=10, avg_wait_time=20.0)
        assert pressure1 == 200.0
        
        # Low queue or low wait = low pressure
        pressure2 = controller.calculate_local_pressure(queue_length=2, avg_wait_time=5.0)
        assert pressure2 == 10.0
        
        # Higher queue/wait should give higher pressure
        assert pressure1 > pressure2
    
    def test_coordinated_pressure(self, config):
        """Test pressure coordination with neighbors."""
        controller = AdaptiveController(config)
        
        local = 100.0
        downstream = 50.0
        
        coordinated = controller.calculate_coordinated_pressure(local, downstream)
        
        # Should be local + (weight * downstream)
        expected = 100.0 + (0.30 * 50.0)
        assert coordinated == expected
    
    def test_minimum_green_respected(self, config):
        """Adaptive controller must respect minimum green time."""
        controller = AdaptiveController(config)
        
        # High opposing pressure but below minimum time
        result = controller.should_switch_phase(
            current_direction_pressure=10.0,
            opposing_direction_pressure=100.0,
            phase_elapsed=5  # Below min_green of 10
        )
        
        assert result is False
    
    def test_maximum_green_forces_switch(self, config):
        """Must switch at maximum green time."""
        controller = AdaptiveController(config)
        
        # At max time, must switch regardless of pressure
        result = controller.should_switch_phase(
            current_direction_pressure=100.0,
            opposing_direction_pressure=10.0,
            phase_elapsed=45  # At max_green
        )
        
        assert result is True
    
    def test_pressure_threshold_switch(self, config):
        """Switch when opposing pressure significantly higher."""
        controller = AdaptiveController(config)
        
        # Opposing pressure exceeds threshold
        result = controller.should_switch_phase(
            current_direction_pressure=100.0,
            opposing_direction_pressure=120.0,  # 1.2x ratio
            phase_elapsed=15  # Above min, below max
        )
        
        assert result is True
    
    def test_no_switch_when_balanced(self, config):
        """Don't switch when pressures are balanced."""
        controller = AdaptiveController(config)
        
        # Similar pressures
        result = controller.should_switch_phase(
            current_direction_pressure=100.0,
            opposing_direction_pressure=105.0,  # 1.05x ratio < 1.15 threshold
            phase_elapsed=15
        )
        
        assert result is False


@pytest.mark.integration
def test_signal_agent_full_cycle(simulation, config):
    """Test complete signal phase cycle."""
    controller = FixedTimeController(config)
    signal = SignalAgent(simulation, "S1", "I4", controller, config)
    simulation.add_signal_agent(signal)
    
    initial_phase = signal.current_phase
    phase_changes = 0
    max_steps = 100
    
    for _ in range(max_steps):
        signal.step()
        if signal.current_phase != initial_phase:
            phase_changes += 1
            if phase_changes >= 6:  # Complete cycle
                break
            initial_phase = signal.current_phase
    
    # Should complete at least one full cycle
    assert phase_changes >= 6
