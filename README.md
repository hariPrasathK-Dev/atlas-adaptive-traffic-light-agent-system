# ATLAS - Adaptive Traffic Light Agent System

A multi-agent traffic simulation system demonstrating classical AI techniques including A* pathfinding, adaptive signal control, and multi-agent coordination. Built as a case study for Foundations of Artificial Intelligence coursework.

## Overview

ATLAS simulates a 3x3 grid traffic network with intelligent vehicle and signal agents. The system demonstrates key AI concepts:

- **Multi-agent systems** with autonomous vehicle and signal agents
- **A* search algorithm** for optimal pathfinding with dynamic rerouting
- **Adaptive control** using pressure-based signal timing
- **Agent coordination** through message passing
- **PEAS formulation** for both vehicle and signal agents

## Features

### Core Simulation
- 3x3 intersection grid with bidirectional roads
- Stochastic vehicle arrivals (Poisson process)
- Real-time congestion tracking and dynamic routing
- Multiple failure scenarios (incidents, sensor failures, communication failures)

### Vehicle Agents
- A* pathfinding with Manhattan heuristic
- Congestion-aware routing with automatic rerouting
- State machine: PLANNING, MOVING, WAITING, REROUTING, COMPLETED, STUCK
- Performance tracking (waiting time, travel time, distance)

### Signal Agents
- Fixed-time controller (baseline)
- Adaptive controller with pressure-based switching
- Neighbor coordination for wave propagation
- Safe phase transitions (green → yellow → all-red)

### Visualization Dashboard
- Real-time network visualization with traffic flow
- Live metrics charts (waiting time, throughput, congestion, signal switches)
- AI decision explanations for adaptive controller
- Scenario selector and controller comparison
- Clean Google-style UI with Inter and Roboto fonts

## Architecture

```
atlas/
├── app.py                  # Streamlit application entry point
├── config.yaml            # Simulation configuration
├── requirements.txt       # Python dependencies
├── pytest.ini            # Test configuration
├── src/
│   ├── agents/
│   │   ├── vehicle_agent.py    # Vehicle agent with A* routing
│   │   └── signal_agent.py     # Traffic signal agent
│   ├── ai/
│   │   ├── astar.py           # A* search implementation
│   │   ├── fixed_controller.py     # Fixed-time baseline
│   │   └── adaptive_controller.py  # Pressure-based adaptive
│   ├── communication/
│   │   └── message_bus.py     # Agent message passing
│   ├── environment/
│   │   ├── road_network.py    # Network graph structure
│   │   └── simulation.py      # Main simulation engine
│   ├── metrics/
│   │   ├── collector.py       # Performance metrics
│   │   └── decision_log.py    # AI decision logging
│   └── visualization/
│       ├── dashboard.py       # Main dashboard layout
│       ├── network_view.py    # Traffic network visualization
│       ├── charts.py          # Metrics charts
│       └── controls.py        # Simulation controls
└── tests/
    ├── test_astar.py          # A* algorithm tests
    ├── test_signal_agent.py   # Signal controller tests
    ├── test_communication.py  # Message bus tests
    └── test_scenarios.py      # End-to-end scenario tests
```

## Technology Stack

- **Python 3.11+** - Core programming language
- **Mesa 3.3.1** - Agent-based modeling framework
- **NetworkX** - Graph structure and algorithms
- **NumPy & Pandas** - Numerical computing and data analysis
- **Plotly** - Interactive visualizations
- **Streamlit** - Web dashboard framework
- **pytest** - Testing framework

## Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd atlas
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv myvenv
   # Windows
   .\myvenv\Scripts\activate
   # Linux/Mac
   source myvenv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Simulation

Start the Streamlit dashboard:
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### Dashboard Controls

1. **Initialize** - Configure and create a new simulation
   - Select scenario (normal, heavy, incident, sensor_failure, comm_failure)
   - Choose controller type (fixed-time or adaptive)
   - Set simulation duration

2. **Run Controls**
   - Run/Pause - Start or pause continuous simulation
   - Step - Execute single timestep
   - Stop - Halt simulation
   - Reset - Return to initial state

3. **Visualization Tabs**
   - Network View - Live traffic visualization with congestion heatmap
   - Metrics - Real-time performance charts
   - AI Decisions - Adaptive controller decision explanations
   - Comparison - Side-by-side baseline vs adaptive analysis

### Running Tests

Execute the test suite:
```bash
pytest -v
```

