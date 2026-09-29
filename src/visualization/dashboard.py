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
    
    # Auto-run if running: step the simulation then immediately rerun to refresh the UI
    if st.session_state.running and sim.running:
        for _ in range(max(1, speed)):
            sim.step()
            if not sim.running:
                st.session_state.running = False
                break
        # Small delay controls frame rate (~20 fps at delay=0.05)
        time.sleep(max(0.05, 0.5 / max(speed, 1)))
        st.rerun()
    elif st.session_state.running and not sim.running:
        st.session_state.running = False
        # ── Auto-save completed run for comparison ──────────────────────────
        _save_completed_run(sim)
        st.success("✅ Simulation complete! Results saved for comparison.")
    
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


def _save_completed_run(sim: ATLASSimulation):
    """
    Persist a completed simulation run into session state for comparison.
    Keyed by controller type so Fixed and Adaptive are stored separately.
    """
    if 'completed_runs' not in st.session_state:
        st.session_state.completed_runs = {}

    key = sim.controller_type  # 'fixed' or 'adaptive'
    st.session_state.completed_runs[key] = {
        'controller':   sim.controller_type,
        'scenario':     sim.scenario_name,
        'seed':         sim.random_seed,
        'duration':     sim.current_step,
        'stats':        sim.metrics.get_summary_statistics(),
        'history':      sim.metrics.history.copy(),          # MetricsSnapshot list
        'phase_changes': sum(a.phase_changes for a in sim.signal_agents.values()),
        'total_spawned': sim.total_vehicles_spawned,
    }


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
    True side-by-side comparison between Fixed-Time and Adaptive runs.
    Results are saved automatically when each run completes.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.subheader("📈 Performance Comparison: Fixed vs Adaptive")

    runs = st.session_state.get('completed_runs', {})

    # ── Protocol instructions ─────────────────────────────────────────────────
    with st.expander("ℹ️ How to compare", expanded=len(runs) < 2):
        st.markdown("""
        **Steps:**
        1. Select **Fixed-Time** controller → click **Initialize** → click **▶️ Run** → wait for completion
        2. Select **Adaptive** controller → click **Initialize** (same seed & scenario) → click **▶️ Run** → wait
        3. Results are saved automatically. Come back here to see the side-by-side comparison.

        > **Tip:** Use the same *Random Seed* for a fair comparison — both controllers face identical traffic.
        """)

    # ── Save button for current (possibly mid-run) result ─────────────────────
    col_save, _ = st.columns([1, 3])
    with col_save:
        if sim.current_step > 0:
            if st.button("💾 Save current run"):
                _save_completed_run(sim)
                st.success(f"Saved {sim.controller_type} run ({sim.current_step} steps)")

    # ── Show what's been saved ────────────────────────────────────────────────
    if not runs:
        st.info("No completed runs saved yet. Run a simulation and it will be saved here.")
        return

    st.divider()

    # ── Single-run summary (only one saved) ──────────────────────────────────
    if len(runs) == 1:
        key = list(runs.keys())[0]
        r = runs[key]
        st.info(f"Only **{r['controller'].title()}** run saved so far. Run the other controller to compare.")
        _render_single_run_stats(r)
        return

    # ── Side-by-side comparison (both runs present) ───────────────────────────
    fixed = runs.get('fixed')
    adap  = runs.get('adaptive')

    if not fixed or not adap:
        # Only one type saved; show what we have
        for r in runs.values():
            _render_single_run_stats(r)
        return

    sf = fixed['stats']
    sa = adap['stats']

    st.markdown(f"**Scenario:** {fixed['scenario'].replace('_',' ').title()}  |  "
                f"**Seed:** {fixed['seed']}  |  "
                f"**Steps:** Fixed={fixed['duration']}, Adaptive={adap['duration']}")
    st.divider()

    # ── Metric tiles with delta ───────────────────────────────────────────────
    METRICS = [
        ('avg_waiting_time',  'Avg Wait (s)',      True),
        ('max_waiting_time',  'Max Wait (s)',      True),
        ('avg_queue_length',  'Avg Queue',         True),
        ('max_queue_length',  'Max Queue',         True),
        ('avg_travel_time',   'Avg Travel (s)',    True),
        ('total_completed',   'Completed Trips',   False),
    ]

    cols = st.columns(len(METRICS))
    for col, (key, label, lower_is_better) in zip(cols, METRICS):
        fval = sf.get(key, 0)
        aval = sa.get(key, 0)
        if fval and fval != 0:
            pct = (aval - fval) / abs(fval) * 100
        else:
            pct = 0.0
        delta_str = f"{pct:+.1f}%"
        # delta_color: 'inverse' means green when negative (lower is better)
        delta_color = 'inverse' if lower_is_better else 'normal'
        col.metric(
            label,
            f"{aval:.1f}" if isinstance(aval, float) else str(aval),
            delta=delta_str,
            delta_color=delta_color,
            help=f"Fixed: {fval:.2f}" if isinstance(fval, float) else f"Fixed: {fval}"
        )

    # Phase change comparison
    st.divider()
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Fixed Phase Changes",    fixed['phase_changes'])
    pc2.metric("Adaptive Phase Changes", adap['phase_changes'])
    pc3.metric("Spawned (Fixed / Adap)",
               f"{fixed['total_spawned']} / {adap['total_spawned']}")

    # ── Time-series overlay charts ────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Time-Series Overlay")

    def ts(run, attr):
        return [getattr(s, attr) for s in run['history']]

    def steps(run):
        return [s.timestep for s in run['history']]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Avg Waiting Time',
            'Avg Queue Length',
            'Active Vehicles',
            'Cumulative Completed',
        )
    )
    BLUE, GREEN = '#4C9BE8', '#2ECC71'

    for attr, row, col, label in [
        ('avg_waiting_time', 1, 1, 'Wait (s)'),
        ('avg_queue_length', 1, 2, 'Queue'),
        ('total_vehicles',   2, 1, 'Vehicles'),
        ('throughput',       2, 2, 'Completed'),
    ]:
        fig.add_trace(go.Scatter(
            x=steps(fixed), y=ts(fixed, attr),
            name='Fixed', line=dict(color=BLUE),
            showlegend=(row == 1 and col == 1)
        ), row=row, col=col)
        fig.add_trace(go.Scatter(
            x=steps(adap), y=ts(adap, attr),
            name='Adaptive', line=dict(color=GREEN),
            showlegend=(row == 1 and col == 1)
        ), row=row, col=col)

    fig.update_layout(
        height=500,
        plot_bgcolor='#0F1117',
        paper_bgcolor='#0F1117',
        font=dict(color='white'),
        legend=dict(bgcolor='rgba(20,20,30,0.85)', bordercolor='#555', borderwidth=1),
    )
    fig.update_xaxes(title_text='Timestep', gridcolor='#333')
    fig.update_yaxes(gridcolor='#333')
    st.plotly_chart(fig, use_container_width=True)

    # ── Summary table ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Summary Table")
    import pandas as pd
    rows = []
    for key, label, lower_is_better in METRICS:
        fval = sf.get(key, 0)
        aval = sa.get(key, 0)
        pct  = ((aval - fval) / abs(fval) * 100) if fval else 0.0
        better = (pct < 0) == lower_is_better  # True if adaptive is better
        rows.append({
            'Metric':          label,
            'Fixed':           f"{fval:.2f}" if isinstance(fval, float) else str(fval),
            'Adaptive':        f"{aval:.2f}" if isinstance(aval, float) else str(aval),
            'Change':          f"{pct:+.1f}%",
            'Winner':          '🟢 Adaptive' if better else '🔵 Fixed',
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export
    st.divider()
    col_e1, col_e2, _ = st.columns([1, 1, 2])
    with col_e1:
        if st.button("💾 Export Fixed CSV"):
            fname = f"atlas_fixed_{fixed['scenario']}_{fixed['seed']}.csv"
            import io, csv
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(['timestep','avg_waiting_time','avg_queue_length','total_vehicles','throughput'])
            for s in fixed['history']:
                writer.writerow([s.timestep, s.avg_waiting_time, s.avg_queue_length, s.total_vehicles, s.throughput])
            st.download_button("⬇️ Download", buf.getvalue(), fname, mime='text/csv')
    with col_e2:
        if st.button("💾 Export Adaptive CSV"):
            fname = f"atlas_adaptive_{adap['scenario']}_{adap['seed']}.csv"
            import io, csv
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(['timestep','avg_waiting_time','avg_queue_length','total_vehicles','throughput'])
            for s in adap['history']:
                writer.writerow([s.timestep, s.avg_waiting_time, s.avg_queue_length, s.total_vehicles, s.throughput])
            st.download_button("⬇️ Download", buf.getvalue(), fname, mime='text/csv')


def _render_single_run_stats(r: dict):
    """Helper to display stats for a single saved run."""
    stats = r['stats']
    st.markdown(f"**Controller:** {r['controller'].title()}  |  **Scenario:** {r['scenario']}  |  "
                f"**Seed:** {r['seed']}  |  **Steps:** {r['duration']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Wait (s)",    f"{stats.get('avg_waiting_time', 0):.2f}")
    c1.metric("Max Wait (s)",    f"{stats.get('max_waiting_time', 0):.2f}")
    c2.metric("Avg Queue",       f"{stats.get('avg_queue_length', 0):.2f}")
    c2.metric("Max Queue",       f"{stats.get('max_queue_length', 0)}")
    c3.metric("Avg Travel (s)",  f"{stats.get('avg_travel_time', 0):.2f}")
    c3.metric("Completed",       f"{stats.get('total_completed', 0)}")

