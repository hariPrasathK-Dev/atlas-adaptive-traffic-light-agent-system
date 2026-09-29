"""
Charts and Metrics Visualization for ATLAS
Performance graphs and statistics
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_metrics_charts(simulation):
    """
    Render performance metrics charts.
    
    Args:
        simulation: ATLASSimulation instance
    """
    st.subheader("📊 Performance Metrics")
    
    metrics = simulation.metrics
    
    if not metrics.history:
        st.warning("No metrics data yet. Run simulation to collect metrics.")
        return
    
    # Current metrics
    current = metrics.get_current_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Wait Time", f"{current.avg_waiting_time:.2f}s")
    with col2:
        st.metric("Avg Queue", f"{current.avg_queue_length:.1f}")
    with col3:
        st.metric("Throughput", current.throughput)
    with col4:
        st.metric("Stopped Vehicles", current.stopped_vehicles)
    
    # Time series charts
    st.divider()
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Waiting Time Over Time',
            'Queue Length Over Time',
            'Vehicle Count Over Time',
            'Throughput Over Time'
        )
    )
    
    # Get time series data
    timesteps = metrics.get_time_series('timestep')
    
    # Waiting time
    avg_wait = metrics.get_time_series('avg_waiting_time')
    max_wait = metrics.get_time_series('max_waiting_time')
    
    fig.add_trace(
        go.Scatter(x=timesteps, y=avg_wait, name='Avg Wait', line=dict(color='blue')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=timesteps, y=max_wait, name='Max Wait', line=dict(color='red', dash='dash')),
        row=1, col=1
    )
    
    # Queue length
    avg_queue = metrics.get_time_series('avg_queue_length')
    max_queue = metrics.get_time_series('max_queue_length')
    
    fig.add_trace(
        go.Scatter(x=timesteps, y=avg_queue, name='Avg Queue', line=dict(color='green')),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=timesteps, y=max_queue, name='Max Queue', line=dict(color='orange', dash='dash')),
        row=1, col=2
    )
    
    # Vehicle counts
    total_vehicles = metrics.get_time_series('total_vehicles')
    stopped_vehicles = metrics.get_time_series('stopped_vehicles')
    
    fig.add_trace(
        go.Scatter(x=timesteps, y=total_vehicles, name='Total', line=dict(color='purple')),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=timesteps, y=stopped_vehicles, name='Stopped', line=dict(color='brown', dash='dash')),
        row=2, col=1
    )
    
    # Throughput
    throughput = metrics.get_time_series('throughput')
    
    fig.add_trace(
        go.Scatter(x=timesteps, y=throughput, name='Completed', line=dict(color='teal')),
        row=2, col=2
    )
    
    # Update layout
    fig.update_xaxes(title_text="Timestep")
    fig.update_yaxes(title_text="Time (s)", row=1, col=1)
    fig.update_yaxes(title_text="Vehicles", row=1, col=2)
    fig.update_yaxes(title_text="Vehicles", row=2, col=1)
    fig.update_yaxes(title_text="Vehicles", row=2, col=2)
    
    fig.update_layout(height=700, showlegend=True)
    
    st.plotly_chart(fig, width="stretch")
    
    # Summary statistics
    st.divider()
    st.subheader("📈 Summary Statistics")
    
    summary = metrics.get_summary_statistics()
    if summary:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Avg Waiting Time", f"{summary.get('avg_waiting_time', 0):.2f}s")
            st.metric("Max Waiting Time", f"{summary.get('max_waiting_time', 0):.2f}s")
        
        with col2:
            st.metric("Avg Queue Length", f"{summary.get('avg_queue_length', 0):.2f}")
            st.metric("Max Queue Length", f"{summary.get('max_queue_length', 0)}")
        
        with col3:
            st.metric("Avg Travel Time", f"{summary.get('avg_travel_time', 0):.2f}s")
            st.metric("Total Completed", f"{summary.get('total_completed', 0)}")


def render_comparison_charts(metrics1, metrics2, label1: str = "Run 1", label2: str = "Run 2"):
    """
    Render comparison charts between two simulation runs.
    
    Args:
        metrics1: MetricsCollector from first run
        metrics2: MetricsCollector from second run
        label1: Label for first run
        label2: Label for second run
    """
    st.subheader("📊 Performance Comparison")
    
    if not metrics1.history or not metrics2.history:
        st.warning("Need data from both runs for comparison.")
        return
    
    # Get summary statistics
    stats1 = metrics1.get_summary_statistics()
    stats2 = metrics2.get_summary_statistics()
    
    # Calculate improvements
    improvements = metrics2.compare_with(metrics1)
    
    # Display comparison metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Avg Waiting Time",
            f"{stats2.get('avg_waiting_time', 0):.2f}s",
            delta=f"{improvements.get('avg_waiting_time_improvement_%', 0):.1f}%",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "Avg Queue Length",
            f"{stats2.get('avg_queue_length', 0):.2f}",
            delta=f"{improvements.get('avg_queue_length_improvement_%', 0):.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "Total Completed",
            f"{stats2.get('total_completed', 0)}",
            delta=f"{improvements.get('total_completed_improvement_%', 0):.1f}%",
            delta_color="normal"
        )
    
    # Comparison charts
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Waiting Time Comparison', 'Queue Length Comparison')
    )
    
    # Waiting time comparison
    timesteps1 = metrics1.get_time_series('timestep')
    timesteps2 = metrics2.get_time_series('timestep')
    wait1 = metrics1.get_time_series('avg_waiting_time')
    wait2 = metrics2.get_time_series('avg_waiting_time')
    
    fig.add_trace(
        go.Scatter(x=timesteps1, y=wait1, name=label1, line=dict(color='blue')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=timesteps2, y=wait2, name=label2, line=dict(color='green')),
        row=1, col=1
    )
    
    # Queue comparison
    queue1 = metrics1.get_time_series('avg_queue_length')
    queue2 = metrics2.get_time_series('avg_queue_length')
    
    fig.add_trace(
        go.Scatter(x=timesteps1, y=queue1, name=label1, line=dict(color='blue'), showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=timesteps2, y=queue2, name=label2, line=dict(color='green'), showlegend=False),
        row=1, col=2
    )
    
    fig.update_xaxes(title_text="Timestep")
    fig.update_yaxes(title_text="Time (s)", row=1, col=1)
    fig.update_yaxes(title_text="Vehicles", row=1, col=2)
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, width="stretch")
    
    # Detailed comparison table
    st.divider()
    st.subheader("📋 Detailed Comparison")
    
    comparison_data = {
        'Metric': [],
        label1: [],
        label2: [],
        'Improvement': []
    }
    
    metrics_to_compare = [
        ('avg_waiting_time', 'Avg Waiting Time (s)'),
        ('max_waiting_time', 'Max Waiting Time (s)'),
        ('avg_queue_length', 'Avg Queue Length'),
        ('max_queue_length', 'Max Queue Length'),
        ('avg_travel_time', 'Avg Travel Time (s)'),
        ('total_completed', 'Total Completed')
    ]
    
    for metric_key, metric_name in metrics_to_compare:
        comparison_data['Metric'].append(metric_name)
        comparison_data[label1].append(f"{stats1.get(metric_key, 0):.2f}")
        comparison_data[label2].append(f"{stats2.get(metric_key, 0):.2f}")
        
        imp_key = f"{metric_key}_improvement_%"
        if imp_key in improvements:
            comparison_data['Improvement'].append(f"{improvements[imp_key]:+.1f}%")
        else:
            comparison_data['Improvement'].append("N/A")
    
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, width="stretch", hide_index=True)
