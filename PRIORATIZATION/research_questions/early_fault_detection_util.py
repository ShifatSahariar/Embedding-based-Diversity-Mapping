import os
import numpy as np
import csv
import pandas as pd

def save_rq3_table(metrics, subject_program, run_name):
    """
    Save RQ3 table in the simplified 2-column format:
    Metrics | SpreadEx | Random
    """

    # Identify method names
    spreadex = None
    random_m = None

    # detect matching method names
    for m in metrics.keys():
        if "Spread" in m and "Ex" in m:
            spreadex = m
        if m == "Random":
            random_m = m

    if spreadex is None or random_m is None:
        raise ValueError("SpreadEx or Random method not found in metrics!")

    # Extract values (mean only, ignoring std for RQ3)
    rows = [
        ["Metrics", "SpreadEx", "Random"],
        ["T2K",
            metrics[spreadex]["T2K_mean"],
            metrics[random_m]["T2K_mean"]],
        ["MS_5",
            metrics[spreadex]["MS_5"],
            metrics[random_m]["MS_5"]],
        ["MS_10",
            metrics[spreadex]["MS_10"],
            metrics[random_m]["MS_10"]],
        ["MS_20",
            metrics[spreadex]["MS_20"],
            metrics[random_m]["MS_20"]],
        #
        # ["KP_5",
        #     metrics[spreadex]["KP_5"],
        #     metrics[random_m]["KP_5"]],
        # ["KP_10",
        #     metrics[spreadex]["KP_10"],
        #     metrics[random_m]["KP_10"]],
        # ["KP_20",
        #     metrics[spreadex]["KP_20"],
        #     metrics[random_m]["KP_20"]],
    ]

    save_dir = f"ALL_SUT_RESULTS/{subject_program}/rq3_tables"
    os.makedirs(save_dir, exist_ok=True)

    path = f"{save_dir}/RQ3_{run_name}.csv"

    import csv
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"[SAVED] RQ3 table → {path}")


def compute_rq3_metrics(selection_sequences,
                        filtered_profiles_dict,
                        results,
                        budgets,
                        subject_program,
                        run_name):
    """
    Compute all metrics required for RQ3 (per experiment per SUT):

        - AUC_mean, AUC_std        (Effectiveness over full budget range)
        - MS_B, MS_B_std           (Mutation Score at budget B)
        - KP_B, KP_B_std           (Killing Power at budget B)
        - T2K_mean, T2K_std        (Tests to Kill mutants)

    Inputs:
        selection_sequences[method][run_id][budget] = ordered list of selected inputs
        filtered_profiles_dict[input_id]            = boolean kill vector (post-filtering)
        results[method][budget]                    = list of mutation scores (1 for deterministic, 50 for random)
        budgets                                     = list like [5,10,20,40,80]

    Returns:
        metrics[method_name][metric_name] = value (float)
        or (mean/std for random methods)
    """

    metrics = {}  # method → metric_name → value

    # Total number of mutants after filtering
    num_mutants = len(next(iter(filtered_profiles_dict.values())))

    # =============================================================
    #   MAIN LOOP — PROCESS EACH TEST SELECTION METHOD
    # =============================================================
    for method_name, runs in selection_sequences.items():
        metrics[method_name] = {}

        # ====================================================================
        # 1. AUC (Area Under Mutation Score Curve)
        # ====================================================================
        # For deterministic methods:
        #     results[method][b] = [score, score, ..., score] repeated 50 times
        # For random methods:
        #     results[method][b] = [score_run0, score_run1, ... score_run49]
        #
        # We compute AUC per-run, then summarize with mean/std.

        # Collect mutation score values for all budgets
        auc_values = []
        for B in budgets:
            auc_values.append(results[method_name][B])  # list of size 1 or 50

        # Transpose → rows = runs, columns = budgets
        # Example:
        #   auc_per_run[0] = [MS_5_run0, MS_10_run0, ...]
        auc_per_run = list(zip(*auc_values))

        # AUC per run is the **mean of the curve values across budgets**
        # (You already pre-computed the monotonic MS curve per budget.)
        auc_run_scores = [np.mean(run) for run in auc_per_run]

        metrics[method_name]["AUC_mean"] = float(np.mean(auc_run_scores))
        metrics[method_name]["AUC_std"]  = float(np.std(auc_run_scores))

        # ====================================================================
        # 2. Compute per-budget metrics (MS_B, KP_B)
        # ====================================================================
        #
        #   MS(B): Mutation Score at budget B
        #          MS(B) = |Union of kills by first B tests| / M
        #
        #   KP(B): Killing Power at budget B
        #          KP(B) = (1/B) * Σ_i |kills(test_i)|   for i=1..B
        #
        # Deterministic → only one run
        # Random        → 50 runs, so we collect distributions then mean/std

        for B in budgets:

            ms_values = []   # MS_B of all runs
            kp_values = []   # KP_B of all runs

            for run_id, b_map in runs.items():

                # Skip if run does not contain this budget (should not happen)
                if B not in b_map:
                    continue

                # Ordered selected inputs for this budget
                ordered_inputs = b_map[B]

                # --- Compute MS_B ---
                kill_union = np.zeros(num_mutants, dtype=bool)
                kills_per_input = []

                for inp in ordered_inputs[:B]:
                    kill_vec = filtered_profiles_dict[inp]

                    # Union across inputs → whether mutant killed at least once
                    kill_union = np.logical_or(kill_union, kill_vec)

                    # Count number of mutants killed by this input
                    kills_per_input.append(kill_vec.sum())

                # MS_B = fraction of mutants killed by the union of first B tests
                MS_B = kill_union.mean()

                # KP_B = mean kills per selected input
                KP_B = np.mean(kills_per_input)

                ms_values.append(MS_B)
                kp_values.append(KP_B)

            # Store mean/std across all runs
            metrics[method_name][f"MS_{B}"] = float(np.mean(ms_values))
            metrics[method_name][f"MS_{B}_std"] = float(np.std(ms_values))

            metrics[method_name][f"KP_{B}"] = float(np.mean(kp_values))
            metrics[method_name][f"KP_{B}_std"] = float(np.std(kp_values))

        # ====================================================================
        # 3. Compute T2K — Tests To Kill each mutant
        # ====================================================================
        #
        # For each run:
        #    T2K(m) = index of FIRST test that kills mutant m
        #    If mutant never killed → T2K(m) = ∞
        #
        #    T2K_run = mean over all mutants m
        #
        # Then average T2K_run over 1 (det) or 50 (random) runs.

        t2k_values_runs = []

        for run_id, b_map in runs.items():

            # Use the LARGEST budget (contains full kill info)
            Bmax = max(budgets)
            ordered_inputs = b_map[Bmax]

            # Initialize T2K(m) = ∞
            t2k_per_mutant = np.full(num_mutants, np.inf)

            # For each mutant, scan the ordered inputs
            for m in range(num_mutants):
                for idx, inp in enumerate(ordered_inputs):
                    if filtered_profiles_dict[inp][m] == 1:
                        t2k_per_mutant[m] = idx + 1  # tests are 1-indexed
                        break

            # T2K_run = mean over finite values
            finite_kills = t2k_per_mutant[np.isfinite(t2k_per_mutant)]
            if len(finite_kills) > 0:
                t2k_values_runs.append(np.mean(finite_kills))
            else:
                t2k_values_runs.append(np.inf)

        metrics[method_name]["T2K_mean"] = float(np.mean(t2k_values_runs))
        metrics[method_name]["T2K_std"]  = float(np.std(t2k_values_runs))

    # End: all methods processed
    return metrics





