# Book Companion

This folder contains companion material for **Smart Honeypot System Using Reinforcement Learning and Human Feedback**.

The goal is to help readers connect the thesis/book concepts to the runnable prototype in this repository.

## Contents

- [Experiment guide](experiment-guide.md): Steps for reproducing the Streamlit training workflow.
- [Dataset format](dataset-format.md): Expected honeypot log schema and sample event structure.
- [Book Proposal](book-proposal.md): Publisher-ready overview, audience, outline, and sample chapter plan.
- [Book Conversion Plan](book-conversion-plan.md): Required changes before turning the thesis into a public book manuscript.
- [Publisher Submission Email](publisher-submission-email.md): Short email/message templates for contacting editors.

## Suggested Reader Flow

1. Read the project overview in the repository `README.md`.
2. Install dependencies from `requirements.txt`.
3. Run `streamlit run app.py`.
4. Load `data/honeypots.json`.
5. Train the Q-learning agent and inspect reward trends, Q-table values, and analyst feedback logs.

## Research Context

The prototype demonstrates adaptive cyber deception through:

- Sessionized honeypot traffic analysis.
- Tabular Q-learning over compact state buckets.
- Human-in-the-loop reward feedback.
- Dashboard-based monitoring and export workflows.

Use this material as a practical companion to the book, not as a production security deployment guide.
