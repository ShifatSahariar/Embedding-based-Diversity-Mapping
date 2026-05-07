# Data Format and Result Interpretation

This guide explains how to read the processed reports after either:

- inspecting the archived results under `data/`, or
- reproducing the workflow and generating fresh reports under the experiment output folders.

Use this document after completing:

- [Phase 1: Generator Selection](phase1_generator_selection.md)
- [Phase 2: Input Prioritization](phase2_input_prioritization.md)

---

## Where Results Live

Archived paper results:

```tree
data/
├── Generator_Selection_Results/
├── Input_Prioritization_Results/
└── Paper-Figure_plots/
```

Freshly reproduced Phase 1 results:

```tree
FUZZ_TOOL_SELECTION/result/<SUT>/
```

Freshly reproduced Phase 2 results:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/
```

The file names and interpretation are the same in the archived and reproduced result folders.

---

## Phase 1: Generator Selection Results

Phase 1 answers: **Which generator should be selected for a subject program?**

Start with:

```tree
data/Generator_Selection_Results/<SUT>/correlations_summary/
```

or, after reproduction:

```tree
FUZZ_TOOL_SELECTION/result/<SUT>/correlations_summary/
```

### Key Files

| File | Purpose | How to Read |
|------|---------|-------------|
| `final_correlation_summary.csv` | Aggregated relationship between Cluster Coverage (CC) and Mutation Score (MS) | Higher positive `Mean_Coverage–MS` means CC better tracks mutation effectiveness |
| `jaccard_summary_by_model.csv` | Top-K agreement between CC-based and MS-based generator rankings | Higher `Jaccard` values mean stronger ranking agreement |
| `cluster_coverage_summary_all_runs.csv` | Mean CC values per generator/model/cluster setting | Used to choose the highest-coverage generator once the embedding model is fixed |
| `summary_plots/` | Visual summaries of CC-MS relations | Useful for quick inspection and paper-figure validation |

### `final_correlation_summary.csv`

Important columns:

- `Configuration`: embedding model and clustering algorithm pair.
- `Mean_Coverage–MS`: mean Spearman correlation between CC and MS across runs.
- `Wilcoxon_p`: Wilcoxon signed-rank p-value against a zero-correlation baseline.

Interpretation:

- Positive `Mean_Coverage–MS` means generators with higher CC tend to also have higher MS.
- Smaller `Wilcoxon_p` gives stronger evidence that the correlation is above the zero baseline.
- This file helps decide whether CC is a reliable proxy for mutation effectiveness.

### `jaccard_summary_by_model.csv`

This file compares the Top-K generators selected by:

- mutation score, and
- cluster coverage.

Interpretation:

- `Jaccard@K = 1.0`: perfect Top-K overlap.
- `Jaccard@K = 0.0`: no Top-K overlap.
- Higher values indicate that CC identifies the same high-performing generators as mutation testing.

### `cluster_coverage_summary_all_runs.csv`

This file aggregates CC values across independent runs.

Use it after choosing a representative embedding model. For that model, compare generator columns and select the generator with the highest CC.

Typical generator-selection logic:

1. Use `final_correlation_summary.csv` and `jaccard_summary_by_model.csv` to identify a reliable embedding/model setting.
2. Use `cluster_coverage_summary_all_runs.csv` to rank generators by CC.
3. Carry the selected generator into Phase 2.

### Run-Level Folders

Run-level folders such as `run_1/` to `run_10/` contain:

- `cluster_coverage_summary_run_<N>.csv`
- `mutation_metrics.csv`
- `correlations_table.csv`
- `selected_mutant_indices.txt`
- `jaccard_similarity/topK_<K>.csv`
- `analysis_plots/`

Use these for debugging, variance inspection, and reproduction checks. For paper-level verification, start with `correlations_summary/`.

---

## Phase 2: Input Prioritization Results

Phase 2 answers: **Given the selected generator, does SpreadEx prioritize inputs better and more stably than Random?**

Start with:

```tree
data/Input_Prioritization_Results/
```

or, after reproduction:

```tree
PRIORATIZATION/ALL_SUT_RESULTS/
```

### Key Folders

| Folder | Purpose |
|--------|---------|
| `AUC_AGGREGATED/` | Global and per-SUT AUC comparison between SpreadEx and Random |
| `<SUT>/<MODEL>/run_<N>/` | Per-run prioritization curves and AUC tables |
| `<SUT>/rq3_summary/` | Aggregated early fault-detection results |
| `<SUT>/rq4_summary/` | Aggregated stability results |
| `<SUT>/tool_selection/` | Phase 1 RankSum-derived generator selection used by Phase 2 |

### `AUC_AGGREGATED/GLOBAL_AUC_SUMMARY.csv`

This file summarizes SpreadEx vs Random across all available Phase 2 experiments.

Important rows:

- `SpreadEx_mean_AUC`: mean normalized AUC for SpreadEx.
- `Random_mean_AUC`: mean normalized AUC for Random.
- `Mean_diff`: `SpreadEx_mean_AUC - Random_mean_AUC`.
- `Wilcoxon_W`: Wilcoxon signed-rank statistic.
- `p_greater`: one-sided p-value for SpreadEx being greater than Random.
- `Cliffs_delta`: effect size.

Interpretation:

- Higher AUC means better cumulative mutation-score performance across budgets.
- Positive `Mean_diff` favors SpreadEx.
- Smaller `p_greater` gives stronger evidence that SpreadEx outperforms Random.
- Positive `Cliffs_delta` indicates SpreadEx tends to have higher AUC than Random.

### `AUC_AGGREGATED/<SUT>_AUC.csv`

This file gives the same AUC comparison for one SUT.

Use it to understand whether the global trend is consistent for each subject program.

### `<SUT>/<MODEL>/run_<N>/`

Each run folder contains:

- `AUC_Summary.csv`: normalized AUC per approach for one run.
- `SpreadEx_RR_AUC_Table.csv`: budget-by-budget mutation score for SpreadEx.
- `Random_AUC_Table.csv`: budget-by-budget mutation score for Random.
- `AUC_Clean.png`: MS-vs-budget plot.
- `AUC_Shaded.png`: MS-vs-budget plot with variability shading.
- `cluster_analysis/`: cluster-level mutation-diversity diagnostics.

Use this folder when you want to inspect an individual experiment rather than aggregated results.

### `<SUT>/rq3_summary/RQ3_GLOBAL_<SUT>.csv`

RQ3 measures early fault detection.

Important metrics:

- `MS_K`: Mutation Score at budget `K`.
- `T2K`: Tests-to-Kill, the average number of selected inputs needed to kill a mutant.

Interpretation:

- Higher `MS_K` is better.
- Lower `T2K` is better.
- Compare `SpreadEx_mean` and `Random_mean` to see which approach detects faults earlier.

### `<SUT>/rq4_summary/RQ4_GLOBAL_<SUT>.csv`

RQ4 measures stability and variability.

Important metrics:

- `STD`: standard deviation of Random mutation score at each budget.
- `PEG`: Gaussian estimate of the probability that Random is at least as good as SpreadEx.
- `PMR`: empirical probability that Random is better than SpreadEx.
- `PKHM`: probability that Random kills at most half of its expected mutants.

Interpretation:

- Lower `STD` means Random is more stable.
- Lower `PEG` and `PMR` mean Random is less likely to match or beat SpreadEx.
- `PKHM` helps quantify poor Random outcomes under the same budget.

---

## Smoke Tests vs Full Results

The KarateJS smoke-test commands in the reproduction guide intentionally use tiny settings such as:

- one run,
- three inputs,
- budgets `1,2,3`,
- two Random repeats.

These smoke-test outputs are useful for checking that the pipeline works, but the values are not meaningful for paper-level interpretation.

For paper-scale interpretation, use:

- all independent runs,
- the full input budget schedule,
- the full selected generator/model configuration,
- archived processed results in `data/`.

---

## Recommended Reading Order

1. For paper-level validation, open `data/Generator_Selection_Results/<SUT>/correlations_summary/`.
2. Read `final_correlation_summary.csv` and `jaccard_summary_by_model.csv`.
3. Open `data/Input_Prioritization_Results/AUC_AGGREGATED/GLOBAL_AUC_SUMMARY.csv`.
4. Inspect `<SUT>/rq3_summary/` for early fault-detection behavior.
5. Inspect `<SUT>/rq4_summary/` for stability behavior.
6. Use run-level folders only when debugging or checking a specific independent run.

