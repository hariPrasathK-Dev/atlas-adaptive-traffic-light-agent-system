"""
Decision Logger for ATLAS
Tracks AI decisions for explainability and analysis
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class DecisionRecord:
    """Record of a single signal phase decision."""
    timestep: int
    signal_id: str
    current_phase: str
    action: str
    phase_elapsed: int
    
    # Traffic observations
    ns_queue: int
    ew_queue: int
    ns_avg_wait: float
    ew_avg_wait: float
    
    # Pressure calculations (for adaptive controller)
    ns_local_pressure: Optional[float] = None
    ew_local_pressure: Optional[float] = None
    ns_coordinated_pressure: Optional[float] = None
    ew_coordinated_pressure: Optional[float] = None
    
    # Decision reasoning
    reason: str = ""
    controller_type: str = "unknown"


class DecisionLogger:
    """
    Logs AI decisions for traffic signal control.
    
    Provides:
    - Complete decision history
    - Explainable AI outputs
    - Analysis of decision patterns
    - Export for external review
    """
    
    def __init__(self):
        """Initialize decision logger."""
        self.decisions: List[DecisionRecord] = []
        self.current_step_decisions: Dict[str, DecisionRecord] = {}
    
    def log_decision(
        self,
        timestep: int,
        signal_id: str,
        current_phase: str,
        action: str,
        phase_elapsed: int,
        observation: Dict[str, Any],
        controller_type: str = "unknown",
        reason: str = ""
    ):
        """
        Log a signal control decision.
        
        Args:
            timestep: Current simulation step
            signal_id: Intersection identifier
            current_phase: Current signal phase
            action: Action taken ("MAINTAIN", "SWITCH", etc.)
            phase_elapsed: Time in current phase
            observation: Full observation dictionary
            controller_type: "fixed" or "adaptive"
            reason: Human-readable explanation
        """
        record = DecisionRecord(
            timestep=timestep,
            signal_id=signal_id,
            current_phase=current_phase,
            action=action,
            phase_elapsed=phase_elapsed,
            ns_queue=observation.get('ns_queue', 0),
            ew_queue=observation.get('ew_queue', 0),
            ns_avg_wait=observation.get('ns_avg_wait', 0.0),
            ew_avg_wait=observation.get('ew_avg_wait', 0.0),
            ns_local_pressure=observation.get('_ns_local'),
            ew_local_pressure=observation.get('_ew_local'),
            ns_coordinated_pressure=observation.get('_ns_pressure'),
            ew_coordinated_pressure=observation.get('_ew_pressure'),
            reason=reason,
            controller_type=controller_type
        )
        
        self.decisions.append(record)
        self.current_step_decisions[signal_id] = record
    
    def get_latest_decision(self, signal_id: str) -> Optional[DecisionRecord]:
        """
        Get most recent decision for a signal.
        
        Args:
            signal_id: Intersection identifier
            
        Returns:
            Latest DecisionRecord or None
        """
        return self.current_step_decisions.get(signal_id)
    
    def get_decisions_for_signal(self, signal_id: str) -> List[DecisionRecord]:
        """
        Get all decisions for a specific signal.
        
        Args:
            signal_id: Intersection identifier
            
        Returns:
            List of decisions chronologically
        """
        return [d for d in self.decisions if d.signal_id == signal_id]
    
    def get_phase_changes(self, signal_id: Optional[str] = None) -> List[DecisionRecord]:
        """
        Get all phase change decisions.
        
        Args:
            signal_id: Optional filter by intersection
            
        Returns:
            List of decisions where action was "SWITCH"
        """
        changes = [d for d in self.decisions if d.action == "SWITCH"]
        
        if signal_id:
            changes = [d for d in changes if d.signal_id == signal_id]
        
        return changes
    
    def get_decisions_at_timestep(self, timestep: int) -> List[DecisionRecord]:
        """
        Get all decisions made at a specific timestep.
        
        Args:
            timestep: Simulation step
            
        Returns:
            List of decisions
        """
        return [d for d in self.decisions if d.timestep == timestep]
    
    def analyze_decision_patterns(self) -> Dict[str, Any]:
        """
        Analyze decision patterns across the simulation.
        
        Returns:
            Dictionary with analysis results
        """
        if not self.decisions:
            return {}
        
        # Count actions
        action_counts = {}
        for decision in self.decisions:
            action_counts[decision.action] = action_counts.get(decision.action, 0) + 1
        
        # Count phase changes per signal
        changes_per_signal = {}
        for decision in self.decisions:
            if decision.action == "SWITCH":
                signal = decision.signal_id
                changes_per_signal[signal] = changes_per_signal.get(signal, 0) + 1
        
        # Average phase duration when switching
        switch_durations = [d.phase_elapsed for d in self.decisions if d.action == "SWITCH"]
        
        return {
            'total_decisions': len(self.decisions),
            'action_distribution': action_counts,
            'phase_changes_per_signal': changes_per_signal,
            'total_phase_changes': sum(changes_per_signal.values()),
            'avg_phase_duration_at_switch': sum(switch_durations) / len(switch_durations) if switch_durations else 0,
            'unique_signals': len(set(d.signal_id for d in self.decisions))
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert decision log to pandas DataFrame.
        
        Returns:
            DataFrame with all decision records
        """
        if not self.decisions:
            return pd.DataFrame()
        
        data = []
        for record in self.decisions:
            data.append({
                'timestep': record.timestep,
                'signal_id': record.signal_id,
                'current_phase': record.current_phase,
                'action': record.action,
                'phase_elapsed': record.phase_elapsed,
                'ns_queue': record.ns_queue,
                'ew_queue': record.ew_queue,
                'ns_avg_wait': record.ns_avg_wait,
                'ew_avg_wait': record.ew_avg_wait,
                'ns_local_pressure': record.ns_local_pressure,
                'ew_local_pressure': record.ew_local_pressure,
                'ns_coordinated_pressure': record.ns_coordinated_pressure,
                'ew_coordinated_pressure': record.ew_coordinated_pressure,
                'reason': record.reason,
                'controller_type': record.controller_type
            })
        
        return pd.DataFrame(data)
    
    def export_to_csv(self, filename: str):
        """
        Export decision log to CSV file.
        
        Args:
            filename: Output file path
        """
        df = self.to_dataframe()
        df.to_csv(filename, index=False)
    
    def get_explanation_for_signal(self, signal_id: str, timestep: Optional[int] = None) -> str:
        """
        Get human-readable explanation for a signal's decision.
        
        Args:
            signal_id: Intersection identifier
            timestep: Optional specific timestep (default: latest)
            
        Returns:
            Explanation string
        """
        if timestep is not None:
            decisions = [d for d in self.decisions if d.signal_id == signal_id and d.timestep == timestep]
            record = decisions[0] if decisions else None
        else:
            record = self.get_latest_decision(signal_id)
        
        if not record:
            return f"No decision found for {signal_id}"
        
        explanation = f"Signal: {record.signal_id} at timestep {record.timestep}\n"
        explanation += f"Phase: {record.current_phase} (elapsed: {record.phase_elapsed}s)\n"
        explanation += f"Action: {record.action}\n\n"
        
        explanation += f"Traffic State:\n"
        explanation += f"  NS Queue: {record.ns_queue} vehicles (avg wait: {record.ns_avg_wait:.1f}s)\n"
        explanation += f"  EW Queue: {record.ew_queue} vehicles (avg wait: {record.ew_avg_wait:.1f}s)\n\n"
        
        if record.ns_local_pressure is not None:
            explanation += f"Pressure Analysis:\n"
            explanation += f"  NS Local: {record.ns_local_pressure:.2f}\n"
            explanation += f"  EW Local: {record.ew_local_pressure:.2f}\n"
            if record.ns_coordinated_pressure is not None:
                explanation += f"  NS Coordinated: {record.ns_coordinated_pressure:.2f}\n"
                explanation += f"  EW Coordinated: {record.ew_coordinated_pressure:.2f}\n"
            explanation += "\n"
        
        if record.reason:
            explanation += f"Reasoning: {record.reason}\n"
        
        return explanation
    
    def reset(self):
        """Clear all decision records."""
        self.decisions.clear()
        self.current_step_decisions.clear()
