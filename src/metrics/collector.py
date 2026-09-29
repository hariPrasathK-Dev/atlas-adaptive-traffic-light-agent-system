"""
Metrics Collector for ATLAS
Real-time performance measurement and aggregation
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class MetricsSnapshot:
    """Single timestep metrics snapshot."""
    timestep: int
    avg_waiting_time: float = 0.0
    max_waiting_time: float = 0.0
    avg_queue_length: float = 0.0
    max_queue_length: int = 0
    avg_travel_time: float = 0.0
    throughput: int = 0
    stopped_vehicles: int = 0
    total_vehicles: int = 0
    completed_vehicles: int = 0


class MetricsCollector:
    """
    Collects and aggregates simulation performance metrics.
    
    Tracks:
    - Waiting times (average and maximum)
    - Queue lengths (average and maximum)
    - Travel times
    - Throughput (vehicles completing journeys)
    - Real-time vehicle counts
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.history: List[MetricsSnapshot] = []
        self.current_metrics = MetricsSnapshot(timestep=0)
        
        # Cumulative statistics for completed vehicles
        self.total_waiting_times: List[float] = []
        self.total_travel_times: List[float] = []
        self.completed_count = 0
    
    def collect(self, simulation) -> MetricsSnapshot:
        """
        Collect metrics for current timestep.
        
        Args:
            simulation: ATLASSimulation instance
            
        Returns:
            MetricsSnapshot for current step
        """
        timestep = simulation.current_step
        
        # Collect vehicle waiting times
        waiting_times = []
        travel_times = []
        stopped_count = 0
        
        for vehicle in simulation.vehicle_agents.values():
            waiting_times.append(vehicle.waiting_time)
            travel_times.append(vehicle.total_travel_time)
            
            # Count stopped vehicles (waiting or stuck)
            if vehicle.state.value in ['waiting', 'stuck']:
                stopped_count += 1
        
        # Collect queue lengths from all intersections
        queue_lengths = []
        for signal in simulation.signal_agents.values():
            ns_queue = signal.queue_state.get('north', 0) + signal.queue_state.get('south', 0)
            ew_queue = signal.queue_state.get('east', 0) + signal.queue_state.get('west', 0)
            queue_lengths.extend([ns_queue, ew_queue])
        
        # Calculate metrics
        snapshot = MetricsSnapshot(
            timestep=timestep,
            avg_waiting_time=np.mean(waiting_times) if waiting_times else 0.0,
            max_waiting_time=max(waiting_times) if waiting_times else 0.0,
            avg_queue_length=np.mean(queue_lengths) if queue_lengths else 0.0,
            max_queue_length=max(queue_lengths) if queue_lengths else 0,
            avg_travel_time=np.mean(travel_times) if travel_times else 0.0,
            throughput=len(simulation.completed_vehicles),
            stopped_vehicles=stopped_count,
            total_vehicles=len(simulation.vehicle_agents),
            completed_vehicles=len(simulation.completed_vehicles)
        )
        
        self.current_metrics = snapshot
        self.history.append(snapshot)
        
        return snapshot
    
    def record_completed_vehicle(self, waiting_time: float, travel_time: float):
        """
        Record statistics for a completed vehicle.
        
        Args:
            waiting_time: Total time vehicle spent waiting
            travel_time: Total journey time
        """
        self.total_waiting_times.append(waiting_time)
        self.total_travel_times.append(travel_time)
        self.completed_count += 1
    
    def get_current_metrics(self) -> MetricsSnapshot:
        """Get most recent metrics snapshot."""
        return self.current_metrics
    
    def get_summary_statistics(self) -> Dict[str, float]:
        """
        Calculate summary statistics across entire simulation.
        
        Returns:
            Dictionary with aggregate metrics
        """
        if not self.history:
            return {}
        
        # Completed vehicle statistics
        avg_waiting = np.mean(self.total_waiting_times) if self.total_waiting_times else 0.0
        max_waiting = max(self.total_waiting_times) if self.total_waiting_times else 0.0
        avg_travel = np.mean(self.total_travel_times) if self.total_travel_times else 0.0
        
        # Time-series statistics
        avg_queue = np.mean([s.avg_queue_length for s in self.history])
        max_queue = max([s.max_queue_length for s in self.history])
        
        # Throughput
        final_throughput = self.history[-1].throughput if self.history else 0
        
        return {
            'avg_waiting_time': avg_waiting,
            'max_waiting_time': max_waiting,
            'avg_travel_time': avg_travel,
            'avg_queue_length': avg_queue,
            'max_queue_length': max_queue,
            'total_completed': final_throughput,
            'completion_rate': final_throughput / max(len(self.history), 1)
        }
    
    def get_time_series(self, metric_name: str) -> List[float]:
        """
        Get time series data for a specific metric.
        
        Args:
            metric_name: Name of metric to extract
            
        Returns:
            List of values over time
        """
        if metric_name not in MetricsSnapshot.__annotations__:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        return [getattr(snapshot, metric_name) for snapshot in self.history]
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert metrics history to pandas DataFrame.
        
        Returns:
            DataFrame with all metrics over time
        """
        if not self.history:
            return pd.DataFrame()
        
        data = []
        for snapshot in self.history:
            data.append({
                'timestep': snapshot.timestep,
                'avg_waiting_time': snapshot.avg_waiting_time,
                'max_waiting_time': snapshot.max_waiting_time,
                'avg_queue_length': snapshot.avg_queue_length,
                'max_queue_length': snapshot.max_queue_length,
                'avg_travel_time': snapshot.avg_travel_time,
                'throughput': snapshot.throughput,
                'stopped_vehicles': snapshot.stopped_vehicles,
                'total_vehicles': snapshot.total_vehicles,
                'completed_vehicles': snapshot.completed_vehicles
            })
        
        return pd.DataFrame(data)
    
    def export_to_csv(self, filename: str):
        """
        Export metrics to CSV file.
        
        Args:
            filename: Output file path
        """
        df = self.to_dataframe()
        df.to_csv(filename, index=False)
    
    def reset(self):
        """Reset all metrics."""
        self.history.clear()
        self.total_waiting_times.clear()
        self.total_travel_times.clear()
        self.completed_count = 0
        self.current_metrics = MetricsSnapshot(timestep=0)
    
    def compare_with(self, other: 'MetricsCollector') -> Dict[str, float]:
        """
        Compare metrics with another run (e.g., baseline vs. adaptive).
        
        Args:
            other: Another MetricsCollector to compare against
            
        Returns:
            Dictionary with percentage improvements
        """
        self_stats = self.get_summary_statistics()
        other_stats = other.get_summary_statistics()
        
        comparison = {}
        
        # Metrics where lower is better
        for metric in ['avg_waiting_time', 'max_waiting_time', 'avg_travel_time', 'avg_queue_length', 'max_queue_length']:
            if metric in self_stats and metric in other_stats and other_stats[metric] > 0:
                improvement = ((other_stats[metric] - self_stats[metric]) / other_stats[metric]) * 100
                comparison[f"{metric}_improvement_%"] = improvement
        
        # Metrics where higher is better
        for metric in ['total_completed', 'completion_rate']:
            if metric in self_stats and metric in other_stats and other_stats[metric] > 0:
                improvement = ((self_stats[metric] - other_stats[metric]) / other_stats[metric]) * 100
                comparison[f"{metric}_improvement_%"] = improvement
        
        return comparison
