# Experiment Guide

This guide maps the book companion workflow to the runnable Streamlit prototype.

## 1. Prepare the Environment

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

Start the application:

```bash
streamlit run app.py
```

## 2. Load the Dataset

Use the default dataset path:

```text
data/honeypots.json
```

The app also supports uploading a JSON file from the sidebar.

## 3. Configure the Environment

Recommended starting values:

- Session gap: `15` minutes
- Learning rate alpha: `0.20`
- Discount factor gamma: `0.95`
- Exploration rate epsilon: `0.20`
- Episodes per run: `20`
- Reward weights: `w1=1.0`, `w2=0.5`, `w3=0.2`

## 4. Train the Agent

Open the training controls and run a batch of episodes. Track:

- Episode reward trend
- Moving-average reward
- Action counts
- State visit counts
- Q-table values

## 5. Apply Human Feedback

Use the human-in-the-loop feedback panel to:

- Add global feedback to influence the next step.
- Store per-session feedback.
- Record analyst notes.
- Review audit logs for traceability.

## 6. Export Evidence

Use the export controls to save:

- Filtered honeypot data as CSV
- Environment history as CSV
- Audit logs as CSV
- Q-table snapshots as NumPy files

## Notes for Reproducibility

- Keep dataset, hyperparameters, and reward weights fixed when comparing runs.
- Save snapshots at major milestones.
- Record analyst feedback values and notes because they affect reward dynamics.
- Treat reported results as prototype research evidence unless reproduced across additional datasets.
