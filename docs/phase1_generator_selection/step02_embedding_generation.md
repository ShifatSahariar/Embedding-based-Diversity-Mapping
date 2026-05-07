[← Back to Phase 1 overview](../phase1_generator_selection.md) | [Previous: Step 1 — Test Input Generation](step01_test_input_generation.md) | [Next: Step 3 — Mutation Analysis](step03_mutation_analysis.md)

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
