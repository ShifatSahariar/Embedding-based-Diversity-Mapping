[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 8 — Analysis Reports and Plots](step08_analysis_reports_plots.md)

---

## 🧩 Step 9 — Adding a New Subject Program

Use this checklist when introducing a new SUT. The safest path is to add one thing at a time and run a small smoke test after each stage.

### 1. Prepare the Grammar
Place the grammar files under:
```
GRAMMARS/<SUT>/
```

Check:
- grammar can generate valid inputs
- constraints are type-consistent
- generated files can be executed by the SUT
- a tiny pool, such as 2-3 inputs, works before full generation

### 2. Configure Test Input Generation
Update:
```
Generation_Test_Inputs.py
```

Add or verify:
- subject name
- grammar paths
- output folder naming
- generator configurations
- number of runs and number of inputs per generator

Smoke test:
```bash
python Generation_Test_Inputs.py
```

Expected output:
```
GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/<SUT>/input_pool_by_run_1/
```

### 3. Configure Embedding Generation
Update or verify:
```
Generation_Embeddings.py
EMBEDDINGS/VECTOR_MODELS/
```

Check:
- selected embedding models are installed
- required API keys are configured when using remote APIs
- vector files are produced for every generated input

Expected output:
```
EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/<SUT>/<MODEL>/run_1/
```

### 4. Configure Original Execution and Coverage
Update:
```
Helper_Functions/configs/coverage_configs.py
```

Check:
- `classes_root`
- `source_classes_directory`
- `main_class`
- `dependencies`
- `package_prefix`
- `input_execution_mode`

Use `input_execution_mode: file_arg` when the SUT expects the input file path as a command-line argument, such as KarateJS. Leave it unset for subjects that read input from stdin.

Smoke test original execution:
```bash
python Mutation_Analysis.py --subject <sut> --coverage_only true --runs 1 --parallel false --generate_coverage false
```

Expected output:
```
COVERAGE_REPORTS/<SUT>/coverage_input_pool_by_run_1/
```

Open a few `program_output.txt`, `return_code.txt`, and `stderr_full.txt` files to confirm the SUT is actually executing the input, not only printing a usage message.

### 5. Configure Mutation Generation and Execution
Update:
```
Helper_Functions/configs/mutation_configs.py
Mutation_Analysis.py
```

Check:
- target classes
- compiled classes path
- dependencies
- PIT jars and plugins if PIT is used for mutant export
- whether mutants should be generated, aggregated, selected, or only executed

Recommended smoke sequence:
```bash
python Mutation_Analysis.py --subject <sut> --mutation_only true --generate_mutants true --aggregate_mutants false --selecting_mutants false --running_mutants false --target_classes <one.class.Name>
```

Then aggregate/select/run a small subset before the full experiment.

Expected mutation killing output:
```
MUT_KILLING_PROFILE/<SUT>/main_mut_killing_profiles/mutants_profile_run_1/
```

Check that mutation profiles are not all zero before continuing to Step 5.

### 6. Run Phase 1 Sequentially
After the SUT-specific configuration works, run:
1. Step 1: input generation
2. Step 2: embedding generation
3. Step 3: mutation analysis
4. Step 4: cluster coverage
5. Step 5: mutation scores
6. Step 6: correlation analysis
7. Step 7: Jaccard agreement
8. Step 8: plots

For each step, use `--runs 1` first when available, inspect the output, and only then run the full experiment.

---
