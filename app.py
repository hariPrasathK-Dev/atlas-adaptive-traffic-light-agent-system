"""
ATLAS - Adaptive Traffic Light Agent System
Main Streamlit Application Entry Point
"""

import streamlit as st
import yaml
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="ATLAS - Traffic Signal Control",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_resource
def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Initialize session state
if 'simulation' not in st.session_state:
    st.session_state.simulation = None
    st.session_state.running = False
    st.session_state.initialized = False
    # Stores completed run results keyed by controller type for comparison
    st.session_state.completed_runs = {}  # {'fixed': {...}, 'adaptive': {...}}


# Import visualization components
from src.visualization.dashboard import create_dashboard

# Main application
def main():
    """Main application entry point."""
    
    # Load configuration
    config = load_config()
    
    # Create dashboard
    create_dashboard(config)

if __name__ == "__main__":
    main()
