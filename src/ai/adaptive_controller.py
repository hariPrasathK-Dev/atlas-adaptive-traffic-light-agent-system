"""
Adaptive Traffic Signal Controller
Pressure-based controller with neighbor coordination
"""

from typing import Dict, Any, Optional


class AdaptiveController:
    """
    Adaptive traffic signal controller using pressure-based decisions.
    
    The controller:
    1. Calculates local pressure for each direction (queue × avg_wait)
    2. Receives neighbor pressure from adjacent intersections
    3. Combines local and downstream pressure with coordination weight
    4. Switches phases when opposing direction has significantly higher pressure
    
    This demonstrates:
    - Reactive decision making based on observations
    - Multi-agent coordination through message passing
    - Interpretable AI decisions (all values are trackable)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adaptive controller.
        
        Args:
            config: Configuration dictionary with AI parameters
        """
        ai_config = config.get('ai', {})
        signal_config = config.get('signal', {})
        
        self.coordination_weight = ai_config.get('coordination_weight', 0.30)
        self.phase_switch_threshold = ai_config.get('phase_switch_threshold', 1.15)
        
        self.min_green = signal_config.get('min_green', 10)
        self.max_green = signal_config.get('max_green', 45)
    
    def calculate_local_pressure(
        self,
        queue_length: int,
        avg_wait_time: float
    ) -> float:
        """
        Calculate local traffic pressure for a direction.
        
        Pressure combines queue length with waiting time:
        - Long queue + long wait = high pressure
        - Short queue or short wait = low pressure
        
        Args:
            queue_length: Number of waiting vehicles
            avg_wait_time: Average waiting time of vehicles
            
        Returns:
            Pressure value (higher = more urgent)
        """
        return queue_length * avg_wait_time
    
    def calculate_coordinated_pressure(
        self,
        local_pressure: float,
        downstream_pressure: Optional[float] = None
    ) -> float:
        """
        Calculate total pressure including neighbor coordination.
        
        Considers both local conditions and downstream traffic to prevent
        creating congestion in neighboring intersections.
        
        Args:
            local_pressure: Local traffic pressure
            downstream_pressure: Pressure from downstream neighbor
            
        Returns:
            Combined pressure value
        """
        if downstream_pressure is None:
            return local_pressure
        
        # Coordinated pressure = local + (α × downstream)
        return local_pressure + (self.coordination_weight * downstream_pressure)
    
    def should_switch_phase(
        self,
        current_direction_pressure: float,
        opposing_direction_pressure: float,
        phase_elapsed: int
    ) -> bool:
        """
        Decide whether to switch to opposing direction.
        
        Switch criteria:
        1. Minimum green time has elapsed
        2. Maximum green time reached, OR
        3. Opposing pressure exceeds current by threshold ratio
        
        Args:
            current_direction_pressure: Pressure for current green direction
            opposing_direction_pressure: Pressure for opposing direction
            phase_elapsed: Time in current phase
            
        Returns:
            True if should switch phases, False otherwise
        """
        # Must respect minimum green time
        if phase_elapsed < self.min_green:
            return False
        
        # Must switch at maximum green time
        if phase_elapsed >= self.max_green:
            return True
        
        # Switch if opposing pressure is significantly higher
        if current_direction_pressure < 0.01:  # Avoid division by zero
            # If current has zero pressure, switch if opposing has any demand
            return opposing_direction_pressure > 0.5
        
        pressure_ratio = opposing_direction_pressure / current_direction_pressure
        
        return pressure_ratio >= self.phase_switch_threshold
    
    def get_action(self, observation: Dict[str, Any]) -> str:
        """
        Determine signal action based on traffic observations.
        
        Args:
            observation: Dictionary containing:
                - current_phase: Current signal phase
                - phase_elapsed: Time in current phase
                - ns_queue: North-South queue length
                - ew_queue: East-West queue length
                - ns_avg_wait: North-South average wait time
                - ew_avg_wait: East-West average wait time
                - ns_downstream_pressure: Pressure from NS neighbors (optional)
                - ew_downstream_pressure: Pressure from EW neighbors (optional)
                - min_green: Minimum green time
                - max_green: Maximum green time
                - yellow_time: Yellow duration
                - all_red_time: All-red duration
                
        Returns:
            Action string: "MAINTAIN", "EXTEND", or "SWITCH"
        """
        current_phase = observation.get('current_phase')
        phase_elapsed = observation.get('phase_elapsed', 0)
        yellow_time = observation.get('yellow_time', 3)
        all_red_time = observation.get('all_red_time', 1)
        
        # Handle green phases (adaptive decision)
        # NOTE: phase values are lowercase (matching SignalPhase enum e.g. 'ns_green')
        if current_phase in ['ns_green', 'ew_green']:
            # Calculate pressures
            ns_local = self.calculate_local_pressure(
                observation.get('ns_queue', 0),
                observation.get('ns_avg_wait', 0.0)
            )
            ew_local = self.calculate_local_pressure(
                observation.get('ew_queue', 0),
                observation.get('ew_avg_wait', 0.0)
            )
            
            # Add coordination
            ns_pressure = self.calculate_coordinated_pressure(
                ns_local,
                observation.get('ns_downstream_pressure')
            )
            ew_pressure = self.calculate_coordinated_pressure(
                ew_local,
                observation.get('ew_downstream_pressure')
            )
            
            # Store for logging/explanation
            observation['_ns_pressure'] = ns_pressure
            observation['_ew_pressure'] = ew_pressure
            observation['_ns_local'] = ns_local
            observation['_ew_local'] = ew_local
            
            # Decide based on current phase
            if current_phase == 'ns_green':
                if self.should_switch_phase(ns_pressure, ew_pressure, phase_elapsed):
                    return "SWITCH"
            else:  # ew_green
                if self.should_switch_phase(ew_pressure, ns_pressure, phase_elapsed):
                    return "SWITCH"
            
            return "MAINTAIN"
        
        # Handle yellow phases (always fixed duration)
        elif current_phase in ['ns_yellow', 'ew_yellow']:
            if phase_elapsed >= yellow_time:
                return "SWITCH"
            return "MAINTAIN"
        
        # Handle all-red phases (always fixed duration)
        elif current_phase in ['all_red_ns', 'all_red_ew']:
            if phase_elapsed >= all_red_time:
                return "SWITCH"
            return "MAINTAIN"
        
        # Default: maintain
        return "MAINTAIN"
    
    def get_explanation(self, observation: Dict[str, Any]) -> str:
        """
        Get human-readable explanation of the decision.
        
        Args:
            observation: Same observation dict passed to get_action
            
        Returns:
            Explanation string with pressure values and reasoning
        """
        current_phase = observation.get('current_phase')
        phase_elapsed = observation.get('phase_elapsed', 0)
        
        if current_phase in ['ns_green', 'ew_green']:
            ns_pressure = observation.get('_ns_pressure', 0)
            ew_pressure = observation.get('_ew_pressure', 0)
            ns_local = observation.get('_ns_local', 0)
            ew_local = observation.get('_ew_local', 0)
            
            ns_queue = observation.get('ns_queue', 0)
            ew_queue = observation.get('ew_queue', 0)
            
            explanation = (
                f"Phase: {current_phase.upper()} ({phase_elapsed}s)\n"
                f"NS Pressure: {ns_pressure:.2f} (local: {ns_local:.2f}, queue: {ns_queue})\n"
                f"EW Pressure: {ew_pressure:.2f} (local: {ew_local:.2f}, queue: {ew_queue})\n"
            )
            
            if phase_elapsed < self.min_green:
                explanation += f"Decision: MAINTAIN (min green {self.min_green}s not reached)"
            elif phase_elapsed >= self.max_green:
                explanation += f"Decision: SWITCH (max green {self.max_green}s reached)"
            else:
                if current_phase == 'ns_green':
                    ratio = ew_pressure / max(ns_pressure, 0.01)
                    explanation += (
                        f"Pressure ratio (EW/NS): {ratio:.2f}\n"
                        f"Threshold: {self.phase_switch_threshold:.2f}\n"
                    )
                    if ratio >= self.phase_switch_threshold:
                        explanation += "Decision: SWITCH (EW pressure significantly higher)"
                    else:
                        explanation += "Decision: MAINTAIN (NS still has priority)"
                else:  # ew_green
                    ratio = ns_pressure / max(ew_pressure, 0.01)
                    explanation += (
                        f"Pressure ratio (NS/EW): {ratio:.2f}\n"
                        f"Threshold: {self.phase_switch_threshold:.2f}\n"
                    )
                    if ratio >= self.phase_switch_threshold:
                        explanation += "Decision: SWITCH (NS pressure significantly higher)"
                    else:
                        explanation += "Decision: MAINTAIN (EW still has priority)"
            
            return explanation
        
        return f"Phase: {current_phase} ({phase_elapsed}s) - Transition phase"
