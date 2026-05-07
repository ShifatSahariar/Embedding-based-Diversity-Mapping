[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 2 — Embedding Generation](step02_embedding_generation.md) | [Next: Step 4 — Cluster Coverage Computation](step04_cluster_coverage.md)

---

## 🧬 Step 3 — Mutation Analysis

**Script:** `Mutation_Analysis.py`

### Purpose
Prepares original-program baselines, exports mutants, selects a controlled mutant subset, and then runs the selected mutants against generated test inputs. This step is used to compute mutation-killing profiles and effectiveness metrics with the artifact's own input-based killing procedure.

### Functionality
- Uses **JaCoCo** only when original coverage XML/profile artifacts are requested.
- Uses **PIT only to export mutant bytecode** for the configured target classes.
- Aggregates PIT-exported mutants into a subject-level mutant pool.
- Randomly selects a fixed mutant budget per run.
- Executes the selected mutants with the artifact's own runner against generated inputs.
- Compares each mutant output with the original-program baseline to decide whether the generated input kills the mutant.

### What This Step Assumes

`Mutation_Analysis.py` assumes that test inputs already exist under:

```tree
GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/<SUT>/input_pool_by_run_*/
```

It can work in two modes:

- **Reuse existing mutants:** if the artifact already contains generated/aggregated/selected mutants.
- **Regenerate mutants:** if PIT jars and compiled SUT classes are available locally.

The current artifact layout expects PIT-generated mutants at:

```tree
MUT_KILLING_PROFILE/pit_mut_tool/<SUT>/mutants_collection/export/.../mutants/
```

Aggregated mutants are stored at:

```tree
MUT_KILLING_PROFILE/<SUT>/aggregated_mutants/
```

Selected mutants are stored per run at:

```tree
MUT_KILLING_PROFILE/<SUT>/selected_mutants/selected_mutants_run_<N>/
```

Final mutation-killing profiles are written to:

```tree
MUT_KILLING_PROFILE/<SUT>/main_mut_killing_profiles/mutants_profile_run_<N>/
```

### Recommended Order

Run mutation analysis in phases. Do not enable all flags on the first attempt.

Important: PIT's command-line exporter may still perform its own internal test-coverage discovery during `--generate_mutants true`. This is not the artifact's coverage phase and is not the mutation-killing result reported by this artifact. The reported mutation-killing profiles are produced later by `--running_mutants true`, where selected exported mutants are executed against the generated input pools and compared with the original-program outputs.

#### 3.1 Original-Program Baseline / Optional Coverage Smoke Test

Run this before mutant execution. It executes the generated inputs on the **original, unmutated SUT** and stores the reference behavior for each input: return code, normalized exception, stderr, and program output.

Mutation execution later compares each mutant's behavior against these original results. Therefore, this step is required before `--running_mutants true` unless the corresponding `COVERAGE_REPORTS/<SUT>/coverage_input_pool_by_run_<N>/` folders already exist.

For a smoke test, run only one input run:

```bash
python Mutation_Analysis.py --subject KARATEJS --coverage_only true --runs 1
```

Expected output folder:

```tree
COVERAGE_REPORTS/KARATEJS/coverage_input_pool_by_run_1/
```

By default, this command keeps JaCoCo XML/profile generation and return/exception plotting disabled. It only stores the original-program baseline needed for the artifact's own mutant-killing comparison, which is faster and is usually enough before running selected mutants.

The default smoke-test command also runs sequentially (`--parallel false`) to avoid multiprocessing issues on restricted machines. For full local runs, you may enable:

```bash
python Mutation_Analysis.py --subject KARATEJS --coverage_only true --parallel true
```

If you want the optional return-code and exception plots after baseline execution, enable:

```bash
python Mutation_Analysis.py --subject KARATEJS --coverage_only true --analyze_results true --runs 1
```

If you also need JaCoCo coverage XML/profile artifacts for additional inspection, enable:

```bash
python Mutation_Analysis.py --subject KARATEJS --coverage_only true --generate_coverage true --runs 1
```

Use `--coverage_only false` or omit `--coverage_only` when you are not preparing original baseline outputs. For mutant generation, mutant aggregation, and mutant selection, coverage mode is not needed.

#### 3.2 Mutant Generation With PIT

