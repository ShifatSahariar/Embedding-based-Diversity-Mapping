[Back to Phase 2 overview](../phase2_input_prioritization.md) | [Previous: Step 1 — Run Input Prioritization](step01_run_input_prioritization.md) | [Next: Step 3 — RQ3 Early Fault Detection](step03_rq3_early_fault_detection.md)

---

## Step 2 — Aggregate AUC Results

**Script:** `PRIORATIZATION/research_questions/auc_rq_util.py`

**Purpose:** Step 2 summarizes the per-run `AUC_Summary.csv` files created by Step 1. It compares the area under the mutation-score-vs-budget curve for **SpreadEx** and **Random**. Use this step after Step 1 has produced at least one `AUC_Summary.csv`.

For the KarateJS smoke test:

```bash
python PRIORATIZATION/research_questions/auc_rq_util.py --subjects KARATEJS
```

For all available SUT result folders:

```bash
python PRIORATIZATION/research_questions/auc_rq_util.py
```

This aggregates the per-run Phase 2 outputs into:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/AUC_AGGREGATED/
```

The folder contains per-SUT and global AUC comparisons between **SpreadEx** and **Random**, including Wilcoxon signed-rank test results and Cliff's Delta effect sizes.

For the smoke test, this confirms the aggregation code is working. The statistical values are not meaningful until the full experiment has multiple runs and paper-scale budgets.

---
