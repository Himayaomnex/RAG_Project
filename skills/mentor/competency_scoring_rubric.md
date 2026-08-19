# Trainee Competency Scoring Rubric (Mentor Agent)

Supporting reference guide for `mentor-pedagogical-evaluation` skill.

## 1. Multi-Dimensional Competency Rubric (1–10 Scale)

All evaluation scores produced by the Mentor Agent must be calibrated against this objective rubric:

| Score Band | Classification | Preparation | Conceptual Depth | Code Quality | Engagement |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **9 – 10** | **Mastery / Autonomous** | Pre-tested benchmarks, committed working code before meeting, prepared edge cases. | Explains trade-offs (e.g. latency vs accuracy), understands low-level math/architecture. | Modular, fully typed, docstrings, unit tests, robust error handling. | Leads technical discussion, proposes novel architectures, mentors peers. |
| **7 – 8** | **Proficient / Solid** | Completed assigned tasks, demonstrated working pipeline demo. | Solid understanding of core concepts with minor gaps in distributed scaling. | Working code with clean structure; minor edge-case refactorings needed. | Actively responds, explains reasoning clearly, asks insightful questions. |
| **5 – 6** | **Developing / Needs Guidance** | Partial implementation; ran into blockers and waited for review. | High-level understanding but struggles when probed on underlying mechanism. | Code works but monolithic, lacks modularity or error handling. | Participates when prompted; relies on mentor to structure next steps. |
| **1 – 4** | **Novice / Significant Gaps** | Incomplete tasks without documented blocker analysis. | Fundamental misconceptions (e.g. confusing retrieval with generation). | Broken scripts, unhandled exceptions, no local reproduction. | Passive engagement, unable to explain code logic. |

---

## 2. Bloom's Taxonomy Technical Assessment Matrix

When diagnosing trainee explanations:
* **Remembering**: Can recall parameter names (e.g. `top_k`, `temperature`).
* **Understanding**: Explains why temperature affects output entropy.
* **Applying**: Uses Qdrant filters to restrict search by date or speaker.
* **Analyzing**: Identifies why a specific chunking strategy drops recall for tabular data.
* **Evaluating**: Compares Gemini Flash vs DeepSeek V4 Pro latency/cost trade-offs.
* **Creating**: Designs custom hybrid multi-agent routing graphs from scratch.
