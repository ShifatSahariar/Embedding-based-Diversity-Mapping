import os
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
def mutation_analysis_all_runs(subject_program: str):
    base_dir = f"MUT_KILLING_PROFILE/{subject_program.upper()}/main_mut_killing_profiles"
    run_folders = sorted([f for f in os.listdir(base_dir) if f.startswith("mutants_profile_run_")])
    run_ids = [int(f.split("_")[-1]) for f in run_folders]

    import multiprocessing
    max_workers = min(len(run_ids), multiprocessing.cpu_count())
    print(f"[INFO] Using up to {max_workers} cores for parallel mutation runs.")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(mutation_analysis_run, subject_program, rid): rid for rid in run_ids}
        for f in as_completed(futures):
            rid = futures[f]
            try:
                result = f.result()
                print(f"[DONE]  {result}")
            except Exception as e:
                print(f"[FAIL] Run {rid} failed: {e}")

    print("\n  All mutation analysis runs completed in parallel.")


if __name__ == "__main__":
    mutation_analysis_all_runs("GRAALJS") # RHINO BASIC CALC NASHORN GRAALJS KARATEJS
