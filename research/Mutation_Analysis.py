
import argparse
import os

from Helper_Functions.Mutation_Helping_Functions import generate_mutants, aggregate_mutants, sort_mutants


# ============================================================
# 🔧 Utility helpers
# ============================================================
def count_existing_runs(subject_program: str) -> int:
    """Counting existing run folders under GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/<subject>"""
    base_dir = f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{subject_program.upper()}"
    if not os.path.exists(base_dir):
        print(f"[WARN] No input folders found under {base_dir}")
        return 0
    folders = [f for f in os.listdir(base_dir) if f.startswith("input_pool_by_run_")]
    print(f"[INFO] Detected {len(folders)} run folder(s) for {subject_program}.")
    return len(folders)


def is_empty_dir(path):
    return not os.path.exists(path) or len(os.listdir(path)) == 0


def run_sort_key(folder_name):
    try:
        return int(folder_name.rsplit("_", 1)[-1])
    except ValueError:
        return folder_name


def normalize_subject_for_mutation(subject_program: str) -> str:
    subject = subject_program.strip()
    return "CALC" if subject.lower() == "calc" else subject.lower()


# ============================================================
# Coverage Phase
# ============================================================

def run_coverage_phase(subject_program: str,
                       generate_coverage: bool = False,
                       run_limit: int | None = None,
                       parallel_mode: bool = False,
                       analyze_results: bool = False):
    from COVERAGE_REPORTS.original_result_with_coverage import coverage_profile_with_original_result
    subject_key = normalize_subject_for_mutation(subject_program)
    print(f"\n==================== RUNNING COVERAGE PHASE for {subject_key.upper()} ====================")

    # The function itself handles discovering and looping through all run folders
    coverage_profile_with_original_result(
        sut_program=subject_key,
        generate_coverage=generate_coverage,
        adaptive_timeout=20,
        parallel_mode=parallel_mode,
        run_limit=run_limit,
        analyze_results=analyze_results,
    )

    print(f"\n Completed coverage for all runs of {subject_key.upper()}.")


