[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 4 — Cluster Coverage Computation](step04_cluster_coverage.md) | [Next: Step 6 — Correlation Analysis](step06_correlation_analysis.md)

---

## 🧬 Step 5 — Mutation Score Computation

**Script:** `Mutation_Scores_Generators.py`

### Purpose
Computes mutation-based effectiveness metrics:
- **MS** (Mutation Score)
- **KI** (Kill Index)
- **SKI** (Strong Kill Index)

This step reads the mutation killing profiles from Step 3 and summarizes them per generator. It writes the mutation metrics into the same per-run result folders created by Step 4, so the correlation step can compare Cluster Coverage (CC) and Mutation Score (MS) run by run.

### Before running
Confirm that Step 3 has produced mutation killing profiles under:
```
MUT_KILLING_PROFILE/<SUT>/main_mut_killing_profiles/mutants_profile_run_<N>/
```

For KarateJS, a run folder should look like:
```
MUT_KILLING_PROFILE/KARATEJS/main_mut_killing_profiles/mutants_profile_run_1/
├── fan_con_1.txt
├── fan_con_2.txt
├── ...
├── isla_no_con_3.txt
```

Each `.txt` file is one input's binary mutation-killing profile:
```
0 1 0 0 1 ...
```

Before computing mutation scores, quickly check that profiles are not all zero:
```bash
find MUT_KILLING_PROFILE/KARATEJS/main_mut_killing_profiles/mutants_profile_run_1 \
  -type f -name "*.txt" | sort | head -5 | \
  xargs -I{} awk '{s=0; for(i=1;i<=NF;i++) s+=int($i); print FILENAME, "len=" NF, "sum=" s}' {}
```

If every `sum` is `0`, rerun Step 3 mutation execution after regenerating the original baseline outputs.

### Recommended smoke test from terminal
Run only the first mutation-profile run:
```bash
python Mutation_Scores_Generators.py --subject karatejs --runs 1 --parallel false
```

With the PyCharm virtual environment used in this artifact:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Mutation_Scores_Generators.py \
  --subject karatejs \
  --runs 1 \
  --parallel false
```

Expected output:
```
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/mutation_metrics.csv
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/selected_mutant_indices.txt
FUZZ_TOOL_SELECTION/result/KARATEJS/run_1/global_report/global_filter_report.txt
```

Open `mutation_metrics.csv` and confirm that it contains one row per generator:
```
Tool,Tests,Mutants_Selected,MS,KI,SKI
fan_con,...
fan_no_con,...
...
```

Also inspect `global_filter_report.txt`. It explains how many mutants were removed as never killed, always killed, duplicate, or subsumed.

### Running from an IDE such as PyCharm
For a smoke test, open `Mutation_Scores_Generators.py` and use these script parameters in the Run Configuration:
```bash
--subject karatejs --runs 1 --parallel false
```

For the full Step 5 run:
```bash
--subject karatejs --parallel false
```

Recommended for first-time artifact checking: keep `--parallel false` so errors are printed in run order and are easier to debug. Once the sequential run works, `--parallel true` can be used to process runs concurrently.

### Full run from terminal
After the smoke test succeeds:
```bash
python Mutation_Scores_Generators.py --subject karatejs --parallel false
```

or with the artifact virtual environment:
```bash
/Users/usi/PyCharmMiscProject/.venv/bin/python Mutation_Scores_Generators.py \
  --subject karatejs \
  --parallel false
```

### Output
Each run produces:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/mutation_metrics.csv
```
with per-generator metrics.

It also writes:
```
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/selected_mutant_indices.txt
FUZZ_TOOL_SELECTION/result/<SUT>/run_<N>/global_report/global_filter_report.txt
```

Meaning of the main columns:
- **Tool**: generator configuration, such as `fan_con` or `isla_no_con`
- **Tests**: number of inputs available for that generator in the run
- **Mutants_Selected**: number of informative mutants retained after global filtering
- **MS**: fraction of retained mutants killed by at least one input from the generator
- **KI**: number of inputs that kill at least one retained mutant
- **SKI**: average number of retained mutants killed by the KI-positive inputs

These files are required by Step 6.

---