Use this only if the artifact does not already include PIT-exported mutants, or if you intentionally want to regenerate them. PIT is not used here to decide which generated inputs kill mutants; it is used only to export mutant bytecode for the selected target classes. If PIT prints messages about gathering coverage or killed/survived mutants, treat them as internal PIT diagnostics required by its exporter.

Before running, ensure:

- PIT jars are in `MUT_KILLING_PROFILE/pit_mut_tool/`
- For KarateJS, the PIT directory includes `pitest-junit5-plugin`, `junit-jupiter-engine`, and `junit-platform-launcher`
- The SUT has already been compiled
- The configured class/source/test paths in `Helper_Functions/configs/mutation_configs.py` exist

Fast PIT smoke test with one class:

```bash
python Mutation_Analysis.py \
  --subject KARATEJS \
  --mutation_only true \
  --generate_mutants true \
  --aggregate_mutants false \
  --selecting_mutants false \
  --running_mutants false \
  --target_classes io.karatelabs.js.CoreContext
```

Expected sign that setup is correct: PIT exports mutant files under the configured `mutants_collection` directory. If PIT says `could not run any tests`, check that the JUnit 5 plugin/runtime jars are in `MUT_KILLING_PROFILE/pit_mut_tool/` and that `SUT/karate-v2/karate-js/target/test-classes` exists.

This smoke test writes to `MUT_KILLING_PROFILE/pit_mut_tool/KARATEJS/mutants_collection_smoke/` so it does not overwrite the full mutant collection used by the reproduction pipeline.

Full configured mutant generation:

```bash
python Mutation_Analysis.py \
  --subject KARATEJS \
  --mutation_only true \
  --generate_mutants true \
  --aggregate_mutants true \
  --selecting_mutants false \
  --running_mutants false
```

This exports raw PIT mutants for the configured target classes and aggregates them into:

```tree
MUT_KILLING_PROFILE/KARATEJS/aggregated_mutants/
```

#### 3.3 Select Mutants Per Run

If aggregated mutants already exist, select the mutant subset for each run:

```bash
python Mutation_Analysis.py \
  --subject KARATEJS \
  --mutation_only true \
  --generate_mutants false \
  --aggregate_mutants false \
  --selecting_mutants true \
  --running_mutants false \
  --budget 100 \
  --runs 1
```

For a smoke test, use a smaller budget:

```bash
python Mutation_Analysis.py --subject KARATEJS --mutation_only true --selecting_mutants true --running_mutants false --budget 5 --runs 1
```

#### 3.4 Run Selected Mutants

Only run this after original-program baseline results and selected mutants exist. This is the phase that computes the artifact's mutation-killing profiles.

Smoke test:

```bash
python Mutation_Analysis.py \
  --subject KARATEJS \
  --mutation_only true \
  --generate_mutants false \
  --aggregate_mutants false \
  --selecting_mutants false \
  --running_mutants true \
  --budget 5 \
  --runs 1 \
  --input_start 1 \
  --input_end 3 \
  --chunk_size 3
```

Full reproduction uses the paper settings:

```bash
python Mutation_Analysis.py \
  --subject KARATEJS \
  --mutation_only true \
  --selecting_mutants true \
  --running_mutants true \
  --budget 100
```

### Flag Meaning

| Flag | Meaning |
|------|---------|
| `--coverage_only true` | Run the original SUT on generated inputs and save baseline outputs |
| `--generate_coverage true` | With `--coverage_only true`, also collect JaCoCo XML/profile artifacts |
| `--parallel true` | Run baseline/coverage input execution in parallel; keep false for smoke tests |
| `--analyze_results true` | Create optional return-code/exception distribution plots |
| `--mutation_only true` | Enter mutation workflow |
| `--generate_mutants true` | Export raw mutants with PIT; PIT's own kill/survive output is ignored |
| `--aggregate_mutants true` | Rebuild `aggregated_mutants/` from PIT output |
| `--selecting_mutants true` | Select the per-run mutant subset |
| `--running_mutants true` | Execute selected mutants against generated inputs and compare with original outputs |
| `--budget N` | Number of mutants to select per run |
| `--runs N` | Limit to first N runs for smoke testing |
| `--input_start N`, `--input_end N` | Limit the input range during mutation execution |

⚠️ **Note:** Mutation generation and mutant execution are computationally expensive. Start with coverage, then selection, then a tiny mutation-execution smoke test before running the full experiment.
