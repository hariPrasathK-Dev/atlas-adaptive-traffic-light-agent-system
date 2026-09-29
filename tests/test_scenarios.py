"""
Smoke Tests for ATLAS Scenarios
End-to-end scenario validation
"""

import pytest
import numpy as np
from src.environment.simulation import ATLASSimulation


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'simulation': {'duration': 50, 'random_seed': 42, 'grid_size': 3},
        'signal': {'min_green': 10, 'max_green': 45, 'yellow': 3, 'all_red': 1},
        'ai': {'coordination_weight': 0.30, 'phase_switch_threshold': 1.15},
        'traffic': {
            'normal_arrival_rate': 1.0,
            'heavy_arrival_rate': 2.5,
            'unequal_ns_rate': 2.0,
            'unequal_ew_rate': 0.5
        },
        'road': {'default_length': 100, 'default_capacity': 20, 'default_speed_limit': 50}
    }


@pytest.mark.smoke
class TestScenarios:
    """Smoke tests for all scenarios."""
    
    def test_normal_traffic_fixed(self, config):
        """Test normal traffic with fixed controller."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("fixed")
        sim.load_scenario("normal")
        
        # Run simulation
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        assert sim.current_step == config['simulation']['duration']
        assert len(sim.signal_agents) == 9  # 3x3 grid
        assert sim.metrics.history
    
    def test_normal_traffic_adaptive(self, config):
        """Test normal traffic with adaptive controller."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("adaptive")
        sim.load_scenario("normal")
        
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        assert sim.current_step == config['simulation']['duration']
        assert sim.scenario_name == "normal"
    
    def test_heavy_traffic(self, config):
        """Test heavy traffic scenario."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("adaptive")
        sim.load_scenario("heavy")
        
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        # Should handle high arrival rate
        assert sim.total_vehicles_spawned > 0
        stats = sim.metrics.get_summary_statistics()
        assert 'avg_queue_length' in stats
    
    def test_incident_scenario(self, config):
        """Test road incident scenario."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("adaptive")
        sim.load_scenario("incident")
        
        # Incident should be scheduled
        assert len(sim.incidents) > 0
        
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        # At least one road should be blocked after incident
        blocked_roads = [r for r in sim.network.roads.values() if r.blocked]
        assert len(blocked_roads) > 0
    
    def test_sensor_failure_scenario(self, config):
        """Test sensor failure scenario."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("adaptive")
        sim.load_scenario("sensor_failure")
        
        assert len(sim.sensor_failures) > 0
        
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        # Check that sensor failure was applied
        failed_signal = sim.signal_agents.get(sim.sensor_failures[0])
        if failed_signal:
            assert failed_signal.sensor_enabled is False
    
    def test_comm_failure_scenario(self, config):
        """Test communication failure scenario."""
        sim = ATLASSimulation(config)
        sim.set_controller_type("adaptive")
        sim.load_scenario("comm_failure")
        
        assert len(sim.comm_failures) > 0
        
        for _ in range(config['simulation']['duration']):
            sim.step()
        
        # Check that communication failure was applied
        stats = sim.message_bus.get_statistics()
        assert stats['disabled_links'] > 0
    
    def test_reset_functionality(self, config):
        """Test simulation reset."""
        sim = ATLASSimulation(config)
        sim.load_scenario("normal")
        
        # Run for some steps
        for _ in range(20):
            sim.step()
        
        assert sim.current_step == 20
        
        # Reset
        sim.reset()
        
        assert sim.current_step == 0
        assert len(sim.vehicle_agents) == 0
        assert len(sim.completed_vehicles) == 0
        assert len(sim.metrics.history) == 0


@pytest.mark.integration
def test_controller_comparison(config):
    """Test comparing fixed vs adaptive controllers."""
    # Fixed controller run
    sim_fixed = ATLASSimulation(config)
    sim_fixed.set_controller_type("fixed")
    sim_fixed.load_scenario("normal")
    
    for _ in range(config['simulation']['duration']):
        sim_fixed.step()
    
    stats_fixed = sim_fixed.metrics.get_summary_statistics()
    
    # Adaptive controller run (same seed)
    sim_adaptive = ATLASSimulation(config)
    sim_adaptive.set_controller_type("adaptive")
    sim_adaptive.load_scenario("normal")
    
    for _ in range(config['simulation']['duration']):
        sim_adaptive.step()
    
    stats_adaptive = sim_adaptive.metrics.get_summary_statistics()
    
    # Both should complete
    assert stats_fixed['total_completed'] >= 0
    assert stats_adaptive['total_completed'] >= 0
    
    # Can compare metrics
    comparison = sim_adaptive.metrics.compare_with(sim_fixed.metrics)
    # Comparison should have some metrics (exact keys depend on whether vehicles completed)
    assert len(comparison) > 0
    # Check that comparison values are numbers
    for key, value in comparison.items():
        assert isinstance(value, (int, float, np.number))


@pytest.mark.integration
def test_metrics_export(config, tmp_path):
    """Test metrics export functionality."""
    sim = ATLASSimulation(config)
    sim.load_scenario("normal")
    
    for _ in range(30):
        sim.step()
    
    # Export metrics
    csv_file = tmp_path / "test_metrics.csv"
    sim.metrics.export_to_csv(str(csv_file))
    
    assert csv_file.exists()
    
    # Verify CSV content
    import pandas as pd
    df = pd.read_csv(csv_file)
    assert len(df) > 0
    assert 'timestep' in df.columns
    assert 'avg_waiting_time' in df.columns
