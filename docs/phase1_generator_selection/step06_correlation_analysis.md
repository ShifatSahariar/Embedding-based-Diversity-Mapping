[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 5 — Mutation Score Computation](step05_mutation_score_computation.md) | [Next: Step 7 — Jaccard Similarity](step07_jaccard_similarity.md)

---

## 📈 Step 6 — Correlation Analysis (MS vs CC)

**Script:** `Correlations_MS_CC.py`

### Purpose
Computes **Spearman correlation** between:
- Cluster coverage (CC)
- Mutation score (MS)

across multiple runs and embedding models.

This step combines the Step 4 cluster coverage files and the Step 5 mutation metrics files.

### Before running
Confirm that every run folder under:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/
```
contains both files:
```
cluster_coverage_summary_run_<N>.csv
mutation_metrics.csv
```

For KarateJS:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/cluster_coverage_summary_run_1.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/mutation_metrics.csv
```

If one of these files is missing, rerun Step 4 or Step 5 before correlation analysis.

### Recommended smoke test from terminal
Run only the first result run:
```bash
python Correlations_MS_CC.py --subject karatejs --runs 1
```

With the PyCharm virtual environment used in this artifact:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Correlations_MS_CC.py \
  --subject karatejs \
  --runs 1
```

Expected smoke-test outputs:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/correlations_table.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/final_correlation_summary.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/cluster_coverage_summary_all_runs.csv
```

The one-run smoke test may leave `Wilcoxon_p` empty because Wilcoxon needs multiple runs.

### Running from an IDE such as PyCharm
Open `Correlations_MS_CC.py` and use these script parameters in the Run Configuration for a smoke test:
```bash
--subject karatejs --runs 1
```

For the full Step 6 run:
```bash
--subject karatejs
```

### Full run from terminal
After the smoke test succeeds:
```bash
python Correlations_MS_CC.py --subject karatejs
```

or with the artifact virtual environment:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Correlations_MS_CC.py \
  --subject karatejs
```

### How it works
1. For each run:
   - Reads `cluster_coverage_summary_*.csv` and `mutation_metrics.csv`
   - Builds a per-run correlation table:
     ```
     Configuration | Coverage–MS
     ```
2. Aggregates across runs:
   - Averages correlation per configuration  
   - Computes **Wilcoxon p-value** per embedding model (vs 0 baseline)
   - Produces a final unified summary table:
     ```
     Configuration | Mean_Coverage–MS | Wilcoxon_p
     ```

### Output
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/correlations_table.csv
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/final_correlation_summary.csv
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/cluster_coverage_summary_all_runs.csv
```

where:
- **correlations_table.csv**: per-run correlation between CC and MS for each model/cluster configuration
- **final_correlation_summary.csv**: mean `Coverage–MS` across runs plus `Wilcoxon_p`
- **cluster_coverage_summary_all_runs.csv**: mean and standard deviation of CC across runs

If only one embedding model has embeddings available, the summary will contain only that model's configurations. For example, if only UNIXCODER vectors exist, the final table will only include rows such as `UNIXCODER + Affinity`.

---
