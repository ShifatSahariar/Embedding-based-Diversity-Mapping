## Interpreting Generator Selection Results (`data/Generator_Selection_Results/`)

This section explains how to inspect and interpret the experimental results for
**Phase 1: Generator Selection**, as reported in the paper.  
All files in this directory are **final, processed results**—no execution is
required to validate the findings.

---

### Directory Structure
```tree
data/Generator_Selection_Results/
├── <SUT_NAME>/
│   ├── correlations_summary/
│   │   ├── cluster_coverage_summary_all_runs.csv
│   │   ├── final_correlation_summary.csv
│   │   ├── jaccard_summary_by_model.csv
│   │   └── summary_plots/
│   │       ├── Mean_Coverage–MS_by_Cluster_Algo.png
│   │       └── Mean_Coverage–MS_by_Embedding_Model.png
│   ├── run_1/
│   │   ├── cluster_coverage_summary_run_1.csv
│   │   ├── mutation_metrics.csv
│   │   ├── correlations_table.csv
│   │   ├── selected_mutant_indices.txt
│   │   └── ...
│   ├── run_2/
│   ├── ...
│   └── run_10/
```

Each **SUT (e.g., `CALC`, `BASIC`, `RHINO`)** has its own directory.  
Results are produced from **10 independent runs** per SUT.

---

### Where to Start (Recommended)

For result verification, focus on:
``` <SUT_NAME>/correlations_summary/ ```

This folder contains **aggregated results across all 10 runs**, which are the
values reported in the paper.

---

### Key Files and How to Read Them

#### 1. `final_correlation_summary.csv`

**Purpose:**  
Shows the relationship between **Cluster Coverage (CC)** and **Mutation Score (MS)**
for each embedding model.

**Columns:**
- `Configuration`: embedding model and clustering algorithm pair
- `Mean_Coverage–MS`: mean Spearman CC-MS correlation aggregated across runs
- `Wilcoxon_p`: Wilcoxon signed-rank p-value against a zero-correlation baseline

**How to interpret:**
- Higher positive `Mean_Coverage–MS` values indicate that CC is a better proxy for mutation effectiveness.
- Lower `Wilcoxon_p` values indicate stronger statistical evidence that the observed correlation is above the zero-correlation baseline.

**Example (CALC):**
- OpenAI shows a strong positive CC–MS correlation with a low p-value
- Indicates CC is meaningful when computed using this embedding model

---

#### 2. `jaccard_summary_by_model.csv`

**Purpose:**  
Measures how well **CC-based rankings** identify **top mutation-performing generators**.

**Metric:**
- `Jaccard@K` compares:
  - Top-K generators by mutation score
  - Top-K generators by cluster coverage

**How to interpret:**
- Values closer to `1.0` → stronger overlap

**Example (CALC):**
- OpenAI at `Top-3` has a Jaccard value of `0.46`
- Indicates substantial agreement between CC-based and MS-based top generators

---

#### 3. `cluster_coverage_summary_all_runs.csv`

**Purpose:**  
Shows **mean Cluster Coverage values** for each generator configuration,
aggregated across all runs.

**How to use this file:**
1. Identify the **best-performing embedding model** (from correlation/Jaccard files)
2. Filter CC values for that embedding
3. Compare generators to select the one with the **highest CC**

**Example (CALC):**
- OpenAI selected as the representative embedding
- Among 8 generators, `Fuzz_equal` achieves the highest mean CC (≈ 0.32)

---

### Run-Level Results (`run_1/` … `run_10/`)

Each `run_i/` folder contains **raw per-run data**, including:
- CC values per generator
- Mutation scores
- Correlation tables
- Selected mutant indices

These files support:
- Reproducibility
- Variance and stability analysis
However, **they are not required** to validate the paper’s main results.

---

### Summary

- Use `correlations_summary/` for **paper-level verification**
- Use `run_i/` folders for **per-run inspection**
- Generator selection follows:
  1. Identify stable embedding model (correlation + Jaccard)
  2. Select generator with highest aggregated CC for that model

