# Phase 2 — Input Prioritization with SpreadEx

Phase 2 prioritizes test inputs using **SpreadEx** after fixing the subject program, embedding model, and input generator selected from Phase 1 Cluster Coverage results.

The selected generator is determined automatically from the Phase 1 RankSum summary for the chosen embedding model. A manual generator override is also available for debugging.

For the current artifact smoke test, we use:

- Subject: `KARATEJS`
- Embedding model: `UNIXCODER`
- Runs: `1`
- Small budgets: `1,2,3`

---

## Step-by-Step Guides

| Step | Guide | Script / Area | Purpose |
|------|-------|---------------|---------|
| Setup | [Prerequisites](phase2_input_prioritization/00_prerequisites.md) | Phase 1 outputs | Confirm embeddings, mutation profiles, and cluster coverage exist |
| 1 | [Run Input Prioritization](phase2_input_prioritization/step01_run_input_prioritization.md) | `PRIORATIZATION/inputs_selection_main.py` | Run SpreadEx and Random over input budgets |
| 2 | [Aggregate AUC Results](phase2_input_prioritization/step02_aggregate_auc_results.md) | `PRIORATIZATION/research_questions/auc_rq_util.py` | Summarize AUC across runs/SUTs |
| 3 | [RQ3 Early Fault Detection](phase2_input_prioritization/step03_rq3_early_fault_detection.md) | `early_fault_detection_util.py` | Aggregate `MS@K` and `T2K` metrics |
| 4 | [RQ4 Stability Analysis](phase2_input_prioritization/step04_rq4_stability_analysis.md) | `stability_compare_util.py` | Aggregate random stability and comparison metrics |

---

## Suggested Run Order

1. Read [Prerequisites](phase2_input_prioritization/00_prerequisites.md).
2. Run [Step 1](phase2_input_prioritization/step01_run_input_prioritization.md) with the KarateJS smoke-test command.
3. Run [Step 2](phase2_input_prioritization/step02_aggregate_auc_results.md) to aggregate AUC.
4. Run [Step 3](phase2_input_prioritization/step03_rq3_early_fault_detection.md) to aggregate early fault-detection results.
5. Run [Step 4](phase2_input_prioritization/step04_rq4_stability_analysis.md) to aggregate stability results.
6. Read [Data Format and Result Interpretation](data_format_and_interpretation.md) after the reports are generated.

---

## Output Summary

```tree
PRIORATIZATION/ALL_SUT_RESULTS/
├── AUC_AGGREGATED/
│   ├── GLOBAL_AUC_SUMMARY.csv
│   └── <SUT>_AUC.csv
└── <SUT>/
    ├── <MODEL>/run_<N>/
    │   ├── AUC_Summary.csv
    │   ├── AUC_Clean.png
    │   ├── AUC_Shaded.png
    │   ├── Random_AUC_Table.csv
    │   ├── SpreadEx_RR_AUC_Table.csv
    │   └── cluster_analysis/
    ├── rq3_tables/RQ3_run_<N>.csv
    ├── rq3_summary/RQ3_GLOBAL_<SUT>.csv
    ├── rq4_tables/RQ4_run_<N>.csv
    ├── rq4_summary/RQ4_GLOBAL_<SUT>.csv
    └── tool_selection/
```

For the archived paper results, the corresponding processed outputs are under `data/Input_Prioritization_Results/`.