# ============================================================
# Mutation Phase — Per Run Folder
# ============================================================
def run_mutation_phase(subject_program: str,
                       generate_mutants_flag=False,
                       aggregate_mutants_flag=False,
                       selecting_mutants_flag=False,
                       running_mutants_flag=False,
                       base_seed: int = 7,
                       budget: int = 100,
                       min_per_class: int = 5,
                       input_start: int = 1,
                       input_end: int | None = None,
                       chunk_size: int = 500,
                       run_limit: int | None = None,
                       target_classes: list[str] | None = None):
    from MUT_KILLING_PROFILE.random_mutants_selection import preview_selection
    from MUT_KILLING_PROFILE.Mutation_Killing_Profile import run_mutants_with_inputs
    subject_key = normalize_subject_for_mutation(subject_program)
    key = subject_key.upper()
    aggregated_mutants_path = f"MUT_KILLING_PROFILE/{key}/aggregated_mutants"
    selected_root = f"MUT_KILLING_PROFILE/{key}/selected_mutants"
    mutation_profiles_root = f"MUT_KILLING_PROFILE/{key}/main_mut_killing_profiles"
    # if mutation_profiles_root:
    #     shutil.rmtree(mutation_profiles_root, ignore_errors=True)
    #     os.makedirs(mutation_profiles_root, exist_ok=True)
    # ---- Determine how many runs to process ----
    inputs_root = f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{key}"
    if not os.path.exists(inputs_root):
        print(f"[WARN] No input root found at {inputs_root}. Generate inputs first.")
        return

    run_folders = sorted([
        f for f in os.listdir(inputs_root)
        if f.startswith("input_pool_by_run_")
    ], key=run_sort_key)
    if run_limit is not None:
        run_folders = run_folders[:run_limit]
    n_runs = len(run_folders)
    if n_runs == 0:
        print("[WARN] No input runs found — please generate inputs first.")
        return

    print(f"\n==================== ⚙️ MUTATION ANALYSIS ({n_runs} runs) ====================")

    # Generate Mutants — Once - while we already decided which class we will use to generate mutants
    # So even if we see that - AGGREGATED MUTANTS -- are missing, we will take as that we have to generate again
    if generate_mutants_flag :  #or is_empty_dir(aggregated_mutants_path)
        print(f" Generating mutants for {subject_key}...")
        generate_mutants(subject_program=subject_key, target_classes_override=target_classes)
    else:
        print("Skipped mutant generation (already exists).")

    # Aggregate Mutants — Once - [ If we generate again, we should also aggregate again ]
    if aggregate_mutants_flag:
        print("Aggregating mutants...")
        aggregate_mutants(subject_program=subject_key, aggregated_mutants_path=aggregated_mutants_path)
    else:
        print("[STEP 2] Skipped aggregation.")

    if not selecting_mutants_flag and not running_mutants_flag:
        print("[INFO] No per-run mutation phase enabled. Stopping after requested setup phase(s).")
        return

    if is_empty_dir(aggregated_mutants_path):
        print(
            f"[STOP] No aggregated mutants found at {aggregated_mutants_path}. "
            "Run with --aggregate_mutants true after mutant generation, or provide the artifact's aggregated mutants."
        )
        return

    print(f"\n==================== 🧬 STARTING MUTATION RUNNING ({n_runs} runs for {key}) ====================")

    # ---- Always show a preview (non-destructive) ----
    print(f"\n📊 Preview — Planned Per-Class Mutant Counts (Seed={base_seed}):")
    counts_preview = preview_selection(
        aggregated_mutants_path,
        budget=budget,
        allocation="proportional",
        seed=base_seed,
        min_per_class=min_per_class,
    )
    if not counts_preview:
        print("[STOP] Aggregated mutants folder exists, but no selectable mutant folders were found.")
        return
    for cls, k in sorted(counts_preview.items()):
        print(f"  {cls}: {k}")
    print("--------------------------------------------------")

    # ---- Per-Run Execution ----
    for run_idx, run_folder in enumerate(run_folders, start=1):
        print(f"\n==================== 🧬 RUN {run_idx}/{n_runs} ({run_folder}) ====================")

        # --- Step 3: Selecting mutants ---
        selected_mutants_path = os.path.join(selected_root, f"selected_mutants_run_{run_idx}")

        if selecting_mutants_flag:
            from MUT_KILLING_PROFILE.random_mutants_selection import  select_mutants
            print(f"[STEP 3] Selecting mutants for run {run_idx} ...")
            run_seed = base_seed + run_idx  # ensure unique selection
            per_class, selected = select_mutants(
                src=aggregated_mutants_path,
                dst=selected_mutants_path,
                budget=budget,
                allocation="proportional",
                seed=run_seed,
                min_per_class=5,
                copy=True,
                overwrite=True
            )
            print(f"[STEP 3] Selected {len(selected)} mutants for run_{run_idx}.")
        else:
            print(f"[STEP 3] Skipped mutant selection (reusing {selected_mutants_path}).")

        # --- Step 4: Running mutants ---
        if running_mutants_flag:
            if is_empty_dir(selected_mutants_path):
                print(
                    f"[STOP] Selected mutants are missing at {selected_mutants_path}. "
                    "Run with --selecting_mutants true first, or provide pre-selected mutants."
                )
                return

            print(f"[STEP 4] Running mutants for run {run_idx} ...")

            input_files_directory = os.path.join(
                "GENERATED_INPUTS/FUZZ_TOOL_SELECTOR", key, f"input_pool_by_run_{run_idx}")
            original_results_directory = os.path.join(
                "COVERAGE_REPORTS", key, f"coverage_input_pool_by_run_{run_idx}")
            mutation_profiles_dir = os.path.join(
                mutation_profiles_root, f"mutants_profile_run_{run_idx}")
            os.makedirs(mutation_profiles_dir, exist_ok=True)

            all_mutants_paths = sort_mutants(selected_mutants_path)

            run_mutants_with_inputs(
                subject_program=subject_key,
                mutants_paths=all_mutants_paths,
                input_start=input_start,
                input_end=input_end,
                chunk_size=chunk_size,
                adaptive_timeout=15,
                input_files_directory=input_files_directory,
                original_results_directory=original_results_directory,
                reports_directory=mutation_profiles_dir
            )
        else:
            print(f"[STEP 4] Skipped running mutants for run {run_idx}.")

        # # Filtering profiles ---
        # if filter_mutant_profile_flag:
        #     print(f"[STEP 5] Filtering mutant profiles (Run {run_idx}) ...")
        #     process_mutation_killing_profiles(
        #         mutation_profiles_dir, subject_program, results_dir)
        # else:
        #     print(f"[STEP 5] Skipped filtering profiles for run {run_idx}.")

        print(f"✅ Completed mutation run {run_idx}/{n_runs}")

    print(f"\n✅ Mutation utils completed for {n_runs} run(s) of {key}.\n")



