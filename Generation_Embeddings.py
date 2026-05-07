import os
import shutil
import argparse
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# =====================================
# Model Import Map (auto-dispatch)
# =====================================
MODEL_EXPORT_FUNCS = {
    "OPENAI": "EMBEDDINGS.VECTOR_MODELS.OpenAI_Embedding.export_openai_embeddings",
    "CODESTRAL": "EMBEDDINGS.VECTOR_MODELS.codestral_Embedding.export_codestral_vectors",
    "GRAPH_CODEBERT": "EMBEDDINGS.VECTOR_MODELS.GraphCodeBERT_Embedding.export_graphcodebert_vectors",
    "UNIXCODER": "EMBEDDINGS.VECTOR_MODELS.uni_x_coder_Embedding.export_uniXcoder_vectors",
    "QWEN3": "EMBEDDINGS.VECTOR_MODELS.qwen3_Embedding.export_qwen3_vectors"
}

MODEL_REQUIREMENTS = {
    "OPENAI": {
        "packages": ["openai"],
        "env": ["OPENAI_API_KEY"],
    },
    "CODESTRAL": {
        "packages": ["mistralai"],
        "env": ["MISTRAL_API_KEY"],
    },
    "GRAPH_CODEBERT": {
        "packages": ["torch", "transformers"],
        "env": [],
    },
    "UNIXCODER": {
        "packages": ["torch", "transformers"],
        "env": [],
    },
    "QWEN3": {
        "packages": ["torch", "transformers"],
        "env": [],
    },
}

# =====================================
#  Utility: Dynamic import
# =====================================
def dynamic_import(path_str):
    """Import a function dynamically given 'module.submodule.function'."""
    module_name, func_name = path_str.rsplit(".", 1)
    mod = __import__(module_name, fromlist=[func_name])
    return getattr(mod, func_name)


def _run_sort_key(folder_name):
    try:
        return int(folder_name.rsplit("_", 1)[-1])
    except ValueError:
        return folder_name


def validate_model_environment(model_name):
    """Return True if the selected embedding model has its required package/env setup."""
    model_upper = model_name.upper()
    requirements = MODEL_REQUIREMENTS.get(model_upper)
    if not requirements:
        print(f"[{model_upper}] Unsupported model. Available models: {sorted(MODEL_EXPORT_FUNCS)}")
        return False

    missing_packages = [
        package for package in requirements["packages"]
        if importlib.util.find_spec(package) is None
    ]
    missing_env = [
        env_name for env_name in requirements["env"]
        if not os.getenv(env_name)
    ]

    if missing_packages:
        print(
            f"[{model_upper}] Missing Python package(s): {', '.join(missing_packages)}. "
            "Install dependencies with: pip install -r requirements.txt"
        )
    if missing_env:
        print(
            f"[{model_upper}] Missing environment variable(s): {', '.join(missing_env)}. "
            "Configure the API key or remove this model from --models for a smoke test."
        )

    return not missing_packages and not missing_env


# =====================================
#  Process Single Run
# =====================================
def process_single_run(subject_program, model_name, run_input_dir, run_output_dir):
    """Process one run folder for one model safely with retry and repair."""
    os.makedirs(run_output_dir, exist_ok=True)
    model_upper = model_name.upper()
    print(f"[{model_upper}] → Processing {run_input_dir}")

    # collect all txt files
    files = [
        f for f in os.listdir(run_input_dir)
        if os.path.isfile(os.path.join(run_input_dir, f)) and f.endswith(".txt")
    ]
    if not files:
        print(f"[{model_upper}]  No input files found in {run_input_dir}.")
        return False

    # dynamically call exporter
    try:
        export_func = dynamic_import(MODEL_EXPORT_FUNCS[model_upper])
        export_func(run_input_dir, run_output_dir)
    except Exception as e:
        print(f"[{model_upper}] Error during embedding export: {e}")
        traceback.print_exc()
        return False

    # check missing vectors and repair if needed
    repair_missing_vectors(run_input_dir, run_output_dir, model_upper)
    print(f"[{model_upper}] Finished embeddings for {os.path.basename(run_input_dir)}")
    return True


