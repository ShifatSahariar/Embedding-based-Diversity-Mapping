[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 7 — Jaccard Similarity](step07_jaccard_similarity.md) | [Next: Step 9 — Adding a New Subject Program](step09_adding_new_subject_program.md)

---

## 📊 Step 8 — Analysis Reports and Plots

**Script:** `Analysis_Reports_Plots.py`

### Purpose
Generates visual reports after Phase 1 analysis is complete.

This step should be run after:
- Step 4: cluster coverage
- Step 5: mutation score computation
- Step 6: correlation analysis
- Step 7: Jaccard similarity

The script creates:
- per-run correlation boxplots
- per-run mutation score bar plots
- summary correlation plots
- Jaccard trend plots across Top-K values

### Before running
Confirm that these files exist:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/correlations_table.csv
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/mutation_metrics.csv
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/final_correlation_summary.csv
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/jaccard_summary_by_model.csv
```

For KarateJS:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/correlations_table.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/mutation_metrics.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/final_correlation_summary.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/jaccard_summary_by_model.csv
```

### Recommended smoke test from terminal
Run plots for the first run only:
```bash
python Analysis_Reports_Plots.py --subject karatejs --runs 1
```

With the PyCharm virtual environment used in this artifact:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Analysis_Reports_Plots.py \
  --subject karatejs \
  --runs 1
```

Expected smoke-test outputs:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/analysis_plots/mutation_scores.png
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/analysis_plots/Coverage–MS_by_Embedding_Model.png
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/analysis_plots/Coverage–MS_by_Cluster_Algo.png
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/summary_plots/
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/jaccard_similarity_trends.png
```

### Running from an IDE such as PyCharm
Open `Analysis_Reports_Plots.py` and use these script parameters for a smoke test:
```bash
--subject karatejs --runs 1
```

For the full Step 8 run:
```bash
--subject karatejs
```

The script uses a local `.plot_cache/` folder for Matplotlib cache files, so it can run in headless or restricted environments without needing access to the user's home cache directory.

### Full run from terminal
After the smoke test succeeds:
```bash
python Analysis_Reports_Plots.py --subject karatejs
```

or with the artifact virtual environment:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Analysis_Reports_Plots.py \
  --subject karatejs
```

### Output
Per-run plots:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/analysis_plots/
├── Coverage–MS_by_Embedding_Model.png
├── Coverage–MS_by_Cluster_Algo.png
└── mutation_scores.png
```

Summary plots:
```
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/summary_plots/
├── Mean_Coverage–MS_by_Embedding_Model.png
└── Mean_Coverage–MS_by_Cluster_Algo.png
```

Jaccard trend plot:
```
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/jaccard_similarity_trends.png
```

If only one embedding model or one clustering algorithm is available, some plots will contain only one category. This is expected for smoke tests or partial embedding runs.

---
