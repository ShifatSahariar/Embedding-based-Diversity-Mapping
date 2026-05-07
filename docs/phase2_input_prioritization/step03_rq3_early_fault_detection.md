[Back to Phase 2 overview](../phase2_input_prioritization.md) | [Previous: Step 2 — Aggregate AUC Results](step02_aggregate_auc_results.md) | [Next: Step 4 — RQ4 Stability Analysis](step04_rq4_stability_analysis.md)

---

## Step 3 — Reproduce RQ3: Early Fault Detection

**Script:** `PRIORATIZATION/research_questions/early_fault_detection_util.py`

**Purpose:** Step 3 aggregates the per-run RQ3 tables created by Step 1. RQ3 asks how quickly SpreadEx detects faults under small input budgets. It summarizes **Mutation Score at budget K (`MS@K`)** and **Tests-to-Kill (`T2K`)** for SpreadEx and Random.

For the KarateJS smoke test:

```bash
python PRIORATIZATION/research_questions/early_fault_detection_util.py --subject KARATEJS
```

From Python, the equivalent call is:

```python
aggregate_rq3_for_sut("KARATEJS")
```

Output:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/KARATEJS/rq3_summary/RQ3_GLOBAL_KARATEJS.csv
```

This reports:

- Mutation Score at budget K (`MS@K`)
- Tests-to-Kill (`T2K`)
- Budget-specific prioritization effectiveness

For the smoke test, the file aggregates only `RQ3_run_1.csv`. For full reproduction, Step 1 should be run over all independent runs first, then Step 3 will aggregate all available RQ3 per-run files.

---
