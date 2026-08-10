# CampusOpt: AI-Assisted Resource Optimizer

> Hybrid optimization and prediction for timetables, hostels, and mess planning.

**Difficulty:** Moderate to High

---

## 1. The Real Problem: Why This Arises

Timetabling, hostel allocation, and mess planning are classic **constrained, multi-stakeholder problems**. Wherever these are handled without a formal system, the result tends to be clashes, uneven allocation, and guesswork on demand for attendance and meal counts. Treating this as "just a scheduling app" misses the point: the hard part is the underlying **constraint-satisfaction or optimization problem**, with prediction feeding realistic inputs into it.

A common shortcut is to skip the optimization formulation entirely and ship a UI with hardcoded rules, which looks like a product but solves nothing algorithmically. This problem statement requires the **actual optimization model**, not a rules-based approximation of one.

---

## 2. Problem Statement

Build a hybrid system that combines a **formal optimization model** — with explicit decision variables, constraints, and an objective function — with a **predictive ML component** (for example, forecasting attendance or mess demand) over real or realistically simulated NIT Mizoram data.

---

## 3. Deliverables (Prototype Phase)

- **Formal Model:** Explicitly stated decision variables, constraints, and an objective function, solved with a real solver such as OR-Tools or PuLP — not hardcoded `if/else` rules.

- **Solution Quality Report:** The optimality gap compared with a naive baseline (for example, random or greedy allocation), along with runtime measured at two to three dataset sizes to demonstrate scalability.

- **Predictive Component:** A trained model for attendance or demand forecasting, with a genuine train/test split and a reported error metric such as MAE, RMSE, or accuracy.

- **Infeasibility Handling:** A demonstrated stress test showing what the system does when constraints conflict (for example, an over-booked hostel); the system must degrade gracefully rather than crash or silently ignore constraints.

- **Working Prototype:** A usable interface where a judge can input constraints or demand and see the optimized schedule or allocation, including the infeasible case.

---

## 4. Tech Stack

| Layer              | Technology                                                                 |
| ------------------ | -------------------------------------------------------------------------- |
| **Optimization**   | Python with Google OR-Tools (CP-SAT solver) or PuLP                        |
| **Data Wrangling** | pandas                                                                     |
| **ML / Prediction**| scikit-learn or XGBoost (linear regression acceptable for teams newer to ML)|
| **Backend**        | FastAPI                                                                    |
| **Frontend**       | React or Streamlit                                                         |
| **Visualization**  | Plotly or Matplotlib                                                       |

> [!NOTE]
> Small pilot instances may be prototyped in Excel Solver or Google Sheets, but the submitted deliverable **must** use a real solver as described above, since the core requirement is a formal, solver-based optimization model rather than hardcoded or spreadsheet logic.

---

## 5. Hardware Expectation

| Scenario                          | RAM Required |
| --------------------------------- | ------------ |
| Small–medium instances (OR-Tools / PuLP) | 4–8 GB       |
| ML + solver + live dashboard simultaneously | 16 GB        |

OR-Tools and PuLP are lightweight CPU solvers. The higher memory tier is only needed if the predictive component (e.g., XGBoost on a larger tabular dataset) runs alongside the solver and a live dashboard simultaneously.

---

## 6. Submission Guidelines

- **GitHub Repository:** Maintain a single GitHub repository containing all code, documentation, datasets or data samples, and evaluation results. The repository may remain private during development but **must be made public** immediately once the code is submitted.

- **Mandatory Collaborator:** The repository must include [`coding-ai-club-nitmz`](https://github.com/coding-ai-club-nitmz) as a collaborator **from the start of development**, not just at submission. Submissions without this will not be evaluated.

- **Commit History:** Judges will review commit history as part of evaluation. Build incrementally — a repository with all code added in a single commit close to the deadline will be viewed unfavorably.

- **README Requirement:** The README must clearly state the problem chosen, setup instructions, tech stack used, and where to find the evaluation results and metrics. Include every command needed for judges to set up and run the project from scratch. Where possible, also provide a live deployed link (e.g., a hosted website or Hugging Face Space).

- **Programming Language & Tools:** Any language, framework, or library may be used. The tech stack listed above is illustrative, not mandatory.

- **No Starter Material:** No starter code or datasets are provided. Every team builds its solution and sources or creates its data entirely from scratch.

- **Communication:** Join the official WhatsApp group. All doubts, clarifications, and updates will be shared there or via `coding.club@nitmz.ac.in`.

> [!IMPORTANT]
> Focus entirely on approach quality, technical rigor, and a working prototype. Do **not** spend time on security hardening, authentication, or adversarial robustness — these are not relevant until you have a working solution in place.

---

## 7. Judging Rubric

| Criteria                                          | Weight |
| ------------------------------------------------- | ------ |
| Problem formulation and baseline comparison        | 20%    |
| Data handling (collection, cleaning, labelling)    | 20%    |
| Core technique correctness and justification       | 25%    |
| Evaluation rigor (real metrics, not demo impressions) | 20% |
| Working prototype completeness                     | 15%    |

### Presentation & Evaluation Process

- Every team will present their work and give a **live demo** of their working prototype to the judges.
- A **Q&A round** with the judges will follow each team's presentation and demo.
- An official base presentation template will be provided closer to the event.
- Final scores combine the rubric above with the presentation, demo, and Q&A round.

---

## 8. Difficulty Calibration Note

| Problem       | Difficulty       | Notes                                                                 |
| ------------- | ---------------- | --------------------------------------------------------------------- |
| **CampusOpt** | 🟠 **Moderate–High** | **Well-documented constraint optimization, but tooling does much of the heavy lifting** |

> [!TIP]
> Judges calibrate expectations relative to each problem's inherent ceiling rather than grading all four on one flat scale. A strong, rigorous CampusOpt submission is not automatically considered less impressive than a mediocre CurriGraph attempt — **execution quality is evaluated within the chosen problem's difficulty band**.

---

## 9. Relevant FAQs

**Can we change our chosen problem statement after registration?**
Teams may switch only before the submission deadline, and only by informing the organizing team in advance via the WhatsApp group or `coding.club@nitmz.ac.in`.

**Is the use of AI tools or LLMs allowed while building the solution?**
Yes, but the core technique (optimization model, ML prediction) must be genuinely implemented and understood by the team. Judges may ask questions about the implementation during evaluation.

**Does our commit history matter?**
Yes. Build and commit incrementally. A single-commit repository near the deadline will be viewed unfavorably.

**Will partial submissions be evaluated?**
Yes, on a proportional basis per the rubric. Submit whatever working components you have rather than nothing.

**Are there restrictions on datasets?**
Datasets may be self-collected, publicly available, or realistically simulated. Any external dataset must be credited in the README with source and licensing terms.

**Will there be a presentation or demo round?**
Yes. Every team presents and demos their prototype, followed by Q&A with judges. Teams must use the official presentation template (shared closer to the event).

**No assigned mentors.**
Teams work independently. Doubts can be raised in the WhatsApp group or via `coding.club@nitmz.ac.in`.