def aggregate_rq3_for_sut(sut_name, base_dir="../ALL_SUT_RESULTS"):
    """
    Aggregates the 10 independent RQ3 CSV files for a given SUT.

    Input folder:
        ALL_SUT_RESULTS/{sut_name}/rq3_tables/RQ3_runX.csv

    Output file:
        ALL_SUT_RESULTS/{sut_name}/rq3_summary/RQ3_GLOBAL_{sut_name}.csv
    """

    sut_dir = os.path.join(base_dir, sut_name, "rq3_tables")
    out_dir = os.path.join(base_dir, sut_name, "rq3_summary")
    os.makedirs(out_dir, exist_ok=True)

    # collect all CSV filenames
    csv_files = [
        os.path.join(sut_dir, f) for f in os.listdir(sut_dir)
        if f.endswith(".csv")
    ]

    if len(csv_files) == 0:
        print(f"[WARN] No RQ3 CSV files found for SUT {sut_name}")
        return

    print(f"[INFO] Aggregating {len(csv_files)} RQ3 experiment files for {sut_name}")

    # Combine all dataframes
    dfs = [pd.read_csv(f) for f in csv_files]

    # All dfs have format:
    # Metrics, SpreadEx, Random
    metric_names = dfs[0]["Metrics"].values

    # Prepare final aggregated rows
    aggregated_rows = []

    for metric in metric_names:
        spreadex_values = []
        random_values = []

        for df in dfs:
            row = df[df["Metrics"] == metric]
            spreadex_values.append(float(row["SpreadEx"].values[0]))
            random_values.append(float(row["Random"].values[0]))

        aggregated_rows.append([
            metric,
            np.mean(spreadex_values), np.std(spreadex_values),
            np.mean(random_values), np.std(random_values)
        ])

    # Final DataFrame
    out_df = pd.DataFrame(
        aggregated_rows,
        columns=["Metrics",
                 "SpreadEx_mean", "SpreadEx_std",
                 "Random_mean", "Random_std"]
    )

    out_path = os.path.join(out_dir, f"RQ3_GLOBAL_{sut_name}.csv")
    out_df.to_csv(out_path, index=False)

    print(f"[SAVED] Aggregated RQ3 summary → {out_path}")


# aggregate_rq3_for_sut("CALC")
# aggregate_rq3_for_sut("BASIC")
# aggregate_rq3_for_sut("RHINO")
# aggregate_rq3_for_sut("NASHORN")
# aggregate_rq3_for_sut("GRAALJS")
# aggregate_rq3_for_sut("KARATEJS")
#
