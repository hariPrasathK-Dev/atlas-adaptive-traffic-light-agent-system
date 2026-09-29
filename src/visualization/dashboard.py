"""
Main Dashboard for ATLAS
Streamlit user interface with controls and visualizations
"""

import streamlit as st
from typing import Dict, Any
import time

from ..environment.simulation import ATLASSimulation
from .network_view import render_network_view
from .charts import render_metrics_charts, render_comparison_charts
from .controls import render_controls, render_scenario_selector


def initialize_simulation(config: Dict[str, Any]) -> ATLASSimulation:
    """
    Initialize a new simulation instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ATLASSimulation instance
    """
    simulation = ATLASSimulation(config, random_seed=config['simulation']['random_seed'])
    return simulation


def create_dashboard(config: Dict[str, Any]):
    """
    Create the main ATLAS dashboard.
    
    Args:
        config: Configuration dictionary loaded from config.yaml
    """
    
    # Title and description
    st.title("🚦 ATLAS - Adaptive Traffic Light Agent System")
    st.markdown("""
    **Multi-Agent Traffic Signal Synchronization using Classical AI**
    
    Demonstration of PEAS formulation, A* search, adaptive control, and multi-agent coordination.
    """)
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Scenario selection
        scenario = render_scenario_selector()
        
        # Controller selection
        st.subheader("Controller Type")
        controller_type = st.radio(
            "Select Controller",
            options=["fixed", "adaptive"],
            format_func=lambda x: "Fixed-Time (Baseline)" if x == "fixed" else "Adaptive (Pressure-Based)",
            help="Fixed-time uses predetermined cycles. Adaptive responds to traffic demand."
        )
        
        # Simulation parameters
        st.subheader("Simulation Parameters")
        duration = st.slider("Duration (timesteps)", 50, 500, config['simulation']['duration'], 50)
        speed = st.slider("Speed", 1, 10, 5, help="Simulation speed multiplier")
        
        # Random seed
        random_seed = st.number_input("Random Seed", value=config['simulation']['random_seed'], help="For reproducibility")
        
        st.divider()
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎬 Initialize", width="stretch"):
                # Create new simulation
                config['simulation']['duration'] = duration
                config['simulation']['random_seed'] = int(random_seed)
                
                sim = initialize_simulation(config)
                sim.set_controller_type(controller_type)
                sim.load_scenario(scenario)
                
                st.session_state.simulation = sim
                st.session_state.initialized = True
                st.session_state.running = False
                st.success("✅ Simulation initialized!")
        
        with col2:
            if st.button("🔄 Reset", width="stretch"):
                if st.session_state.simulation:
                    st.session_state.simulation.reset()
                    st.session_state.running = False
                    st.success("✅ Simulation reset!")
        
        st.divider()
        
        # Run controls
        if st.session_state.initialized:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("▶️ Run" if not st.session_state.running else "⏸️ Pause", width="stretch"):
                    st.session_state.running = not st.session_state.running
            
            with col2:
                if st.button("⏭️ Step", width="stretch"):
                    if st.session_state.simulation:
                        st.session_state.simulation.step()
                        st.rerun()
            
            with col3:
                if st.button("⏹️ Stop", width="stretch"):
                    st.session_state.running = False
                    if st.session_state.simulation:
                        st.session_state.simulation.stop()
    
    # Main content area
    if not st.session_state.initialized:
        # Welcome screen
        st.info("👈 Configure parameters and click **Initialize** to start")
        
        # Display project information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Grid Size", "3×3")
            st.caption("9 intersections")
        with col2:
            st.metric("Agent Types", "2")
            st.caption("Signals + Vehicles")
        with col3:
            st.metric("Controllers", "2")
            st.caption("Fixed + Adaptive")
        
        st.divider()
        
        # PEAS specification
        st.subheader("📋 PEAS Model for Traffic Signal Agent")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Performance Measures:**
            - Minimize waiting time
            - Minimize queue length
            - Minimize travel time
            - Maximize throughput
            
            **Environment:**
            - 3×3 intersection grid
            - Bidirectional roads
            - Stochastic vehicle arrivals
            - Dynamic traffic patterns
            """)
        
        with col2:
            st.markdown("""
            **Actuators:**
            - Signal phase control
            - Safe transitions (GREEN → YELLOW → ALL_RED)
            
            **Sensors:**
            - Local queue lengths
            - Vehicle waiting times
            - Neighbor signal states
            - Communication messages
            """)
        
        return
    
    # Simulation is initialized - show dashboard
    sim = st.session_state.simulation
    
    # Auto-run if running
    if st.session_state.running and sim.running:
        for _ in range(speed):
            sim.step()
            if not sim.running:
                st.session_state.running = False
                break
        time.sleep(0.05)
        st.rerun()
    
    # Status bar
    state = sim.get_state()
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Timestep", f"{state['current_step']}/{sim.duration}")
    with col2:
        st.metric("Vehicles", state['num_vehicles'])
    with col3:
        st.metric("Completed", state['completed_vehicles'])
    with col4:
        st.metric("Scenario", scenario.replace('_', ' ').title())
    with col5:
        st.metric("Controller", controller_type.title())
    with col6:
        status = "🟢 Running" if sim.running else "🔴 Stopped"
        st.metric("Status", status)
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ Network View",
        "📊 Metrics & Charts",
        "🤖 AI Decisions",
        "📈 Comparison"
    ])
    
    with tab1:
        # Network visualization
        render_network_view(sim)
    
    with tab2:
        # Metrics and performance charts
        render_metrics_charts(sim)
    
    with tab3:
        # AI decision explanations
        render_ai_decisions(sim)
    
    with tab4:
        # Comparison with baseline
        render_comparison_view(sim, config)


def render_ai_decisions(sim: ATLASSimulation):
    """
    Render AI decision explanations.
    
    Args:
        sim: Simulation instance
    """
    st.subheader("🤖 AI Decision Explanations")
    
    if not sim.signal_agents:
        st.warning("No signal agents initialized yet.")
        return
    
    # Select intersection
    intersection_ids = list(sim.signal_agents.keys())
    selected_intersection = st.selectbox("Select Intersection", intersection_ids)
    
    if selected_intersection in sim.signal_agents:
        signal = sim.signal_agents[selected_intersection]
        
        # Display current state
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Phase", signal.current_phase.value.upper())
            st.metric("Phase Elapsed", f"{signal.phase_elapsed}s")
        
        with col2:
            st.metric("NS Queue", signal.queue_state.get('north', 0) + signal.queue_state.get('south', 0))
            st.metric("EW Queue", signal.queue_state.get('east', 0) + signal.queue_state.get('west', 0))
        
        with col3:
            st.metric("Phase Changes", signal.phase_changes)
            st.metric("Neighbors", len(signal.neighbors))
        
        st.divider()
        
        # Controller explanation
        st.subheader("📝 Controller Decision")
        
        observation = signal._build_observation()
        
        if hasattr(signal.controller, 'get_explanation'):
            explanation = signal.controller.get_explanation(observation)
            st.code(explanation, language=None)
        else:
            st.info("Current controller does not provide detailed explanations.")
        
        # Detailed observations
        with st.expander("🔍 Detailed Observations"):
            st.json(observation)
        
        # Neighbor states
        if signal.neighbor_states:
            with st.expander("👥 Neighbor States"):
                for neighbor_id, neighbor_state in signal.neighbor_states.items():
                    st.write(f"**{neighbor_id}:**", neighbor_state)


def render_comparison_view(sim: ATLASSimulation, config: Dict[str, Any]):
    """
    Render comparison with baseline.
    
    Args:
        sim: Current simulation instance
        config: Configuration dictionary
    """
    st.subheader("📈 Performance Comparison")
    
    st.info("""
    **Experimental Protocol:**
    1. Run simulation with Fixed-Time controller (baseline)
    2. Run simulation with Adaptive controller (same seed and scenario)
    3. Compare performance metrics
    """)
    
    if sim.current_step > 0:
        # Show current run statistics
        stats = sim.metrics.get_summary_statistics()
        
        if stats:
            st.subheader("📊 Current Run Statistics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Avg Waiting Time", f"{stats.get('avg_waiting_time', 0):.2f}s")
                st.metric("Max Waiting Time", f"{stats.get('max_waiting_time', 0):.2f}s")
            
            with col2:
                st.metric("Avg Queue Length", f"{stats.get('avg_queue_length', 0):.2f}")
                st.metric("Max Queue Length", f"{stats.get('max_queue_length', 0)}")
            
            with col3:
                st.metric("Avg Travel Time", f"{stats.get('avg_travel_time', 0):.2f}s")
                st.metric("Completed Vehicles", f"{stats.get('total_completed', 0)}")
            
            # Export option
            st.divider()
            if st.button("💾 Export Metrics to CSV"):
                filename = f"atlas_metrics_{sim.controller_type}_{sim.scenario_name}_{sim.random_seed}.csv"
                sim.metrics.export_to_csv(filename)
                st.success(f"✅ Metrics exported to {filename}")
    else:
        st.warning("Run simulation to see performance statistics.")
