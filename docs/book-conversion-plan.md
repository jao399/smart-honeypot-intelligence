# Book Manuscript Conversion Plan

## Source Document Reviewed

`Smart Honeypot System Using Reinforcement Learning and Human Feedback - Thesis.docx`

This document is strong as a master's thesis, but it should not be published as a book in its current thesis form. The book should be a separate manuscript derived from the thesis and companion repository.

## Required Changes Before Publication

### 1. Remove University Submission Front Matter

Remove thesis-only material before public or commercial publication:

- APU thesis title/submission page.
- Declaration of thesis confidentiality.
- Supervisor declaration.
- Originality and exclusiveness declaration.
- Student ID/signature fields.
- Library copy-rights and university-property wording.

Action: confirm university publication and commercial reuse rules before using thesis-derived content in a public book.

### 2. Replace Placeholder Text

The acknowledgements still contain:

- `[Supervisor Name]`
- `[University/Department Name]`

Action: replace these with final names or rewrite acknowledgements for a public book audience.

### 3. Use a Consistent Professional Author Name

The thesis title page uses only `Amjad`.

Recommended book author name:

```text
Amgad Hussein Alzomi
```

Action: use this name consistently on the title page, proposal, citation metadata, author bio, acknowledgements, and publisher submission materials.

### 4. Convert Thesis Language Into Book Language

Rewrite thesis phrasing throughout the manuscript.

| Thesis wording | Book wording |
| --- | --- |
| This thesis presents... | This book explains... |
| This study seeks... | This chapter explores... |
| The research contributes... | The project demonstrates... |
| Chapter 6 will... | In the next chapter... |
| The findings of this thesis... | These results show... |

Action: perform a full manuscript pass for tone, reader guidance, and chapter transitions.

### 5. Fix the Reinforcement Learning Methodology Consistency

The thesis currently says the methodology incorporates:

- Double DQN
- Dueling DQN
- PPO

The implementation and public companion repository show:

- Tabular Q-learning
- Compact state buckets
- Interpretable Q-table inspection
- Human-in-the-loop reward feedback

Publishing risk: readers may see this as overclaiming unless the mismatch is fixed.

Recommended fix:

- Present tabular Q-learning as the implemented method.
- Move Double DQN, Dueling DQN, and PPO to a future extensions section.
- Explain that tabular Q-learning was chosen for interpretability, reproducibility, and suitability for a teaching-focused prototype.

### 6. Strengthen Results Evidence

The thesis discusses:

- 1,000 training episodes.
- 137 human interventions.
- 62 reward adjustments.
- 75 manual action overrides.
- Responsiveness degradation beyond roughly 500 concurrent sessions.
- Baseline vs RL-only vs RL+HITL comparisons.

Book-ready results need clearer evidence tables.

Recommended tables:

| Experiment | Static Baseline | RL-only | RL+HITL |
| --- | ---: | ---: | ---: |
| Final average reward | TBD | TBD | TBD |
| Episodes to convergence | TBD | ~600 | ~400 |
| Average session duration | TBD | TBD | TBD |
| Requests per session | TBD | TBD | TBD |
| Service diversity index | TBD | TBD | TBD |
| Human interventions | 0 | 0 | 137 |

Action: extract or rerun experiment data from the companion app and replace discussion-only claims with tables and figures.

### 7. Add Practical Book Labs

The book should include hands-on labs that connect directly to the GitHub companion repository.

Recommended labs:

1. Lab 1: Setting up the Smart Honeypot
2. Lab 2: Running the Streamlit Dashboard
3. Lab 3: Training the Q-learning Agent
4. Lab 4: Adding Human Feedback
5. Lab 5: Reading Q-table and Audit Logs
6. Lab 6: Safe Deployment and Isolation Checklist

Each lab should include:

- Objective
- Prerequisites
- Commands
- Expected output
- Troubleshooting notes
- Security and ethics note

## Recommended Book Title

```text
Smart Honeypots with Reinforcement Learning:
Building Adaptive Cyber Deception Systems with Human Feedback
```

## Proposed Book Structure

1. Introduction to smart honeypots and cyber deception
2. Honeypot data, threat intelligence, and sessionization
3. Reinforcement learning foundations for security readers
4. Modeling honeypot interactions as RL episodes
5. Implementing tabular Q-learning for adaptive deception
6. Human-in-the-loop feedback and analyst control
7. Building and running the Streamlit dashboard
8. Experiments, results, and evaluation tables
9. Practical labs and companion repository walkthrough
10. Safe deployment, ethics, and isolation checklist
11. Future extensions: Double DQN, Dueling DQN, PPO, multi-agent simulation, and SIEM integration

## Conversion Workflow

1. Create a new book manuscript file; do not overwrite the thesis.
2. Remove all university declaration and submission pages.
3. Replace title and author metadata.
4. Rewrite acknowledgements.
5. Convert abstract into a book preface.
6. Rewrite Chapter 1 for readers rather than examiners.
7. Move thesis methodology details into practical design chapters.
8. Fix RL consistency by making tabular Q-learning the implemented method.
9. Add results tables and companion-repo reproduction instructions.
10. Add labs after the implementation chapter.
11. Add a book-style conclusion and future roadmap.
12. Perform a legal/permission check before commercial publication.

## Publication Verdict

Do not publish the thesis PDF directly as the book.

Use the thesis as the technical foundation, then publish a separate book manuscript that is cleaned, legally safe, practically structured, and aligned with the public GitHub companion repository.
