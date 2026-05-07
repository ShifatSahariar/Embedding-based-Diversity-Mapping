## 🔍 Phase 2 — Input Prioritization with SpreadEx

In Phase 2, we prioritize test inputs using **SpreadEx**, after fixing:
- the **embedding model** (e.g., OpenAI), and
- the **input generator** selected per SUT based on Phase 1 results.

Both choices are determined automatically from Phase 1 outputs (Cluster Coverage strength per SUT). No manual generator selection is required at this stage.

---

### ▶️ Step 1 — Run Input Prioritization

**Script:** `PRIORATIZATION/inputs_selection_main.py`

This script performs budget-aware input prioritization using SpreadEx.

#### Key Configuration Parameters

```python
subject_program = "BASIC".upper()

# Selected embedding model (fixed from Phase 1)
# Options: CODESTRAL, CODEBERT, UNIXCODER, OpenAI
embedding_model = "OpenAI"

# Input selection budgets
budgets = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
           55, 60, 65, 70, 75, 80, 85, 90, 95, 100]

# Number of independent runs (auto-detected if None)
n_runs = None

# Parallelism (set to 1 for stability)
n_jobs = 1

# Maximum number of inputs per run
limit = 1000
```

At minimum, you only need to specify `subject_program`.
All other parameters are optional unless you want to experiment with different settings.

---

## ▶️ Step 2 — Aggregate AUC Results (RQ3, Global)

To reproduce the **aggregate AUC analysis across all SUTs**, run the following script:

**Script:**  
`PRIORATIZATION/research_questions/auc_rq_util.py`

No parameters are required.  
The script automatically aggregates results from all subjects.

### 📁 Output Location


PRIORATIZATION/ALL_SUT_RESULTS/AUC_AGGREGATED/

This folder contains:
- Global AUC comparisons between **SpreadEx** and **Random**
- Wilcoxon signed-rank test results
- Cliff’s Delta effect sizes

---

## ▶️ Step 3 — Reproduce RQ3 (Early Fault Detection)

To reproduce **RQ3** results (early fault detection metrics such as MS@K and T2K) for a specific SUT, use:

**Script:**  
`PRIORATIZATION/research_questions/early_fault_detection_util.py`

You can either:
- Run the script directly, or
- Call the following function from anywhere:

```markdown
aggregate_rq3_for_sut("SUT_NAME")
```

📁 Output location:

ALL_SUT_RESULTS/{SUT_NAME}/rq3_summary/RQ3_GLOBAL_{SUT_NAME}.csv
---
This file reports:
 - Mutation Score at budget K (MS@K)
 - Tests-to-Kill (T2K)
 - Budget-specific prioritization effectiveness
---
## ▶️ Step 4 — Reproduce RQ4 (Stability Analysis)

To reproduce **RQ4** (stability and variability of random vs. SpreadEx), use:

**Script:** : 
`PRIORATIZATION/research_questions/stability_compare_util.py`

Run directly or call:
```markdown
aggregate_rq4_for_sut("SUT_NAME")
```

📁 Output location:

ALL_SUT_RESULTS/{SUT_NAME}/rq4_summary/RQ4_GLOBAL_{SUT_NAME}.csv
---
This file reports:
 - STD@K (variance across runs),
 - PKHM@K (Probability of Killing Half Mutants).
---