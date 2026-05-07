# 🧪 Test Input Generation and Evaluation Pipeline

This section describes how to reproduce the **generator selection phase** of the pipeline from scratch.  
The full workflow covers **grammar-based test input generation, embedding, clustering, mutation analysis, and correlation evaluation** across multiple generators and embedding models.

⚠️ **Note on Cost and Runtime**  
Mutation analysis is computationally expensive. For large SUTs (e.g., GraalJS), generating mutation profiles for 8,000 inputs (1,000 inputs × 8 generators) may take **up to 1.5 days** per experiment.  
For exploratory runs, we recommend using fewer inputs or fewer generators.

---
## 🔬 Experimental Setup (per SUT)

According to the paper, each SUT is evaluated using **10 independent experiments**.  
Each experiment uses the following configuration:

- **8 input generator configurations**
- **1,000 inputs per generator** (8,000 total inputs)
- **5 embedding models**  
  *(For faster reproduction, we recommend starting with OpenAI embeddings only)*
- **100 randomly selected mutants** per experiment
---

## Recommended Execution Mode

For first-time reproduction, we recommend running the scripts from an IDE such as PyCharm or VS Code. The main scripts expose their configuration near the top of the file, so an IDE makes it easier to inspect paths, edit the subject program, reduce the number of inputs for a quick check, and step through errors if an external tool is missing.

All scripts can also be executed from the command line; the IDE recommendation is mainly for convenience during artifact review.

The full pipeline covers **grammar-based test input generation, clustering, mutation analysis, and correlation evaluation** across multiple embedding models and test generators.  
The workflow is designed to evaluate **which test input generator** produces the most diverse and fault-revealing test cases for a given subject program.

---

## 🧭 Pipeline Overview

Each experiment proceeds through the following phases:

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `Generation_Test_Inputs.py` | Generate test inputs using multiple generators |
| 2 | `Generation_Embeddings.py` | Compute embeddings for all generated inputs |
| 3 | `Mutation_Analysis.py` | Perform coverage and mutation analysis |
| 4 | `Cluster_Coverage.py` | Compute cluster coverage per generator and embedding |
| 5 | `Mutation_Scores_Generators.py` | Compute mutation metrics (MS, KI, SKI) |
| 6 | `Correlations_MS_CC.py` | Compute CC–MS correlation statistics |
| 7 | `Jaccard_Similarity_MS_CC.py` | Compute Top-K overlap between CC and MS rankings |
| 8 | `Analysis_Reports_Plots/` | Generate plots for correlations and overlaps |

---
---
## 🧩 Detailed Workflow

## Environment and Tool Setup

