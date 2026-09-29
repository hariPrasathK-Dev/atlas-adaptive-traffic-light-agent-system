"""
Network Visualization for ATLAS
Interactive road network display
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, List, Tuple


def get_signal_color(phase: str) -> str:
    """
    Get color for signal phase visualization.
    
    Args:
        phase: Signal phase name
        
    Returns:
        Color hex code
    """
    colors = {
        'ns_green': '#00FF00',
        'ns_yellow': '#FFFF00',
        'ew_green': '#00FF00',
        'ew_yellow': '#FFFF00',
        'all_red_ns': '#FF0000',
        'all_red_ew': '#FF0000'
    }
    return colors.get(phase, '#999999')


def render_network_view(simulation):
    """
    Render interactive network view with roads, intersections, and vehicles.
    
    Args:
        simulation: ATLASSimulation instance
    """
    st.subheader("🗺️ Traffic Network View")
    
    network = simulation.network
    
    # Create figure
    fig = go.Figure()
    
    # Draw roads (edges)
    for (source, dest), road in network.roads.items():
        source_pos = network.get_position(source)
        dest_pos = network.get_position(dest)
        
        # Determine road color based on congestion
        if road.blocked:
            color = 'red'
            width = 4
        elif road.congestion_ratio > 0.7:
            color = 'orange'
            width = 3
        elif road.congestion_ratio > 0.4:
            color = 'yellow'
            width = 2
        else:
            color = 'lightgray'
            width = 2
        
        # Draw road
        fig.add_trace(go.Scatter(
            x=[source_pos[0], dest_pos[0]],
            y=[source_pos[1], dest_pos[1]],
            mode='lines',
            line=dict(color=color, width=width),
            hovertext=f"{source} → {dest}<br>Vehicles: {len(road.vehicles)}<br>Congestion: {road.congestion_ratio:.1%}",
            hoverinfo='text',
            showlegend=False
        ))
        
        # Add arrow for direction
        mid_x = (source_pos[0] + dest_pos[0]) / 2
        mid_y = (source_pos[1] + dest_pos[1]) / 2
        dx = dest_pos[0] - source_pos[0]
        dy = dest_pos[1] - source_pos[1]
        
        fig.add_annotation(
            x=mid_x,
            y=mid_y,
            ax=mid_x - dx * 0.1,
            ay=mid_y - dy * 0.1,
            xref='x',
            yref='y',
            axref='x',
            ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor=color
        )
    
    # Draw intersections (nodes)
    for intersection_id in network.intersections:
        pos = network.get_position(intersection_id)
        
        # Determine intersection color based on signal state
        if intersection_id in simulation.signal_agents:
            signal = simulation.signal_agents[intersection_id]
            node_color = get_signal_color(signal.current_phase.value)
            
            # Create hover text
            hover_text = (
                f"<b>{intersection_id}</b><br>"
                f"Phase: {signal.current_phase.value.upper()}<br>"
                f"Elapsed: {signal.phase_elapsed}s<br>"
                f"NS Queue: {signal.queue_state.get('north', 0) + signal.queue_state.get('south', 0)}<br>"
                f"EW Queue: {signal.queue_state.get('east', 0) + signal.queue_state.get('west', 0)}"
            )
        else:
            node_color = 'gray'
            hover_text = f"<b>{intersection_id}</b>"
        
        # Draw intersection
        fig.add_trace(go.Scatter(
            x=[pos[0]],
            y=[pos[1]],
            mode='markers+text',
            marker=dict(
                size=30,
                color=node_color,
                line=dict(color='black', width=2)
            ),
            text=intersection_id,
            textposition='middle center',
            textfont=dict(size=10, color='black'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
    
    # Update layout
    fig.update_layout(
        title="Traffic Network with Signal States",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=600,
        showlegend=False,
        hovermode='closest'
    )
    
    # Display figure
    st.plotly_chart(fig, width="stretch")
    
    # Legend
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Signals:** 🟢 Green | 🟡 Yellow | 🔴 Red")
    with col2:
        st.markdown("**Roads:** Gray = Clear | Yellow = Moderate | Orange = Congested | Red = Blocked")
    with col3:
        st.markdown(f"**Active Vehicles:** {len(simulation.vehicle_agents)}")
    
    # Network statistics
    st.divider()
    stats = network.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Intersections", stats['num_intersections'])
    with col2:
        st.metric("Roads", stats['num_roads'])
    with col3:
        st.metric("Congested Roads", stats['congested_roads'])
    with col4:
        st.metric("Avg Congestion", f"{stats['avg_congestion']:.1%}")
