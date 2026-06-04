# 🧪 Phase 1: Generator Selection

This page is the entry point for reproducing the **generator selection phase** of the artifact. The detailed instructions are split into smaller step-specific guides so reviewers can run, debug, or inspect one part of the pipeline at a time.

The Phase 1 workflow covers grammar-based test input generation, embedding generation, clustering, mutation analysis, mutation-score computation, and agreement analysis across multiple generators and embedding models.

⚠️ **Note on Cost and Runtime**  
Mutation analysis is computationally expensive. For large SUTs (e.g., GraalJS), generating mutation profiles for 8,000 inputs (1,000 inputs × 8 generators) may take **up to 1.5 days** per experiment. For exploratory runs, start with fewer inputs, fewer generators, and one embedding model.

---

## 🔬 Experimental Setup (per SUT)

According to the paper, each SUT is evaluated using **10 independent experiments**. Each experiment uses:

- **8 input generator configurations**
- **1,000 inputs per generator** (8,000 total inputs)
- **5 embedding models**
  *(For faster reproduction, we recommend starting with OpenAI embeddings only if `OPENAI_API_KEY` is configured, or `unixcoder` for local-only reproduction.)*
- **100 randomly selected mutants** per experiment

---

## Recommended Execution Mode

For first-time reproduction, we recommend running the scripts from an IDE such as PyCharm or VS Code. The main scripts expose their configuration near the top of the file, so an IDE makes it easier to inspect paths, edit the subject program, reduce the number of inputs for a quick check, and step through errors if an external tool is missing.

All scripts can also be executed from the command line; the IDE recommendation is mainly for convenience during artifact review.

---

## 🧭 Step-by-Step Guides

Start with the environment setup guide, then run the nine Phase 1 steps in order.

| Step | Guide | Script / Area | Purpose |
|------|-------|---------------|---------|
| Setup | [Environment and Tool Setup](phase1_generator_selection/00_environment_setup.md) | Python, Java, PIT, JaCoCo | Install dependencies and run a small smoke test |
| 1 | [Test Input Generation](phase1_generator_selection/step01_test_input_generation.md) | `Generation_Test_Inputs.py` | Generate test inputs using multiple generators |
| 2 | [Embedding Generation](phase1_generator_selection/step02_embedding_generation.md) | `Generation_Embeddings.py` | Compute embeddings for generated inputs |
| 3 | [Mutation Analysis](phase1_generator_selection/step03_mutation_analysis.md) | `Mutation_Analysis.py` | Generate/select mutants and run mutation-killing profiles |
| 4 | [Cluster Coverage Computation](phase1_generator_selection/step04_cluster_coverage.md) | `Cluster_Coverage.py` | Compute cluster coverage per generator and embedding |
| 5 | [Mutation Score Computation](phase1_generator_selection/step05_mutation_score_computation.md) | `Mutation_Scores_Generators.py` | Compute MS, KI, and SKI per generator |
| 6 | [Correlation Analysis](phase1_generator_selection/step06_correlation_analysis.md) | `Correlations_MS_CC.py` | Compute CC-MS correlation statistics |
| 7 | [Jaccard Similarity](phase1_generator_selection/step07_jaccard_similarity.md) | `Jaccard_Similarity_MS_CC.py` | Compute Top-K agreement between CC and MS rankings |
| 8 | [Analysis Reports and Plots](phase1_generator_selection/step08_analysis_reports_plots.md) | `Analysis_Reports_Plots.py` | Generate run-level and summary plots |
| 9 | [Adding a New Subject Program](phase1_generator_selection/step09_adding_new_subject_program.md) | Configuration files | Add a new SUT to the Phase 1 workflow |

---

## Suggested Run Order

1. Read [Environment and Tool Setup](phase1_generator_selection/00_environment_setup.md).
2. Run [Step 1](phase1_generator_selection/step01_test_input_generation.md) with 2-3 inputs first.
3. Continue through Steps 2-8 using the smoke-test commands before full runs.
4. Use [Step 9](phase1_generator_selection/step09_adding_new_subject_program.md) only when adding a new SUT.
5. After each step, inspect the expected output folder before continuing.
6. After reports are generated, read [Data Format and Result Interpretation](data_format_and_interpretation.md).

---

## 🗳️ Output Folder Structure Summary

```
RESULTS/
├── GENERATED_INPUTS/
│   └── FUZZ_TOOL_SELECTOR/<subject>/input_pool_by_run_1/
├── EMBEDDINGS/
│   └── VECTORS_COLLECTION/INPUT_SELECTOR/<subject>/<model>/run_1/
├── MUTATION_ANALYSIS/
│   └── MUT_KILLING_PROFILE/<subject>/main_mut_killing_profiles/mutants_profile_run_1/
├── CLUSTER_COVERAGE/
│   └── cluster_coverage_summary_*.csv
├── CORRELATIONS/
│   └── correlations_summary/
│       ├── cluster_coverage_summary_all_runs.csv
│       └── final_correlation_summary.csv
├── JACCARD/
│   ├── run_<N>/jaccard_similarity/topK_<K>.csv
│   └── correlations_summary/jaccard_summary_by_model.csv
└── PLOTS/
    ├── run_<N>/analysis_plots/
    ├── correlations_summary/summary_plots/
    └── correlations_summary/jaccard_similarity_trends.png
```

---

## 🧠 Notes for Evaluation

- All random processes (generation, selection, clustering) are **seeded** for reproducibility.  
- Each run folder (e.g., `run_1`, `run_2`, `run_3`) represents an **independent experimental repetition**.
- For statistical consistency, **Wilcoxon test** compares the average correlation distribution against zero baseline (null hypothesis of no correlation).

---
