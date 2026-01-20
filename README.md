# Smart Honeypot Intelligence

A reinforcement learning-powered honeypot management system that adaptively responds to attacker behavior using Q-learning and human-in-the-loop (HITL) feedback.

## Overview

This platform leverages reinforcement learning to intelligently manage honeypot interactions with potential attackers. The system analyzes sessionized network activity, learns optimal response strategies, and enables security teams to provide real-time feedback to improve decision-making.

**Key Features:**
- **Adaptive Defense**: Uses Q-learning to learn optimal honeypot response strategies
- **Human-in-the-Loop**: Incorporates human expertise through real-time feedback mechanisms
- **Session Analysis**: Automatically sessionizes network traffic by source IP
- **Interactive Dashboard**: Streamlit-based web interface for monitoring and control
- **Behavior Analytics**: Comprehensive visualization of attacker patterns and tactics

## Architecture

### Core Components

1. **Reinforcement Learning Agent**: Tabular Q-learning agent that learns optimal honeypot responses
2. **Environment**: Simulates honeypot interactions with configurable reward functions
3. **State Space**: Based on service type, attack intensity, and recency patterns
4. **Action Space**: 
   - `default`: Standard honeypot behavior
   - `banner_variation`: Modify service banners
   - `latency_add`: Introduce artificial delays
   - `decoy_port_toggle`: Enable/disable decoy ports
   - `error_style_flip`: Alter error message styles

### Reward Structure

The system uses a weighted reward function with three components:

- **Session Length (w1)**: Rewards keeping attackers engaged longer
- **Follow-up Activity (w2)**: Encourages repeated interactions
- **Service Diversity (w3)**: Promotes exploration across multiple services

## Installation

### Requirements

- Python 3.8+ (Python 3.11 recommended)
- Dependencies listed in `requirements.txt`

### Setup

1. Clone or download the project:
```bash
cd project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Prepare your data:
   - Place honeypot logs in `data/honeypots.json`
   - Supported formats: JSON array or newline-delimited JSON (NDJSON)

## Usage

### Starting the Application

Run the Streamlit app:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Data Format

Your honeypot data should include the following fields:
- `timestamp`: ISO 8601 format timestamp
- `src_ip`: Source IP address
- `dest_ip`: Destination IP address
- `src_port`: Source port number
- `dest_port`: Destination port number
- `protocol`: Protocol name (e.g., "ssh", "http", "ftp")
- `action`: Action taken by the honeypot

Example:
```json
[
  {
    "timestamp": "2023-01-01T12:00:00.000",
    "src_ip": "192.168.1.100",
    "dest_ip": "10.0.0.1",
    "src_port": 54321,
    "dest_port": 22,
    "protocol": "ssh",
    "action": "default"
  }
]
```

### Configuration

Use the sidebar to configure:

**Dataset & Environment:**
- Dataset path or upload custom data
- Session gap (minutes of inactivity before new session)

**RL Hyperparameters:**
- Learning Rate (α): 0.01 - 1.0
- Discount Factor (γ): 0.0 - 0.999
- Exploration Rate (ε): 0.0 - 1.0
- Episodes per training run

**Reward Weights:**
- Adjust w1, w2, w3 to prioritize different objectives

### Training the Agent

1. Navigate to the **Training** tab
2. Configure hyperparameters in the sidebar
3. Click "Train Agent" to run training episodes
4. Monitor training progress and reward convergence
5. Provide human feedback during training (optional)

### Saving and Loading

**Save Agent:**
1. Enter a snapshot name in the sidebar
2. Click "Save snapshot"
3. Agent state saved to `snapshots/` directory

**Load Agent:**
1. Enter the snapshot name
2. Click "Load snapshot"
3. Previously trained agent is restored

### Analysis and Monitoring

The dashboard provides multiple tabs:

- **Overview**: Dataset statistics and session distribution
- **Training**: Agent training interface with real-time metrics
- **Analysis**: Behavior patterns, attack timelines, and service distribution
- **Q-Table Explorer**: Inspect learned state-action values
- **HITL Feedback**: Provide human feedback on agent decisions

## Project Structure

```
project/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── data/                 # Data directory
│   ├── honeypots.json    # Main honeypot log data
│   └── sample.json       # Sample data
└── snapshots/            # Saved agent snapshots
    ├── agent_snapshot.npy
    └── agent_snapshot1.npy
```

## Technical Details

### Sessionization

Network events are grouped into sessions based on:
- Source IP address
- Configurable idle timeout (default: 15 minutes)

### State Representation

States are tuples of `(service, intensity, recency)`:
- **service**: Service type (ssh, http, ftp, other)
- **intensity**: Request frequency (low/med/high)
- **recency**: Time since last seen (new/warm/frequent)

### Q-Learning Algorithm

- **Algorithm**: Tabular Q-learning
- **Update Rule**: Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') - Q(s,a)]
- **Exploration**: ε-greedy policy

## Export Options

All tabs support data export:
- **CSV**: Tables and logs
- **PNG**: Visualizations and charts
- **NPY**: Agent snapshots (Q-table)

## Contributing

This is a Final Year Project (FYP). For questions or contributions, please contact the project maintainer.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Web application framework
- [NumPy](https://numpy.org/) - Numerical computing
- [Pandas](https://pandas.pydata.org/) - Data analysis
- [Plotly](https://plotly.com/) - Interactive visualizations
- [Matplotlib](https://matplotlib.org/) & [Seaborn](https://seaborn.pydata.org/) - Statistical graphics

---

**Note**: This system is designed for research and educational purposes. Always ensure proper authorization before deploying honeypots in production environments.
