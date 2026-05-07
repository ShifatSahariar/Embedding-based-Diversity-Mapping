[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 3 — Mutation Analysis](step03_mutation_analysis.md) | [Next: Step 5 — Mutation Score Computation](step05_mutation_score_computation.md)

---

## 📊 Step 4 — Cluster Coverage Computation

**Script:** `Cluster_Coverage.py`

### Purpose
Computes **cluster coverage metrics** for each generator and model across runs.

Cluster coverage reflects how well a generator’s inputs cover the **clusters** identified in embedding space — acting as a diversity measure.

### Before running
Confirm that Step 2 has produced embedding vectors under:
```
EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/<SUT>/<MODEL>/run_<N>/
```

For example, for KarateJS and UNIXCODER:
```
EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/KARATEJS/UNIXCODER/run_1/
```

Each `run_<N>` folder should contain one `*_vector.txt` file for each generated input in the corresponding:
```
GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/<SUT>/input_pool_by_run_<N>/
```

### Recommended smoke test
First run only one run folder:
```bash
python Cluster_Coverage.py --subject karatejs --runs 1 --parallel false
```

This should create:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/cluster_coverage_summary_run_1.csv
```

Open the CSV and verify that it contains:
- `Model`
- `Run`
- `Cluster Algo`
- `K_eff`
- cluster quality columns such as `Silhouette`, `DBI`, and `CHI`
- one cluster-coverage column for each generator configuration

### Full run
After the smoke test succeeds:
```bash
python Cluster_Coverage.py --subject karatejs --parallel false
```

The script processes all available embedding `run_<N>` folders. Use `--parallel true` only after the sequential run works on your machine.

### Output
Each run produces:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/cluster_coverage_summary_run_<N>.csv
```

where:
- **Model**: embedding model used
- **Run**: input/embedding run identifier
- **Cluster Algo**: clustering algorithm used
- **K_eff**: effective number of clusters
- Remaining columns report the **cluster coverage values** achieved by each generator configuration

These outputs are later used to:
- compare generators based on diversity,
- compute correlations with mutation-based effectiveness,
- and guide generator selection.

---