Before running the full pipeline from scratch, install the Python dependencies and confirm that the Java mutation/coverage tools are available at the paths used by the scripts.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
java -version
```

Required external tools:

- Python >= 3.10
- Java >= 17
- PIT command-line distribution jars
- JaCoCo agent/CLI jars
- Optional generator CLIs: Fandango and ISLa, if those generators are enabled
- Optional API key: `OPENAI_API_KEY`, if OpenAI input generation or OpenAI embeddings are enabled

### JaCoCo

The coverage scripts expect these files:

```tree
COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/
├── jacocoagent.jar
└── jacococli.jar
```

These files are included in the artifact. If you reinstall JaCoCo, keep these filenames or update the constants in `COVERAGE_REPORTS/Coverage_Reports.py` and `Helper_Functions/Coverage_Helping_Functions.py`.

### PIT

The mutation-generation scripts expect PIT jars under:

```tree
MUT_KILLING_PROFILE/pit_mut_tool/
```

The code passes `MUT_KILLING_PROFILE/pit_mut_tool/*` to Java as the PIT classpath in `Helper_Functions/Mutation_Helping_Functions.py`. Create the directory if it does not exist and place the PIT command-line jar, PIT runtime jars, the PIT JUnit 5 plugin, and the JUnit runtime jars there.

If Maven is available, use the included `pitest-runtime-pom.xml` to download the required PIT and JUnit jars:

```bash
mvn -Dmaven.repo.local=.m2/repository \
  -f pitest-runtime-pom.xml \
  org.apache.maven.plugins:maven-dependency-plugin:3.7.0:copy-dependencies \
  -DoutputDirectory=MUT_KILLING_PROFILE/pit_mut_tool \
  -DincludeScope=runtime
```

After copying the jars, the temporary `.m2/` cache can be deleted or excluded from the archived artifact.

Example:

```tree
MUT_KILLING_PROFILE/
└── pit_mut_tool/
    ├── pitest-command-line-<version>.jar
    ├── pitest-<version>.jar
    ├── pitest-entry-<version>.jar
    ├── pitest-junit5-plugin-<version>.jar
    ├── junit-jupiter-engine-<version>.jar
    ├── junit-platform-launcher-<version>.jar
    └── ...
```

PIT command-line setup is documented at: https://pitest.org/quickstart/commandline

### Optional generator CLIs

If you enable Fandango or ISLa generators, ensure their executables are on `PATH`:

```bash
which fandango
which isla
```

If either command is missing, disable that generator for a smoke test or install the corresponding CLI before running the full generator-selection experiment.

### OpenAI

The `openai` Python package is installed through `requirements.txt`. If you run OpenAI-based input generation or OpenAI embeddings, also configure an API key before starting the script:

```bash
export OPENAI_API_KEY="your-api-key"
```

If no OpenAI key is available, use a local embedding model such as `unixcoder` for the smoke test and disable the OpenAI generator/model until the key is configured.

## Quick Smoke Test Before Full Reproduction

Before launching the full paper-scale experiment, run a small smoke test to check that the local environment, paths, and selected tools work correctly.

Recommended smoke-test settings:

- Use one small SUT first, such as `CALC` or `basic`.
- Generate only 2-3 inputs per generator.
- Run only 1 independent run.
- Start with one generator family, for example `fuzzingbook`, because it has the fewest external tool requirements.
- Generate embeddings with one model only, for example `unixcoder` for a local model or `openai` if `OPENAI_API_KEY` is configured.
- Run coverage before mutation analysis.
- Run mutation generation/execution only after the previous steps produce the expected files.
- After each step, inspect the output folder before continuing. For example, confirm that generated inputs exist before embeddings, embeddings exist before clustering, and mutation profiles exist before computing mutation scores.

Example CLI smoke test for input generation:

```bash
python Generation_Test_Inputs.py --subject CALC --tools fuzzingbook --num_inputs 3 --runs 1
```

Expected result:

```tree
GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/CALC/input_pool_by_run_1/
```

This folder should contain a small number of generated `.txt` inputs. Once this works, continue to embeddings, coverage, cluster coverage, mutation-score computation, and correlation analysis. For the full experiment reported in the paper, restore the settings to 1,000 inputs per generator, all selected generators, 10 independent runs, and the full embedding-model set.

### 1️⃣ Test Input Generation
```markdown
Run `Generation_Test_Inputs.py` to generate test inputs for the target SUT using all configured generators.

Each generator produces the same number of inputs to ensure a fair comparison.
For an IDE smoke test, start with 2-3 inputs per tool and 1 run. For full paper-scale reproduction, use 1,000 inputs per tool and 10 runs.

With an IDE, you can edit the configuration near the top of `Generation_Test_Inputs.py`:
pipeline_config = {
    'subject_program': 'karatejs',       # Options: CALC | rhino | basic | karatejs | nashorn | graaljs
    'generate_inputs': True,             # keep true
    'clean_previous_data': False,        # set true if you want to clean previously generated inputs
    'num_inputs_per_tool': 3,            # smoke test: 2-3; full experiment: 1000
    'num_random_runs': 1,                # smoke test: 1; full experiment: 10
```
### Output
Each run produces:
```tree
GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/<subject>/input_pool_by_run_1/
├── fan_con_1.txt
├── fan_no_con_1.txt
├── isla_con_1.txt
├── isla_no_con_1.txt
├── openai_gram_1.txt
└── openai_no_gram_1.txt
```

---
---
## 🧠 Step 2 — Embedding Generation 

**Script:** `Generation_Embeddings.py`

### Purpose
This step generates **vector embeddings** for each generated test input using one or more
**code embedding models**. These embeddings are later clustered to construct diversity maps
used for generator comparison and input prioritization.

### Supported Embedding Models
- `openai`
- `unixcoder`
- `codestral`
- `graph_codebert`
- `qwen3`

> In the paper, all five models were evaluated.  
> For lightweight reproduction, run only one model and one run first.
---
---

### Model Requirements

Different embedding backends require different setup:

| Model | Requires | Notes |
|------|----------|-------|
| `unixcoder` | `torch`, `transformers` | Local model; easiest option after `pip install -r requirements.txt` |
| `graph_codebert` | `torch`, `transformers` | Local model |
| `qwen3` | `torch`, `transformers` | Local model |
| `openai` | `openai`, `OPENAI_API_KEY` | API-based; fails with 401 if the key is missing |
| `codestral` | `mistralai`, `MISTRAL_API_KEY` | API-based; remove from smoke tests unless configured |

If you see errors such as `No module named 'torch'`, `No module named 'mistralai'`, or `No module named 'openai'`, install the Python dependencies:

```bash
pip install -r requirements.txt
```

Local Hugging Face models such as `unixcoder`, `graph_codebert`, and `qwen3` download model weights the first time they are used. Ensure the machine has internet access for the first run, or pre-populate the Hugging Face cache. Setting `HF_TOKEN` is optional but can help avoid rate limits:

```bash
export HF_TOKEN="your-huggingface-token"
```

If you see an OpenAI 401 error, configure the API key or run without the OpenAI model:

```bash
export OPENAI_API_KEY="your-api-key"
```

For Codestral, configure:

```bash
export MISTRAL_API_KEY="your-api-key"
```

### Smoke-Test Command

After generating a small input pool, run only one embedding model on one run:

```bash
python Generation_Embeddings.py --subject CALC --models unixcoder --runs 1
```

If you want to test OpenAI embeddings instead:

```bash
export OPENAI_API_KEY="your-api-key"
python Generation_Embeddings.py --subject CALC --models openai --runs 1
```

Avoid running `openai,codestral,unixcoder` together until all dependencies and API keys are configured. Otherwise, the script may spend time retrying API calls or loading multiple large models.

### Example Configuration (Python API)

Below is an example showing how to generate embeddings for a selected subject program using a subset of embedding models:

```markdown
subject_program = "CALC"  # CALC | BASIC | RHINO | KARATEJS

# Available models:
# ["openai", "codestral", "graph_codebert", "unixcoder", "qwen3"]
models_to_run = ["unixcoder"]  # smoke test; use all five models for full reproduction

generate_embeddings_for_all_runs(
    subject_program=subject_program,
    vector_models=models_to_run,
    base_input_dir=f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{subject_program.upper()}",
    base_output_dir=f"EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/{subject_program.upper()}"
)
### Output
--- 
```tree
EMBEDDINGS/
└── VECTORS_COLLECTION/
    └── INPUT_SELECTOR/
        └── <SUT>/
            ├── run_1/
            ├── run_2/
            └── ...

```


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


## 📊 Step 4 — Cluster Coverage Computation

**Script:** `Cluster_Coverage.py`

### Purpose
Computes **cluster coverage metrics** for each generator and model across runs.

Cluster coverage reflects how well a generator’s inputs cover the **clusters** identified in embedding space — acting as a diversity measure.
only you can specify the sut name.
### Output
Each run produces:
```
cluster_coverage_summary_<model>.csv
```
with columns such as:
```

where:
- **Configuration**: input generator setup
- **Cluster_Algo**: clustering algorithm used
- **K_eff**: effective number of clusters
- Remaining columns report the **cluster coverage values** achieved by each generator configuration

These outputs are later used to:
- compare generators based on diversity,
- compute correlations with mutation-based effectiveness,
- and guide generator selection.

```

---

## 🧬 Step 5 — Mutation Score Computation

**Script:** `Mutation_Scores_Generators.py`
only you can specify the sut name.
### Purpose
Computes mutation-based effectiveness metrics:
- **MS** (Mutation Score)
- **KI** (Kill Index)
- **SKI** (Strong Kill Index)

### Output
Each run produces:
```
mutation_metrics.csv
```
with per-generator metrics.

---

## 📈 Step 6 — Correlation Analysis (MS vs CC)

**Script:** `Correlations_MS_CC.py`
only you can specify the sut name.
### Purpose
Computes **Spearman correlation** between:
- Cluster coverage (CC)
- Mutation score (MS)

across multiple runs and embedding models.

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
correlations_summary/final_correlation_summary.csv
```

---

## 🥉 Step 7 — Jaccard Similarity (Top-K Agreement)

**Script:** `Jaccard_Similarity_MS_CC.py`
only you can specify the sut name.
### Purpose
Evaluates **ranking consistency** between MS and CC across generators using **Top-K Jaccard similarity**.

### Configuration
Specify:
- `K_list = [2, 3]` (or other)
- Runs across all embedding models and generators

### Output
```
jaccard_summary_topK.csv
```
with similarity scores for each model and run.

---

## 🧩 Adding a New Subject Program

When introducing a new subject program (SUT):
1. **Prepare grammar** under `GRAMMARS/` with Fandango or probabilistic format.  
   - Ensure type consistency and define constraints (`LET`, `FOR`, etc.).
2. **Configure generation** in `Generation_Test_Inputs.py`  
   - Add program name to supported subjects.
3. **Adjust mutation class filters** in `Mutation_Analysis.py`
4. **Run the pipeline sequentially** following the steps above.

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
│       ├── average_correlation.csv
│       └── final_correlation_summary.csv
└── JACCARD/
    └── jaccard_summary_topK.csv
```

---

## 🧠 Notes for Evaluation

- All random processes (generation, selection, clustering) are **seeded** for reproducibility.  
- Each run folder (e.g., `run_1`, `run_2`, `run_3`) represents an **independent experimental repetition**.
- For statistical consistency, **Wilcoxon test** compares the average correlation distribution against zero baseline (null hypothesis of no correlation).

---