#Entry Point
# ============================================================
def main():
    # Default IDE Flags
    # -------------------------------
    coverage_mode = False
    mutation_mode = True
    subject_program = "karatejs" # nashorn | basic | CALC | rhino | graaljs | karatejs

    # Mutation phase flags
    generate_mutants_flag = False
    aggregate_mutants_flag = False
    selecting_mutants_flag = False
    running_mutants_flag = True  # enable explicitly after fresh original outputs exist
    filter_mutant_profile_flag = False

    # -------------------------------
    # CLI Argument Overrides
    # -------------------------------
    parser = argparse.ArgumentParser(description="Mutation Analysis Pipeline CLI")
    parser.add_argument("--subject", type=str, default=subject_program)
    parser.add_argument("--coverage_only", type=lambda x: x.lower() == "true", default=coverage_mode)
    parser.add_argument(
        "--generate_coverage",
        type=lambda x: x.lower() == "true",
        default=False,
        help="When coverage_only is true, also collect JaCoCo XML/coverage profiles. Keep false for mutation baseline smoke tests.",
    )
    parser.add_argument(
        "--parallel",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Run coverage/original-baseline inputs in parallel. Keep false for smoke tests.",
    )
    parser.add_argument(
        "--analyze_results",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Create return-code/exception plots after baseline execution. Keep false for smoke tests.",
    )
    parser.add_argument("--mutation_only", type=lambda x: x.lower() == "true", default=mutation_mode)
    parser.add_argument("--generate_mutants", type=lambda x: x.lower() == "true", default=generate_mutants_flag)
    parser.add_argument("--aggregate_mutants", type=lambda x: x.lower() == "true", default=aggregate_mutants_flag)
    parser.add_argument("--selecting_mutants", type=lambda x: x.lower() == "true", default=selecting_mutants_flag)
    parser.add_argument("--running_mutants", type=lambda x: x.lower() == "true", default=running_mutants_flag)
    parser.add_argument("--filter_mutant_profile", type=lambda x: x.lower() == "true", default=filter_mutant_profile_flag)
    parser.add_argument("--budget", type=int, default=100, help="Number of mutants to select per run")
    parser.add_argument("--min_per_class", type=int, default=5, help="Minimum selected mutants per class when possible")
    parser.add_argument("--input_start", type=int, default=1, help="1-based first input index for mutation execution")
    parser.add_argument("--input_end", type=int, default=None, help="1-based last input index for mutation execution; omit to use all inputs")
    parser.add_argument("--chunk_size", type=int, default=500, help="Number of inputs per mutation execution chunk")
    parser.add_argument("--runs", type=int, default=None, help="Limit to first N input run folders for a smoke test")
    parser.add_argument(
        "--target_classes",
        type=str,
        default=None,
        help="Comma-separated PIT target class names for mutant-generation smoke tests; omit to use the configured subject target classes.",
    )
    args = parser.parse_args()
    target_classes = None
    if args.target_classes:
        target_classes = [cls.strip() for cls in args.target_classes.split(",") if cls.strip()]

    # -------------------------------
    # Decision Logic
    # -------------------------------
    if args.coverage_only:
        run_coverage_phase(
            args.subject,
            generate_coverage=args.generate_coverage,
            run_limit=args.runs,
            parallel_mode=args.parallel,
            analyze_results=args.analyze_results,
        )

    if args.mutation_only:
        run_mutation_phase(
            subject_program=args.subject,
            generate_mutants_flag=args.generate_mutants,
            aggregate_mutants_flag=args.aggregate_mutants,
            selecting_mutants_flag=args.selecting_mutants,
            running_mutants_flag=args.running_mutants,
            budget=args.budget,
            min_per_class=args.min_per_class,
            input_start=args.input_start,
            input_end=args.input_end,
            chunk_size=args.chunk_size,
            run_limit=args.runs,
            target_classes=target_classes,
        )

    if not args.coverage_only and not args.mutation_only:
        print("[INFO] Please specify or enable at least one phase: coverage or mutation.")


if __name__ == "__main__":
    # python Mutation_Analysis.py --subject CALC --coverage_only True
    # python Mutation_Analysis.py --subject CALC --mutation_only True --running_mutants False
    main()
