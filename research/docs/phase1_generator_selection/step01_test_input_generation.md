[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Environment and Tool Setup](00_environment_setup.md) | [Next: Step 2 — Embedding Generation](step02_embedding_generation.md)

---

## 1️⃣ Test Input Generation

Run `Generation_Test_Inputs.py` to generate test inputs for the target SUT using all configured generators.

Each generator produces the same number of inputs to ensure a fair comparison.
For an IDE smoke test, start with 2-3 inputs per tool and 1 run. For full paper-scale reproduction, use 1,000 inputs per tool and 10 runs.

With an IDE, you can edit the configuration near the top of `Generation_Test_Inputs.py`:
```python
pipeline_config = {
    'subject_program': 'karatejs',       # Options: CALC | rhino | basic | karatejs | nashorn | graaljs
    'generate_inputs': True,             # keep true
    'clean_previous_data': False,        # set true if you want to clean previously generated inputs
    'num_inputs_per_tool': 3,            # smoke test: 2-3; full experiment: 1000
    'num_random_runs': 1,                # smoke test: 1; full experiment: 10
}
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
