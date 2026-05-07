import os
import pandas as pd
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

from FUZZ_TOOL_SELECTION.utils.clustering_analysis_utils import cluster_coverage_pipeline
from FUZZ_TOOL_SELECTION.utils.utils import infer_generator_order_from_inputs


# ============================================================
#  Define Model Directories and Parameters
# ============================================================
def get_embedding_models(root: str, subject: str) -> dict:
    """Map embedding models to their directories (each has run_X folders)."""
    base = os.path.join(root, subject)
    return {
        "OpenAI": os.path.join(base, "OPENAI"),
        "CODESTRAL": os.path.join(base, "CODESTRAL"),
        "GraphCodeBERT": os.path.join(base, "GRAPH_CODEBERT"),
        "UNIXCODER": os.path.join(base, "UNIXCODER"),
        "QWEN3": os.path.join(base, "QWEN3"),
    }


def get_cluster_algorithms() -> list:
    """Select which clustering algorithms to use."""
    return ["Affinity"]  # ["Affinity", "OPTICS", "HDBSCAN", "K-Means"]


def get_k_values() -> list:
    """Define K values to try for K-based clustering."""
    return [100, 250, 500, 1000]


# ============================================================
#  Model-level computation (runs in parallel per run)
# ============================================================
def process_model_for_run(model_name, model_dir, run_folder, algorithms, k_values, generator_order):
    """Compute cluster coverage for one embedding model inside a given run."""
    run_dir = os.path.join(model_dir, run_folder)
    if not os.path.exists(run_dir):
        print(f"[SKIP] {model_name} → no {run_folder} folder found.")
        return []

    print(f"\n[MODEL] {model_name} → {run_folder}")
    print(f" Reading vectors from: {run_dir}")

    try:
        rows, _ = cluster_coverage_pipeline(
            embedding_models={model_name: run_dir},
            algorithms=algorithms,
            k_values=k_values,
            generator_order=generator_order,
            output_csv=None,  # no per-model CSV
        )

        for r in rows:
            r["Run"] = run_folder
            r["Model"] = model_name


        return rows

    except Exception as e:
        print(f"[ERROR] Failed {model_name} → {run_folder}: {e}")
        return []


# ============================================================
#   Multi-Run Cluster Coverage Driver
# ============================================================
def run_cluster_coverage_multi_run(subject_program: str):
    SUBJECT = subject_program.upper()

    ROOT = "EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR"
    RESULT_ROOT = f"FUZZ_TOOL_SELECTION/result/{SUBJECT}"
    INPUT_BASE = f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{SUBJECT}"

    os.makedirs(RESULT_ROOT, exist_ok=True)

    # ---------------------------------------------------------
    # Load generator order (important for consistent column order)
    # ---------------------------------------------------------
    generator_order = infer_generator_order_from_inputs(base_input_dir=INPUT_BASE)
    if not generator_order:
        print("[WARN] Could not infer generator order — cluster coverage skipped.")
        return

    embedding_models = get_embedding_models(ROOT, SUBJECT)
    algorithms = get_cluster_algorithms()
    k_values = get_k_values()

    # ---------------------------------------------------------
    # Collect available run folders (shared across models)
    # ---------------------------------------------------------
    run_folders = sorted({
        f for model_path in embedding_models.values() if os.path.exists(model_path)
        for f in os.listdir(model_path) if f.startswith("run_")
    })

    if not run_folders:
        print("[WARN] No run folders found in any embedding model.")
        return

    print(f"\n[CFG] Found {len(run_folders)} runs: {run_folders}")
    print(f"[CFG] Models: {list(embedding_models.keys())}")

    # ---------------------------------------------------------
    # Parallelism setup: per run → models in parallel
    # ---------------------------------------------------------
    available_cores = multiprocessing.cpu_count()
    max_workers = min(len(embedding_models), available_cores)
    print(f"[INFO] Using up to {max_workers} cores for parallel model processing per run.")

    # =======================================================
    #  LOOP OVER RUNS (sequential, but each run uses all cores)
    # =======================================================
    for run_folder in run_folders:
        print(f"\n==================== 📊 RUN {run_folder.upper()} ====================")
        run_output_dir = os.path.join(RESULT_ROOT, run_folder)
        os.makedirs(run_output_dir, exist_ok=True)
        all_rows_for_run = []

        # Parallelize over models for this run
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_model_for_run,
                    model_name,
                    model_dir,
                    run_folder,
                    algorithms,
                    k_values,
                    generator_order
                ): model_name
                for model_name, model_dir in embedding_models.items()
            }

            for f in as_completed(futures):
                model = futures[f]
                try:
                    rows = f.result()
                    if rows:
                        all_rows_for_run.extend(rows)
                        print(f"[DONE] {model} completed for {run_folder}")
                    else:
                        print(f"[SKIP] No data for {model}")
                except Exception as e:
                    print(f"[FAIL]  {model} → {e}")

        # --- Save combined results for this run ---
        if all_rows_for_run:
            df_run = pd.DataFrame(all_rows_for_run)

            # Enforce consistent model order across runs
            # Define a fixed preferred order (modify if needed)
            model_order = ["OpenAI", "CODESTRAL", "GraphCodeBERT", "UNIXCODER", "QWEN3"]
            df_run["Model"] = pd.Categorical(df_run["Model"], categories=model_order, ordered=True)

            # Sort deterministically: Model first, then algo, then K_eff
            sort_cols = [c for c in ["Model", "Cluster Algo", "K_eff"] if c in df_run.columns]
            df_run = df_run.sort_values(sort_cols, ignore_index=True)

            # Fix consistent column order for saving
            metric_cols = ["Silhouette", "DBI", "CHI"]
            fixed_cols = ["Model", "Run", "Cluster Algo", "K_eff"] + metric_cols
            generator_cols = [c for c in df_run.columns if c not in fixed_cols]
            df_run = df_run[fixed_cols + generator_cols]

            # Save deterministic CSV
            summary_csv = os.path.join(run_output_dir, f"cluster_coverage_summary_{run_folder}.csv")
            df_run.to_csv(summary_csv, index=False)

            print(f"\n Run {run_folder} completed → summary saved at:\n   {summary_csv}")
        else:
            print(f"\n No results for {run_folder}.")

    print(f"\nAll runs completed sequentially. Results stored under: {RESULT_ROOT}")


# ============================================================
#  Entry Point
# ============================================================
if __name__ == "__main__":
    subject_program = "calc"  # or 'calc', 'rhino'
    run_cluster_coverage_multi_run(subject_program)
