[Back to Phase 2 overview](../phase2_input_prioritization.md) | [Previous: Step 3 — RQ3 Early Fault Detection](step03_rq3_early_fault_detection.md)

---

## Step 4 — Reproduce RQ4: Stability Analysis

**Script:** `PRIORATIZATION/research_questions/stability_compare_util.py`

**Purpose:** Step 4 aggregates the per-run RQ4 tables created by Step 1. RQ4 measures the stability of Random relative to the deterministic SpreadEx result. It summarizes the variability of Random and the probability that Random matches or exceeds SpreadEx under each budget.

For the KarateJS smoke test:

```bash
python PRIORATIZATION/research_questions/stability_compare_util.py --subject KARATEJS
```

From Python, the equivalent call is:

```python
aggregate_rq4_for_sut("KARATEJS")
```

Output:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/KARATEJS/rq4_summary/RQ4_GLOBAL_KARATEJS.csv
```

This reports:

- `STD@K`: variability across random runs
- `PKHM@K`: probability of killing at most half the expected mutants
- `PEG@K` / `PMR@K`: random-vs-SpreadEx comparison probabilities

For the smoke test, the file aggregates only `RQ4_run_1.csv`. For full reproduction, run Step 1 over all independent runs first, then Step 4 will aggregate all available RQ4 per-run files.