## Understanding Input Prioritization Results (Phase 2)

This section explains how to inspect and interpret the results produced during
the **Input Prioritization phase** of the study. These results correspond to
RQ3 (effectiveness) and RQ4 (stability) in the paper.

All results are **fully processed** and can be inspected without re-running
any experiments.

---

### Folder Structure
```tree
data/Input_Prioritization_Results/
├── AUC_AGGREGATED/                # Aggregated AUC (Area Under Curve) results
│   ├── GLOBAL_AUC_SUMMARY.csv    # Overall summary across all experiments
│   ├── CALC_AUC.csv              # AUC results for CALC experiments
│   ├── BASIC_AUC.csv             # AUC results for BASIC experiments
│   └── ...                       # Other aggregated metrics
│
├── CALC/                         # CALC-specific experiment results
│   ├── OPENAI/                   # OpenAI model results
│   ├── rq3_summary/              # Research Question 3 findings
│   ├── rq4_summary/              # Research Question 4 findings
│   └── tool_selection/           # Tool selection methodology results
│
├── BASIC/                        # BASIC-specific experiment results
│   └── ...                       # (structure similar to CALC/)

```


---

## AUC_AGGREGATED — Overall Effectiveness (RQ3)

The `AUC_AGGREGATED/` directory contains **summary results** that compare
SpreadEx with random selection across all SUTs.

### Key Files

- **`GLOBAL_AUC_SUMMARY.csv`**
  - Aggregated results across **all SUTs and runs**
  - Reports:
    - Mean AUC for SpreadEx and Random
    - Wilcoxon signed-rank test results  
      (10 runs × 6 SUTs = 60 paired experiments)
    - Cliff’s Delta (effect size)

  This file directly supports the **global AUC results** reported in the paper.

- **`<SUT>_AUC.csv` (e.g., `CALC_AUC.csv`)**
  - Mean AUC values for a **single SUT**
  - Aggregated across the 10 independent runs
  - Used to generate per-SUT comparisons and figures

### Interpretation

A higher AUC indicates **better cumulative fault detection** over budgets
ranging from **5 to 100 inputs (step = 5)**.

---

## Per-SUT Results (Detailed Analysis)

Each SUT folder (e.g., `CALC/`, `BASIC/`) contains detailed summaries for RQ3
and RQ4.

---

### rq3_summary — Effectiveness at Specific Budgets (RQ3)

Example:

This file reports **early-budget effectiveness metrics**, including:

- **MS@K** — Mutation Score at budget K (K ∈ {5, 10, 20})
- **T2K** — Tests-to-Kill (average number of tests required to kill a mutant)

These metrics are **averaged across 10 independent runs** for the given SUT.

Use this file to:
- Compare early fault detection between SpreadEx and Random
- Validate MS@K and T2K values reported in tables and figures

---

### rq4_summary — Stability and Variability (RQ4)

Example:

This file reports metrics related to **run-to-run stability**, including:

- **STD@K** — Standard deviation of MS@K across runs
- **PKHM@K** — Probability of Killing Half Mutants at budget K

These values quantify the **instability of random selection** and the
deterministic behavior of SpreadEx.

Use this file to:
- Inspect variance across runs
- Validate claims about reproducibility and reliability

---

### OPENAI / run_x

The `OPENAI/` and `run_x/` directories document:

- The **fixed embedding model** used for prioritization (OpenAI)
- Each **independent experiment result of that SUT**
---

## How to Use These Results

- To **verify paper claims** → start with `AUC_AGGREGATED/`
- To **inspect SUT-specific behavior** → open the corresponding SUT folder
- To **analyze early-budget performance** → check `rq3_summary`
- To **analyze stability and variance** → check `rq4_summary`

No scripts or execution are required to validate the results.

---

If you wish to **reproduce the experiments from scratch**, follow the
step-by-step instructions provided in:

