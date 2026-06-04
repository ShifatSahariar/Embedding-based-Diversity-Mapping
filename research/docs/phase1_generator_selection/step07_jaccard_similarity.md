[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 6 — Correlation Analysis](step06_correlation_analysis.md) | [Next: Step 8 — Analysis Reports and Plots](step08_analysis_reports_plots.md)

---

## 🥉 Step 7 — Jaccard Similarity (Top-K Agreement)

**Script:** `Jaccard_Similarity_MS_CC.py`

### Purpose
Evaluates **ranking consistency** between MS and CC across generators using **Top-K Jaccard similarity**.

This step compares:
- the Top-K generators ranked by Cluster Coverage (CC)
- the Top-K generators ranked by Mutation Score (MS)

The Jaccard score is:
```
|TopK_CC ∩ TopK_MS| / |TopK_CC ∪ TopK_MS|
```

### Before running
Confirm that Step 4 and Step 5 have produced, for each run:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/cluster_coverage_summary_run_<N>.csv
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/mutation_metrics.csv
```

For KarateJS:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/cluster_coverage_summary_run_1.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/mutation_metrics.csv
```

### Recommended smoke test from terminal
Run only the first result run:
```bash
python Jaccard_Similarity_MS_CC.py --subject karatejs --runs 1 --top_ks 1,2,3,4
```

With the PyCharm virtual environment used in this artifact:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Jaccard_Similarity_MS_CC.py \
  --subject karatejs \
  --runs 1 \
  --top_ks 1,2,3,4
```

Expected smoke-test outputs:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/jaccard_similarity/topK_1.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/jaccard_similarity/topK_2.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/jaccard_similarity/topK_3.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/jaccard_similarity/topK_4.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/correlations_summary/jaccard_summary_by_model.csv
```

### Running from an IDE such as PyCharm
Open `Jaccard_Similarity_MS_CC.py` and use these script parameters for a smoke test:
```bash
--subject karatejs --runs 1 --top_ks 1,2,3,4
```

For the full Step 7 run:
```bash
--subject karatejs --top_ks 1,2,3,4
```

### Full run from terminal
After the smoke test succeeds:
```bash
python Jaccard_Similarity_MS_CC.py --subject karatejs --top_ks 1,2,3,4
```

or with the artifact virtual environment:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Jaccard_Similarity_MS_CC.py \
  --subject karatejs \
  --top_ks 1,2,3,4
```

### Output
Each run produces one file per K:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/jaccard_similarity/topK_<K>.csv
```

Each `topK_<K>.csv` contains:
- **Embedding_Model**: embedding model used
- **TopK**: K value
- **Jaccard**: Top-K overlap score
- **Top_Cov_Tools**: generators selected by cluster coverage
- **Top_MS_Tools**: generators selected by mutation score

The subject-level summary is:
```
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/jaccard_summary_by_model.csv
```

with:
- **Embedding_Model**
- **TopK**
- **Jaccard_Mean**
- **Jaccard_Std**

If only one embedding model has embeddings available, the summary will contain only that model.

---
