import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".plot_cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(REPO_ROOT / ".plot_cache"))
sys.path.insert(0, str(REPO_ROOT))

import matplotlib

matplotlib.use("Agg")

from PRIORATIZATION.prioritization_utils.auc_utils import aggregate_results, plot_auc_curves
from PRIORATIZATION.prioritization_utils.embeddings_loader import load_embeddings_to_prioritize
from PRIORATIZATION.prioritization_utils.ms_utils import filter_mutation_profiles, load_mutation_profiles
from PRIORATIZATION.prioritization_utils.run_selection_approaches import run_selection_approaches
from PRIORATIZATION.prioritization_utils.tool_selection_ranksum import get_best_tool, compute_ranksum_all_models
from PRIORATIZATION.research_questions.early_fault_detection_util import compute_rq3_metrics, save_rq3_table
from PRIORATIZATION.research_questions.stability_compare_util import compute_rq4_metrics, save_rq4_table


DEFAULT_CANDIDATE_TOOLS = [
    "fan_con",
    "fan_no_con",
    "fuzz_equal",
    "fuzz_prob",
    "isla_con",
    "isla_no_con",
    "openai_gram",
    "openai_no_gram",
]


def natural_run_key(name):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def parse_budgets(value):
    return [int(part.strip()) for part in value.split(",") if part.strip()]


