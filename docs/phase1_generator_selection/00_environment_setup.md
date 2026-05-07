[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Next: Step 1 — Test Input Generation](step01_test_input_generation.md)

---

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

---

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
