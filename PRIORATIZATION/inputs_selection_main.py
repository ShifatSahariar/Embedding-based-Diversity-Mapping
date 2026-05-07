import os
from PRIORATIZATION.prioritization_utils.auc_utils import aggregate_results, plot_auc_curves
from PRIORATIZATION.prioritization_utils.embeddings_loader import load_embeddings_to_prioritize
from PRIORATIZATION.prioritization_utils.ms_utils import filter_mutation_profiles, load_mutation_profiles
from PRIORATIZATION.prioritization_utils.run_selection_approaches import run_selection_approaches
from PRIORATIZATION.prioritization_utils.tool_selection_ranksum import get_best_tool, compute_ranksum_all_models
from PRIORATIZATION.research_questions.early_fault_detection_util import compute_rq3_metrics, save_rq3_table
from PRIORATIZATION.research_questions.stability_compare_util import compute_rq4_metrics, save_rq4_table


# Main Selection Pipeline
# ============================================================
def PRIORATIZATIONprioritize_inputs_pipeline(
        subject_program,
        embeddings_dir,
        mut_profiles_dir,
        embedding_model,
        generator_tool,
        budgets,
        n_runs=None,
        n_jobs=1,
        limit=1000,
):
    # First We Locate all embedding runs for this model
    # ------------------------------------------------------------
    model_path = os.path.join(embeddings_dir, embedding_model)
    run_folders = sorted(
        [d for d in os.listdir(str(model_path)) if d.startswith("run_")]
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
        cluster_analysis_dir = os.path.join("ALL_SUT_RESULTS", subject_program, embedding_model.upper(), run_name)
        # Loading embeddings for this run
        run_embedding_dir = os.path.join(str(model_path), run_name)
        embeddings = load_embeddings_to_prioritize(run_embedding_dir, prefix=generator_tool, limit=limit)

        # Loading matching mutation profiles with prefix which indicate generator tool name
        run_profile_dir = os.path.join(mut_profiles_dir, f"mutants_profile_{run_name}")
        mut_profiles_dict = load_mutation_profiles(
            run_profile_dir,
            prefix=generator_tool,
            # we will only load the profiles corresponding with-
            # the embedding profiles we have loaded
            allowed_names=set(embeddings.keys()))

        # Filter mutants : first filter the mutants and only kept hard mutants
        print(f"Filtering mutants for {subject_program}")
        filtered_profiles_dict, _ = filter_mutation_profiles(
            mut_profiles_dict,
            min_rate=0.0,
            max_rate=0.5,
            drop_never=True,
            drop_always=True,
            dedup=True,
            subsumption=True,
            save_csv_path=f"ALL_SUT_RESULTS/{subject_program}/tool_selection/filtered_mutation_profiles_{run_name}.csv"
        )

        # have to save the filtered mut profile for analysis
        # Running Prioritization approaches
        print("[STEP] Running Prioritization approaches...")
        results,selection_sequences = run_selection_approaches(
            embeddings,
            filtered_profiles_dict,
            budgets,
            n_runs=50,  # each independent experiment repeats selection - non-deterministic approaches
            n_jobs=n_jobs,
            cluster_analysis_dir=cluster_analysis_dir
        )

        save_dir = os.path.join("ALL_SUT_RESULTS", subject_program, embedding_model.upper(), run_name)
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
    #  CONFIGURATION SECTION
    # ============================================================
    # the subject program we want to have the result
    # BASIC, RHINO, CALC, NASHORN ,GRAALJS ,KARATEJS
    subject_program = "BASIC".upper()
    # Could be any model ,we may automate to select the model.
    # but for now we have chosen the best model for us
    # CODESTRAL, CODEBERT, UNIXCODER,OpenAI
    embedding_model = "OpenAI"

    # inputs selection budgets for each approach
    # budgets = [2] + list(range(5, 105, 5))
    budgets = [5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100]

    # how many independent experiment we do have | if we don't mention then auto-detection
    n_runs = None
    # we have some difficulties to sync with multithreading now
    n_jobs = 1
    # for now, it will be always 1000, but we can also take dynamically # max inputs to use per run
    limit = 1000

    candidate_tools = ["fan_con", "fan_no_con", "fuzz_equal", "fuzz_prob", "isla_con", "isla_no_con", "openai_gram",
                       "openai_no_gram"]
    cluster_coverage_path = f"../FUZZ_TOOL_SELECTION/result/{subject_program}"
    #  to select the best input generators for each independent experiment we compute RankSum for ALL models
    ranksum_all, winners = compute_ranksum_all_models(
        base_dir=cluster_coverage_path,
        candidate_tools=candidate_tools,
        n_runs=10,
        save_dir=f"ALL_SUT_RESULTS/{subject_program}/tool_selection")

    #  For the model, we want the selected tool
    best_tool, rank_value = get_best_tool(
        embedding_model,
        f"ALL_SUT_RESULTS/{subject_program}/tool_selection/ranksum_all_models.csv"
    )

    print(best_tool, rank_value)

    # PATHS for loading embedding and mutation killing profiles
    # ============================================================
    embeddings_path = f"../EMBEDDINGS/VECTORS_COLLECTION/INPUT_SELECTOR/{subject_program}"
    profiles_path = f"../MUT_KILLING_PROFILE/{subject_program}/main_mut_killing_profiles"

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
            embeddings_dir=embeddings_path,
            mut_profiles_dir=profiles_path,
            embedding_model=embedding_model.upper(),
            generator_tool=best_tool,
            budgets=budgets,
            n_runs=n_runs,
            n_jobs=n_jobs,
            limit=limit,
        )
        print("\nAll experiments completed successfully.\n")

    except Exception as e:
        print("\n Pipeline failed due to an unexpected error:")
        print(f"   {type(e).__name__}: {e}\n")
        raise
