"""
Network Visualization for ATLAS
Interactive road network display with live vehicle positions
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, List, Tuple
import numpy as np


# ─────────────────────────────────────────────
# Colour helpers
# ─────────────────────────────────────────────

PHASE_COLORS = {
    'ns_green':   '#00CC44',
    'ew_green':   '#00CC44',
    'ns_yellow':  '#FFD700',
    'ew_yellow':  '#FFD700',
    'all_red_ns': '#FF3333',
    'all_red_ew': '#FF3333',
}

PHASE_LABELS = {
    'ns_green':   'NS GREEN',
    'ew_green':   'EW GREEN',
    'ns_yellow':  'NS YELLOW',
    'ew_yellow':  'EW YELLOW',
    'all_red_ns': 'ALL RED',
    'all_red_ew': 'ALL RED',
}


def _road_color(road):
    if road.blocked:
        return '#FF3333', 5
    if road.congestion_ratio > 0.7:
        return '#FF8C00', 4
    if road.congestion_ratio > 0.4:
        return '#FFD700', 3
    return '#B0B8C1', 2


def _lerp(p0, p1, t):
    return (p0[0] + t * (p1[0] - p0[0]),
            p0[1] + t * (p1[1] - p0[1]))


def render_network_view(simulation):
    """
    Render interactive network view with roads, intersections, and vehicles.
    """
    network = simulation.network
    fig = go.Figure()

    # ── 1. Roads ──────────────────────────────────────────────────────────────
    for (source, dest), road in network.roads.items():
        sx, sy = network.get_position(source)
        dx, dy = network.get_position(dest)
        color, width = _road_color(road)

        hover_txt = (
            f"<b>{source} → {dest}</b><br>"
            f"Vehicles: {len(road.vehicles)}<br>"
            f"Congestion: {road.congestion_ratio:.0%}"
            + ("<br>🚫 BLOCKED" if road.blocked else "")
        )
        fig.add_trace(go.Scatter(
            x=[sx, dx], y=[sy, dy],
            mode='lines',
            line=dict(color=color, width=width),
            hovertext=hover_txt,
            hoverinfo='text',
            showlegend=False,
        ))

        # Direction arrow
        mx, my = (sx + dx) / 2, (sy + dy) / 2
        ox, oy = (dx - sx) * 0.1, (dy - sy) * 0.1
        fig.add_annotation(
            x=mx, y=my,
            ax=mx - ox, ay=my - oy,
            xref='x', yref='y', axref='x', ayref='y',
            showarrow=True,
            arrowhead=3, arrowsize=1.2, arrowwidth=1.5,
            arrowcolor=color,
        )

    # ── 2. Vehicles on roads ──────────────────────────────────────────────────
    # Build a set of vehicle IDs that are already placed on a road segment
    STATE_MAP = {
        'moving':    ('Moving',    '#00BFFF'),
        'waiting':   ('Waiting',   '#FF8C00'),
        'rerouting': ('Rerouting', '#DA70D6'),
        'stuck':     ('Stuck',     '#FF3333'),
        'planning':  ('Planning',  '#AAAAAA'),
    }

    vxs, vys, vhovers, vcolors = [], [], [], []
    # track which vehicles have been placed (they appear in road.vehicles)
    placed_ids = set()

    for (source, dest), road in network.roads.items():
        if not road.vehicles:
            continue
        sx, sy = network.get_position(source)
        dx, dy = network.get_position(dest)
        n = len(road.vehicles)

        for i, vid in enumerate(road.vehicles):
            placed_ids.add(vid)
            t = 0.2 + 0.6 * (i + 1) / (n + 1)
            vx, vy = _lerp((sx, sy), (dx, dy), t)
            vxs.append(vx)
            vys.append(vy)

            v = simulation.vehicle_agents.get(vid)
            if v:
                label, vcol = STATE_MAP.get(v.state.value, ('Moving', '#00BFFF'))
                hover = (
                    f"<b>{vid}</b> — {label}<br>"
                    f"On road: {source}→{dest}<br>"
                    f"Dest: {v.destination}<br>"
                    f"Wait: {v.waiting_time}s | Trip: {v.total_travel_time}s"
                )
            else:
                hover = f"<b>{vid}</b>"
                vcol = '#00BFFF'

            vhovers.append(hover)
            vcolors.append(vcol)

    # ── Vehicles at intersection nodes (current_road is None / not yet on a road) ──
    # Collect them per node so we can offset multiple vehicles at the same intersection
    node_vehicles: dict = {}
    for vid, v in simulation.vehicle_agents.items():
        if vid not in placed_ids:
            node = v.current_node
            node_vehicles.setdefault(node, []).append(vid)

    OFFSETS = [(25, 0), (-25, 0), (0, 25), (0, -25),
               (20, 20), (-20, 20), (20, -20), (-20, -20)]

    for node, vids in node_vehicles.items():
        nx, ny = network.get_position(node)
        for k, vid in enumerate(vids):
            ox, oy = OFFSETS[k % len(OFFSETS)]
            vxs.append(nx + ox)
            vys.append(ny + oy)

            v = simulation.vehicle_agents.get(vid)
            if v:
                label, vcol = STATE_MAP.get(v.state.value, ('Moving', '#00BFFF'))
                hover = (
                    f"<b>{vid}</b> — {label}<br>"
                    f"At node: {node}<br>"
                    f"Dest: {v.destination}<br>"
                    f"Wait: {v.waiting_time}s | Trip: {v.total_travel_time}s"
                )
            else:
                hover = f"<b>{vid}</b>"
                vcol = '#AAAAAA'

            vhovers.append(hover)
            vcolors.append(vcol)

    if vxs:
        fig.add_trace(go.Scatter(
            x=vxs, y=vys,
            mode='markers',
            marker=dict(
                symbol='circle',
                size=11,
                color=vcolors,
                line=dict(color='white', width=1.5),
            ),
            hovertext=vhovers,
            hoverinfo='text',
            name='Vehicles',
            showlegend=True,
        ))

    # ── 3. Intersection nodes ──────────────────────────────────────────────────
    for iid in network.intersections:
        px, py = network.get_position(iid)

        if iid in simulation.signal_agents:
            signal = simulation.signal_agents[iid]
            phase  = signal.current_phase.value
            color  = PHASE_COLORS.get(phase, '#888888')
            label  = PHASE_LABELS.get(phase, phase)
            ns_q = signal.queue_state.get('north', 0) + signal.queue_state.get('south', 0)
            ew_q = signal.queue_state.get('east',  0) + signal.queue_state.get('west',  0)
            hover = (
                f"<b>{iid}</b><br>"
                f"Phase: {label}<br>"
                f"Elapsed: {signal.phase_elapsed}s<br>"
                f"NS queue: {ns_q}  |  EW queue: {ew_q}<br>"
                f"Phase changes: {signal.phase_changes}"
            )
        else:
            color = '#666666'
            hover = f"<b>{iid}</b>"

        fig.add_trace(go.Scatter(
            x=[px], y=[py],
            mode='markers+text',
            marker=dict(size=40, color=color, line=dict(color='#111', width=2.5)),
            text=iid,
            textposition='middle center',
            textfont=dict(size=9, color='black', family='Arial Black'),
            hovertext=hover,
            hoverinfo='text',
            showlegend=False,
        ))

    # ── 4. Layout ──────────────────────────────────────────────────────────────
    positions = [network.get_position(i) for i in network.intersections]
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    pad = 100

    fig.update_layout(
        title=dict(
            text=f"Live Traffic Network  —  Step {simulation.current_step} / {simulation.duration}",
            font=dict(size=14, color='white'),
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(xs) - pad, max(xs) + pad],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(ys) - pad, max(ys) + pad],
            scaleanchor='x',
            scaleratio=1,
        ),
        plot_bgcolor='#0F1117',
        paper_bgcolor='#0F1117',
        font=dict(color='white'),
        height=580,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        legend=dict(
            x=0.01, y=0.99,
            bgcolor='rgba(20,20,30,0.85)',
            bordercolor='#555',
            borderwidth=1,
            font=dict(color='white', size=11),
        ),
        hovermode='closest',
    )

    # Use unique key tied to current_step so Streamlit re-renders every step
    st.plotly_chart(fig, use_container_width=True,
                    key=f"net_{simulation.current_step}")

    # ── 5. Quick stats (all live / change as simulation runs) ─────────────────
    stats = network.get_statistics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Vehicles",  len(simulation.vehicle_agents))
    c2.metric("Completed Trips",  len(simulation.completed_vehicles))
    c3.metric("Total Spawned",    simulation.total_vehicles_spawned)
    c4.metric("Congested Roads",  f"{stats['congested_roads']} / {stats['num_roads']}")

    st.caption(
        "**Nodes:** 🟢 NS/EW Green | 🟡 Yellow | 🔴 All-Red  ·  "
        "**Roads:** Light = Clear | Yellow = Moderate | Orange = Congested | Red = Blocked  ·  "
        "**Dots:** 🔵 Moving | 🟠 Waiting | 🔴 Stuck"
    )

