"""
Fixed-Time Traffic Signal Controller
Baseline controller with predetermined timing
"""

from typing import Dict, Any


class FixedTimeController:
    """
    Fixed-time traffic signal controller (baseline).
    
    Uses predetermined cycle times regardless of traffic conditions.
    This serves as the baseline for comparison with adaptive control.
    
    Cycle:
    - NS_GREEN for fixed duration
    - NS_YELLOW for 3 seconds
    - ALL_RED for 1 second
    - EW_GREEN for fixed duration
    - EW_YELLOW for 3 seconds
    - ALL_RED for 1 second
    - Repeat
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize fixed-time controller.
        
        Args:
            config: Configuration dictionary with signal timing parameters
        """
        self.min_green = config.get('signal', {}).get('min_green', 10)
        self.max_green = config.get('signal', {}).get('max_green', 45)
        
        # Fixed-time uses middle of range
        self.fixed_green_time = (self.min_green + self.max_green) // 2
    
    def get_action(self, observation: Dict[str, Any]) -> str:
        """
        Determine signal action based on current state.
        
        For fixed-time control, the decision is purely based on elapsed time,
        not on traffic conditions.
        
        Args:
            observation: Dictionary containing:
                - current_phase: Current signal phase
                - phase_elapsed: Time in current phase
                - min_green: Minimum green time
                - max_green: Maximum green time
                - yellow_time: Yellow duration
                - all_red_time: All-red duration
                
        Returns:
            Action string: "MAINTAIN", "EXTEND", or "SWITCH"
        """
        current_phase = observation.get('current_phase')
        phase_elapsed = observation.get('phase_elapsed', 0)
        min_green = observation.get('min_green', self.min_green)
        yellow_time = observation.get('yellow_time', 3)
        all_red_time = observation.get('all_red_time', 1)
        
        # Handle green phases
        if current_phase in ['ns_green', 'ew_green']:
            # Must stay for minimum time
            if phase_elapsed < min_green:
                return "MAINTAIN"
            
            # Switch at fixed time
            if phase_elapsed >= self.fixed_green_time:
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
    
    def get_explanation(self, observation: Dict[str, Any] = None) -> str:
        """
        Get human-readable explanation of controller logic.
        
        Args:
            observation: Optional observation dict (not used by fixed-time controller)
        
        Returns:
            Explanation string
        """
        return f"Fixed-time controller: {self.fixed_green_time}s green time regardless of traffic"