# Main Selection Pipeline
# ============================================================
def prioritize_inputs_pipeline(
        subject_program,
        embeddings_dir,
        mut_profiles_dir,
        embedding_model,
        generator_tool,
        budgets,
        n_runs=None,
        n_jobs=1,
        limit=1000,
        selection_repeats=50,
):
    # First We Locate all embedding runs for this model
    # ------------------------------------------------------------
    model_path = os.path.join(embeddings_dir, embedding_model.upper())
    if not os.path.isdir(model_path):
        raise FileNotFoundError(
            f"Embedding model folder not found: {model_path}. "
            "Run Phase 1 Step 2 for this subject/model before Phase 2."
        )
    run_folders = sorted(
        [d for d in os.listdir(str(model_path)) if d.startswith("run_")],
        key=natural_run_key,
    )

    if not run_folders:
        raise FileNotFoundError(f"No run folders found under {model_path}")

    if n_runs is None:
        n_runs = len(run_folders)

    print(f"\n  Starting Prioritization for {embedding_model} ({generator_tool})")
    print(f"[INFO] Found {n_runs} runs → {run_folders[:n_runs]}")

    # ------------------------------------------------------------
    # Step 2. Iterate over each run and process
    # ------------------------------------------------------------
    for run_idx, run_name in enumerate(run_folders[:n_runs], start=1):
        print(f"\n========== Run {run_idx}/{n_runs}: {run_name} ==========")
        cluster_analysis_dir = os.path.join("PRIORATIZATION", "ALL_SUT_RESULTS", subject_program, embedding_model.upper(), run_name)
        # Loading embeddings for this run
        run_embedding_dir = os.path.join(str(model_path), run_name)
        embeddings = load_embeddings_to_prioritize(run_embedding_dir, prefix=generator_tool, limit=limit)
        if not embeddings:
            raise RuntimeError(
                f"No embeddings found for generator '{generator_tool}' in {run_embedding_dir}. "
                "Check the selected generator prefix and embedding output files."
            )

        # Loading matching mutation profiles with prefix which indicate generator tool name
        run_profile_dir = os.path.join(mut_profiles_dir, f"mutants_profile_{run_name}")
        mut_profiles_dict = load_mutation_profiles(
            run_profile_dir,
            prefix=generator_tool,
            # we will only load the profiles corresponding with-
            # the embedding profiles we have loaded
            allowed_names=set(embeddings.keys()))
        if not mut_profiles_dict:
            raise RuntimeError(
                f"No matching mutation profiles found for generator '{generator_tool}' in {run_profile_dir}. "
                "Run Phase 1 Step 3 mutation execution before Phase 2."
            )

        # Filter mutants : first filter the mutants and only kept hard mutants
        print(f"Filtering mutants for {subject_program}")
        tool_selection_dir = os.path.join("PRIORATIZATION", "ALL_SUT_RESULTS", subject_program, "tool_selection")
        os.makedirs(tool_selection_dir, exist_ok=True)
        filtered_profiles_dict, _ = filter_mutation_profiles(
            mut_profiles_dict,
            min_rate=0.0,
            max_rate=0.5,
            drop_never=True,
            drop_always=True,
            dedup=True,
            subsumption=True,
            save_csv_path=os.path.join(tool_selection_dir, f"filtered_mutation_profiles_{run_name}.csv")
        )

        # have to save the filtered mut profile for analysis
        # Running Prioritization approaches
        print("[STEP] Running Prioritization approaches...")
        results,selection_sequences = run_selection_approaches(
            embeddings,
            filtered_profiles_dict,
            budgets,
            n_runs=selection_repeats,  # repeats non-deterministic approaches
            n_jobs=n_jobs,
            cluster_analysis_dir=cluster_analysis_dir
        )

        save_dir = os.path.join("PRIORATIZATION", "ALL_SUT_RESULTS", subject_program, embedding_model.upper(), run_name)
        os.makedirs(save_dir, exist_ok=True)
        # After getting MS values for each input selection for all runs  for non-deterministic and only one time for deterministic,
        # we aggregate and plot results
        print("[STEP] Aggregating and plotting...")
        mean_std, normalized_auc = aggregate_results(results, save_dir)
        plot_auc_curves(mean_std, normalized_auc, save_dir=save_dir)

        print(f"[✅] Saved results for {run_name} in {save_dir}")
        metrics = compute_rq3_metrics(
            selection_sequences,
            filtered_profiles_dict,
            results,
            budgets,
            subject_program,
            run_name
        )
        save_rq3_table(metrics, subject_program, run_name)
        metrics = compute_rq4_metrics(
            selection_sequences,
            filtered_profiles_dict,
            results,
            budgets,
            subject_program,
            run_name
        )
        # RQ4
        save_rq4_table(metrics, subject_program, run_name)

    print("\n Pipeline Completed for All Independent Experiments successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2 SpreadEx input prioritization.")
    parser.add_argument("--subject", type=str, default="karatejs", help="Subject/SUT name, e.g., karatejs, calc, basic.")
    parser.add_argument("--model", type=str, default="UNIXCODER", help="Embedding model folder/name, e.g., UNIXCODER, OpenAI.")
    parser.add_argument("--budgets", type=parse_budgets, default=parse_budgets("5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100"),
                        help="Comma-separated input budgets, e.g., 1,2,3 for a smoke test.")
    parser.add_argument("--runs", type=int, default=None, help="Limit to the first N independent input runs.")
    parser.add_argument("--rank-runs", type=int, default=None, help="Limit the Phase 1 run folders used for RankSum tool selection.")
    parser.add_argument("--selection-repeats", type=int, default=50, help="Repeats for non-deterministic baselines such as Random.")
    parser.add_argument("--n-jobs", type=int, default=1, help="Parallel jobs for non-deterministic baselines. Use 1 for smoke tests.")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum inputs to load per run for the selected generator.")
    parser.add_argument("--generator-tool", type=str, default=None,
                        help="Override automatic RankSum tool selection with a generator prefix, e.g., fan_con.")
    args = parser.parse_args()

    subject_program = args.subject.upper()
    embedding_model = args.model.upper()
    budgets = args.budgets
    n_runs = args.runs
    n_jobs = args.n_jobs
    limit = args.limit
    candidate_tools = DEFAULT_CANDIDATE_TOOLS

    cluster_coverage_path = REPO_ROOT / "FUZZ_TOOL_SELECTION" / "result" / subject_program
    #  to select the best input generators for each independent experiment we compute RankSum for ALL models
    ranksum_all, winners = compute_ranksum_all_models(
        base_dir=str(cluster_coverage_path),
        candidate_tools=candidate_tools,
        n_runs=args.rank_runs,
        save_dir=str(REPO_ROOT / "PRIORATIZATION" / "ALL_SUT_RESULTS" / subject_program / "tool_selection"))

    #  For the model, we want the selected tool
    if args.generator_tool:
        best_tool = args.generator_tool
        rank_value = "manual override"
    else:
        best_tool, rank_value = get_best_tool(
            embedding_model,
            str(REPO_ROOT / "PRIORATIZATION" / "ALL_SUT_RESULTS" / subject_program / "tool_selection" / "ranksum_all_models.csv")
        )

    print(best_tool, rank_value)

    # PATHS for loading embedding and mutation killing profiles
    # ============================================================
    embeddings_path = REPO_ROOT / "EMBEDDINGS" / "VECTORS_COLLECTION" / "INPUT_SELECTOR" / subject_program
    profiles_path = REPO_ROOT / "MUT_KILLING_PROFILE" / subject_program / "main_mut_killing_profiles"

    print("\n===================================================")
    print(" INPUT PRIORITIZATION + SELECTION : — CONFIG SUMMARY")
    print("===================================================")
    print(f" Subject Program : {subject_program}")
    print(f" Embedding Model : {embedding_model}")
    print(f" Generator Tool  : {best_tool}")
    print(f" Budgets         : {budgets}")
    print(f" Max Inputs/Run  : {limit}")
    print(f" Parallel Jobs   : {n_jobs}")
    print(f" Runs            : {'Auto-detected' if n_runs is None else n_runs}")
    print("===================================================\n")

    # EXECUTE PIPELINE
    # ============================================================
    try:
        prioritize_inputs_pipeline(
            subject_program=subject_program,
            embeddings_dir=str(embeddings_path),
            mut_profiles_dir=str(profiles_path),
            embedding_model=embedding_model.upper(),
            generator_tool=best_tool,
            budgets=budgets,
            n_runs=n_runs,
            n_jobs=n_jobs,
            limit=limit,
            selection_repeats=args.selection_repeats,
        )
        print("\nAll experiments completed successfully.\n")

    except Exception as e:
        print("\n Pipeline failed due to an unexpected error:")
        print(f"   {type(e).__name__}: {e}\n")
        raise
