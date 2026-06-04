import os
import re
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from FUZZ_TOOL_SELECTION.utils.ms_score_utils import _load_profiles_from_run, _build_global_matrix, \
    select_mutants_global, \
    _metrics_for_tool


def mutation_analysis_run(subject_program: str, run_id: int = 1):
    SUBJECT = subject_program.upper()
    run_folder = f"mutants_profile_run_{run_id}"

    base_dir = f"MUT_KILLING_PROFILE/{SUBJECT}/main_mut_killing_profiles"
    run_dir = os.path.join(base_dir, run_folder)

    result_dir = f"FUZZ_TOOL_SELECTION/result/{SUBJECT}/run_{run_id}"
    os.makedirs(result_dir, exist_ok=True)

    output_csv = os.path.join(result_dir, "mutation_metrics.csv")
    selected_indices_out = os.path.join(result_dir, "selected_mutant_indices.txt")
    global_report_dir = os.path.join(result_dir, "global_report")

    print(f"\n====================  MUTATION ANALYSIS → {SUBJECT} (RUN {run_id}) ====================")
    print(f"[PATH] run_dir = {run_dir}")
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(
            f"Mutation profile run folder not found: {run_dir}. "
            "Run Step 3 with --running_mutants true before Step 5."
        )

    # --- Load all profiles from this run folder ---
    profiles_by_tool, tool_order, M = _load_profiles_from_run(run_dir)

    # --- Build global matrix and apply filter ---
    global_mat = _build_global_matrix(profiles_by_tool)
    keep_mask, after_band = select_mutants_global(
        global_mat,
        min_rate=0.00,
        max_rate=0.5,
        drop_never=True,
        drop_always=True,
        dedup=True,
        subsumption=True
    )
    selected_idx = np.flatnonzero(keep_mask)
    np.savetxt(selected_indices_out, selected_idx, fmt="%d")

    print(f"[INFO] Selected {len(selected_idx)} / {M} mutants after filtering.")
    if len(selected_idx) == 0:
        print(
            "[WARN] No informative mutants remained after filtering. "
            "Mutation metrics will be zero; check that Step 3 profiles contain non-zero kills."
        )

    # --- Write global report ---
    os.makedirs(global_report_dir, exist_ok=True)
    with open(os.path.join(global_report_dir, "global_filter_report.txt"), "w") as f:
        rates = global_mat.mean(axis =0)

        # === Basic statistics ===
        f.write(f"M_total: {M}\n")  # total number of mutants before filtering
        f.write(f"selected_after_band: {after_band}\n")  # mutants kept after kill-rate banding
        f.write(f"selected_final: {len(selected_idx)}\n")  # final mutants after all filters

        # === Drop statistics ===
        dropped_never = int(np.count_nonzero(rates == 0.0))  # mutants never killed
        dropped_always = int(np.count_nonzero(rates == 1.0))  # mutants always killed
        dropped_band = int(M - after_band)  # total dropped after rate band filtering

        f.write(f"dropped_never_exact: {dropped_never}\n")
        f.write(f"dropped_always_exact: {dropped_always}\n")
        f.write(f"dropped_within_band: {dropped_band}\n")

        # Optional: add percentage summary for clarity
        f.write("\n--- Percentage summary ---\n")
        f.write(f"Equivalent (never killed): {100 * dropped_never / M:.2f}%\n")
        f.write(f"Trivial (always killed): {100 * dropped_always / M:.2f}%\n")
        f.write(f"Selected informative mutants: {100 * len(selected_idx) / M:.2f}%\n")

    # --- MS SCORE BY EACH TOOL ---
    rows = []
    for tool in tool_order:
        X_tool = np.vstack(profiles_by_tool[tool]).astype(bool) # [F,T,F,T,T]
        # skip_all_ones=true, if we want to remove test cases kill all mutants from the filtered mutants
        m = _metrics_for_tool(X_tool, keep_mask, ki_threshold=1,skip_all_ones =False)

        rows.append({
            "Tool": tool,
            "Tests": m["tests"],
            "Mutants_Selected": m["mutants_selected"],
            "MS": m["MS"],
            "KI": m["KI"],
            "SKI": m["SKI"],
        })

    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"[OK] Wrote mutation metrics to {output_csv}")

    return rows, tool_order, keep_mask


# ============================================================
#   PARALLEL EXECUTION FOR ALL RUNS
# ============================================================
def natural_run_key(run_name: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", run_name)]


def mutation_analysis_all_runs(subject_program: str,
                               run_limit: int | None = None,
                               parallel: bool = False):
    base_dir = f"MUT_KILLING_PROFILE/{subject_program.upper()}/main_mut_killing_profiles"
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(
            f"Mutation profile root not found: {base_dir}. "
            "Run Step 3 mutation killing before Step 5."
        )

    run_folders = sorted(
        [f for f in os.listdir(base_dir) if f.startswith("mutants_profile_run_")],
        key=natural_run_key,
    )
    if run_limit is not None:
        run_folders = run_folders[:run_limit]
    if not run_folders:
        raise RuntimeError(f"No mutants_profile_run_<N> folders found under {base_dir}.")

    run_ids = [int(f.split("_")[-1]) for f in run_folders]

    if parallel:
        import multiprocessing
        max_workers = min(len(run_ids), multiprocessing.cpu_count())
        print(f"[INFO] Using up to {max_workers} cores for parallel mutation-score runs.")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(mutation_analysis_run, subject_program, rid): rid for rid in run_ids}
            for f in as_completed(futures):
                rid = futures[f]
                try:
                    f.result()
                    print(f"[DONE] Run {rid} completed.")
                except Exception as e:
                    print(f"[FAIL] Run {rid} failed: {e}")
    else:
        print("[INFO] Running mutation-score runs sequentially. Use --parallel true after smoke testing if desired.")
        for rid in run_ids:
            mutation_analysis_run(subject_program, rid)
            print(f"[DONE] Run {rid} completed.")

    print("\nAll mutation score runs completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute per-generator mutation score metrics from mutation killing profiles.")
    parser.add_argument("--subject", type=str, default="karatejs", help="Subject/SUT name, e.g., karatejs, calc, rhino.")
    parser.add_argument("--runs", type=int, default=None, help="Limit to the first N mutation profile runs for smoke testing.")
    parser.add_argument("--parallel", type=lambda x: x.lower() == "true", default=False,
                        help="Process runs in parallel. Keep false for first smoke tests.")
    args = parser.parse_args()

    mutation_analysis_all_runs(args.subject, run_limit=args.runs, parallel=args.parallel)