Run specific test categories:
```bash
pytest tests/test_astar.py -v          # A* algorithm tests
pytest tests/test_signal_agent.py -v   # Controller tests
pytest tests/test_scenarios.py -v      # Integration tests
```

## Scenarios

### Normal Traffic
- Steady arrival rate (λ=1.0 vehicles/timestep)
- Baseline performance measurement

### Heavy Congestion
- High arrival rate (λ=2.5 vehicles/timestep)
- Tests adaptive controller under load

### Unequal Flow
- Directional traffic bias
- North-South higher than East-West

### Incident
- Mid-simulation road blockage
- Tests rerouting capabilities

### Sensor Failure
- Signal loses queue/wait observations
- Falls back to timing-based control

### Communication Failure
- Agent message passing disabled
- Tests local-only decision making

## PEAS Formulation

### Vehicle Agent
- **Performance**: Minimize travel time, reach destination
- **Environment**: Road network, traffic signals, other vehicles
- **Actuators**: Move to next intersection
- **Sensors**: Current position, route validity, signal state

### Signal Agent
- **Performance**: Minimize average waiting time, maximize throughput
- **Environment**: Road network, vehicle queues, neighbor signals
- **Actuators**: Change signal phase
- **Sensors**: Queue lengths, waiting times, neighbor states

## Configuration

Edit `config.yaml` to customize simulation parameters:

```yaml
simulation:
  duration: 300        # Simulation length (timesteps)
  grid_size: 3         # Network grid dimensions
  random_seed: 42      # Reproducibility seed

signal:
  min_green: 10        # Minimum green phase (seconds)
  max_green: 45        # Maximum green phase (seconds)
  yellow: 3            # Yellow phase duration
  all_red: 1           # All-red clearance time

ai:
  coordination_weight: 0.30          # Neighbor influence (0-1)
  phase_switch_threshold: 1.15       # Pressure ratio threshold

traffic:
  normal_arrival_rate: 1.0           # Poisson λ for normal
  heavy_arrival_rate: 2.5            # Poisson λ for heavy
```

## Performance Metrics

The system tracks comprehensive performance indicators:

- **Waiting Time** - Time spent stopped at red signals
- **Travel Time** - Total journey duration
- **Queue Length** - Vehicles waiting per direction
- **Throughput** - Completed journeys per timestep
- **Congestion Level** - Road capacity utilization
- **Signal Switches** - Phase changes per intersection

## AI Techniques

### A* Search
- **Heuristic**: Manhattan distance on grid
- **Cost Function**: f(n) = g(n) + h(n)
- **Dynamic Weighting**: Congestion-aware edge costs
- **Admissibility**: Guaranteed optimal paths

### Adaptive Signal Control
- **Local Pressure**: Queue length weighted by wait time
- **Coordinated Pressure**: Includes downstream neighbor state
- **Decision Logic**: Switch when pressure imbalance exceeds threshold
- **Constraints**: Minimum/maximum green time bounds

### Multi-Agent Coordination
- **Message Types**: Traffic state, incident notification, coordination request
- **Communication**: Asynchronous message bus
- **Neighbor Discovery**: Network topology-based
- **Failure Handling**: Graceful degradation when communication fails

## Testing

Test coverage includes:

- **Unit Tests**: A* search, controllers, message bus
- **Integration Tests**: Signal phase transitions, multi-agent communication
- **Scenario Tests**: End-to-end simulation scenarios
- **Edge Cases**: Invalid routes, blocked roads, sensor failures

Current test coverage: 59% (55/55 tests passing)

## Known Limitations

- Grid-based topology only (no arbitrary networks)
- Simplified vehicle dynamics (no acceleration/deceleration)
- Homogeneous vehicles (no trucks, buses, emergency vehicles)
- Single intersection per grid cell
- No pedestrian or bicycle traffic

## Future Enhancements

- Reinforcement learning-based signal control
- Real-world map import (OpenStreetMap)
- Vehicle heterogeneity and priority
- Multi-lane roads with lane changing
- Public transit integration
- Historical data replay

## License

MIT License - See LICENSE file for details

## Authors

Developed as a case study for Foundations of Artificial Intelligence coursework.

## Acknowledgments

- Mesa framework for agent-based modeling
- NetworkX for graph algorithms
- Streamlit for rapid dashboard development
- Classical AI techniques from Russell & Norvig's "Artificial Intelligence: A Modern Approach"

## Contact

For questions or issues, please refer to the course instructor or teaching assistants.
