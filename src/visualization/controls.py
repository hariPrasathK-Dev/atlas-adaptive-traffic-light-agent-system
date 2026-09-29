"""
Control Components for ATLAS Dashboard
UI elements for simulation control
"""

import streamlit as st
from typing import Dict, Any


def render_scenario_selector() -> str:
    """
    Render scenario selection UI.
    
    Returns:
        Selected scenario name
    """
    st.subheader("Scenario Selection")
    
    scenarios = {
        "normal": {
            "name": "🚗 Normal Traffic",
            "description": "Balanced stochastic arrivals"
        },
        "heavy": {
            "name": "🚙🚗🚕 Heavy Traffic",
            "description": "High arrival rate stress test"
        },
        "unequal": {
            "name": "⬆️↔️ Unequal Flow",
            "description": "Biased NS/EW distribution"
        },
        "incident": {
            "name": "🚧 Road Incident",
            "description": "Dynamic blockage & rerouting"
        },
        "sensor_failure": {
            "name": "📡❌ Sensor Failure",
            "description": "Partial observability test"
        },
        "comm_failure": {
            "name": "📶❌ Comm Failure",
            "description": "Decentralized operation"
        }
    }
    
    selected_scenario = st.radio(
        "Choose Scenario",
        options=list(scenarios.keys()),
        format_func=lambda x: scenarios[x]["name"],
        help="Select traffic scenario to simulate"
    )
    
    # Show description
    st.caption(scenarios[selected_scenario]["description"])
    
    return selected_scenario


def render_controls(simulation) -> Dict[str, Any]:
    """
    Render simulation control buttons.
    
    Args:
        simulation: ATLASSimulation instance
        
    Returns:
        Dictionary with control actions
    """
    actions = {
        'start': False,
        'pause': False,
        'reset': False,
        'step': False
    }
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶️ Start", width="stretch"):
            actions['start'] = True
    
    with col2:
        if st.button("⏸️ Pause", width="stretch"):
            actions['pause'] = True
    
    with col3:
        if st.button("⏭️ Step", width="stretch"):
            actions['step'] = True
    
    with col4:
        if st.button("🔄 Reset", width="stretch"):
            actions['reset'] = True
    
    return actions