# =====================================
# 🔹 Repair Missing Vectors
# =====================================
def repair_missing_vectors(run_input_dir, run_output_dir, model_upper):
    missing = [
        f for f in os.listdir(run_input_dir)
        if f.endswith(".txt") and
        not os.path.exists(os.path.join(run_output_dir, f.replace(".txt", "_vector.txt")))
    ]
    if not missing:
        return

    print(f"[{model_upper}] 🔁 Retrying {len(missing)} missing files...")
    tmp_dir = os.path.join(run_input_dir, "_retry_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    for f in missing:
        shutil.copy(os.path.join(run_input_dir, f), tmp_dir)

    try:
        export_func = dynamic_import(MODEL_EXPORT_FUNCS[model_upper])
        export_func(tmp_dir, run_output_dir)
    except Exception as e:
        print(f"[{model_upper}] Retry failed: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =====================================
# 🔹 Unified Model Runner
# =====================================
def process_model_runs(subject_program, model_name, base_input_dir, base_output_dir, run_limit=None):
    """Process all run folders for a model (safe parallel per run)."""
    model_upper = model_name.upper()
    print(f"\n==================== MODEL: {model_upper} ====================")

    model_output_root = os.path.join(base_output_dir, model_upper)
    os.makedirs(model_output_root, exist_ok=True)

    if not validate_model_environment(model_upper):
        print(f"[{model_upper}] Skipping model because setup is incomplete.")
        return False

    run_folders = sorted([
        f for f in os.listdir(base_input_dir) if f.startswith("input_pool_by_run_")
    ], key=_run_sort_key)
    if run_limit is not None:
        run_folders = run_folders[:run_limit]
    if not run_folders:
        print(f"[WARN] No input folders found for {subject_program}.")
        return

    print(f"[{model_upper}] Found {len(run_folders)} run folders → {run_folders}")

    # Run up to 3 runs in parallel
    with ThreadPoolExecutor(max_workers=min(3, len(run_folders))) as run_pool:
        futures = []
        for run_folder in run_folders:
            run_id = run_folder.split("_")[-1]  # use actual suffix (e.g. "10")
            run_input = os.path.join(base_input_dir, run_folder)
            run_output = os.path.join(str(model_output_root), f"run_{run_id}")

            futures.append(
                run_pool.submit(
                    process_single_run,
                    subject_program,
                    model_upper,
                    run_input,
                    run_output
                )
            )

        completed_runs = 0
        for f in as_completed(futures):
            try:
                if f.result():
                    completed_runs += 1
            except Exception as e:
                print(f"[{model_upper}] ❌ Run failed: {e}")

    if completed_runs == len(run_folders):
        print(f"[{model_upper}] Completed all runs.")
        return True

    print(f"[{model_upper}] Completed {completed_runs}/{len(run_folders)} run(s).")
    return False
# ============================================================
# MAIN FUNCTION (Drop-in replacement)
# ============================================================
def generate_embeddings_for_all_runs(subject_program, vector_models,
                                     base_input_dir=None, base_output_dir=None,
                                     run_limit=None):
    """Unified entry: run all models (API & local) in parallel."""
    print(f"\nFound {len(vector_models)} models → {vector_models}")

    # Running all models in parallel
    with ThreadPoolExecutor(max_workers=min(len(vector_models), 3)) as pool:
        futures = [
            pool.submit(process_model_runs, subject_program, model, base_input_dir, base_output_dir, run_limit)
            for model in vector_models
        ]
        completed = 0
        for f in as_completed(futures):
            try:
                if f.result():
                    completed += 1
            except Exception as e:
                print(f"[ERROR] Model failed: {e}")

    if completed:
        print(f"\n Embedding generation completed for {completed}/{len(vector_models)} selected model(s).")
    else:
        print("\n No embeddings were generated. Fix the setup messages above or choose a configured model.")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for generated test inputs.")
    parser.add_argument("--subject", type=str, default="karatejs", help="SUT name, e.g., CALC, basic, rhino, karatejs")
    parser.add_argument(
        "--models",
        type=str,
        default="unixcoder",
        help="Comma-separated embedding models. Options: openai,codestral,graph_codebert,unixcoder,qwen3",
    )
    parser.add_argument("--runs", type=int, default=None, help="Limit to the first N run folders for a smoke test")
    args = parser.parse_args()

    subject_program = args.subject
    models_to_run = [model.strip() for model in args.models.split(",") if model.strip()]

    generate_embeddings_for_all_runs(
        subject_program=subject_program,
        vector_models=models_to_run,
        base_input_dir=f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{subject_program.upper()}",
        base_output_dir=f"EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/{subject_program.upper()}",
        run_limit=args.runs,
    )
