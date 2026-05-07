[Back to Phase 2 overview](../phase2_input_prioritization.md) | [Previous: Prerequisites](00_prerequisites.md) | [Next: Step 2 — Aggregate AUC Results](step02_aggregate_auc_results.md)

---

## Step 1 — Run Input Prioritization

**Script:** `PRIORATIZATION/inputs_selection_main.py`

This script:

1. Reads Phase 1 cluster-coverage summaries.
2. Computes the RankSum winner for the selected embedding model.
3. Loads embeddings for the winning generator.
4. Loads matching mutation-killing profiles.
5. Runs SpreadEx and the Random baseline across the configured budgets.
6. Saves AUC curves plus RQ3/RQ4 per-run tables.

### KarateJS Smoke Test

Run from the repository root:

```bash
python PRIORATIZATION/inputs_selection_main.py \
  --subject KARATEJS \
  --model UNIXCODER \
  --runs 1 \
  --rank-runs 1 \
  --budgets 1,2,3 \
  --selection-repeats 2 \
  --limit 3 \
  --n-jobs 1
```

For our KarateJS smoke-test data, the Phase 1 RankSum winner for `UNIXCODER` is currently `isla_no_con`. The script selects this automatically unless `--generator-tool` is provided.

The small `--budgets 1,2,3` and `--limit 3` settings are only for the smoke test because the current KarateJS quick run has 3 inputs per generator. For full reproduction, use the paper-scale budgets and input limit.

### Full Run

```bash
python PRIORATIZATION/inputs_selection_main.py \
  --subject KARATEJS \
  --model UNIXCODER \
  --budgets 5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100 \
  --selection-repeats 50 \
  --limit 1000 \
  --n-jobs 1
```

Use `--runs 1` first if you want to test one independent run before launching all runs.

### IDE Execution

In PyCharm or VS Code, open `PRIORATIZATION/inputs_selection_main.py` and use the CLI-equivalent defaults or add run arguments:

```text
--subject KARATEJS --model UNIXCODER --runs 1 --rank-runs 1 --budgets 1,2,3 --selection-repeats 2 --limit 3 --n-jobs 1
```

For first-time runs, keep `--n-jobs 1` so clustering and ranking run sequentially.

### Useful Options

| Option | Meaning |
|--------|---------|
| `--subject` | SUT name, e.g., `KARATEJS`, `CALC`, `BASIC` |
| `--model` | Embedding model folder/name, e.g., `UNIXCODER`, `OpenAI` |
| `--runs` | Limit the number of embedding/profile runs processed |
| `--rank-runs` | Limit how many Phase 1 runs are used for RankSum generator selection |
| `--budgets` | Comma-separated input budgets |
| `--selection-repeats` | Repetitions for non-deterministic baselines such as Random |
| `--limit` | Maximum number of inputs loaded per run for the selected generator |
| `--n-jobs` | Parallel jobs; use `1` for smoke tests and debugging |
| `--generator-tool` | Optional manual generator prefix override, e.g., `fan_con` |

### Output

For the KarateJS smoke test, outputs are written under:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/KARATEJS/
├── tool_selection/
│   ├── ranksum_all_models.csv
│   ├── winning_tool_per_model.csv
│   └── filtered_mutation_profiles_run_1.csv
├── UNIXCODER/
│   └── run_1/
│       ├── AUC_Clean.png
│       ├── AUC_Shaded.png
│       ├── AUC_Summary.csv
│       ├── Random_AUC_Table.csv
│       ├── SpreadEx_RR_AUC_Table.csv
│       └── cluster_analysis/
├── rq3_tables/
│   └── RQ3_run_1.csv
└── rq4_tables/
    └── RQ4_run_1.csv
```

Warnings about undefined Spearman correlation can occur in very small smoke tests because all clusters or mutation values may be constant. This is expected for tiny runs and should disappear or become meaningful on larger runs.

---
