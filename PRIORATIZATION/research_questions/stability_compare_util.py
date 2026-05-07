from scipy.stats import norm
import os
import pandas as pd
import numpy as np
def compute_rq4_metrics(selection_sequences,
                        filtered_profiles_dict,
                        results,
                        budgets,
                        subject,
                        run_name):
    """
    Compute RQ4 metrics per budget:
        - STD_B  : instability of Random
        - PEG_B  : Prob(Random >= SpreadEx) using Gaussian approximation
        - PMR_B  : Prob(Random > SpreadEx) empirical misranking probability
        - PKHM_B : Prob(Random <= half of its mean)
    """

    rq4 = {
        "STD": {},      # budget → std(random)
        "PEG": {},      # budget → Gaussian PEG
        "PMR": {},      # budget → empirical misranking probability
        "PKHM": {}      # budget → random kills half its mean
    }

    # Step 1: Extract SpreadEx + Random methods
    spreadex_method = None
    for m in results.keys():
        if "Spread" in m and "Ex" in m:
            spreadex_method = m
    if spreadex_method is None:
        raise ValueError("SpreadEx method not found!")

    random_method = "Random"
    if random_method not in results:
        raise ValueError("Random method missing.")

    # Step 2: Compute metrics per budget
    for B in budgets:

        # ============================================
        # A) STD — stability of random
        # ============================================
        random_scores = np.array(results[random_method][B])
        rnd_ms = float(np.mean(random_scores))
        rnd_std = float(np.std(random_scores))
        rq4["STD"][B] = rnd_std

        # Deterministic SpreadEx value
        our_ms = float(np.mean(results[spreadex_method][B]))
        # ============================================
        # B) PEG — Gaussian probability Random ≥ SpreadEx
        # ============================================
        #if rnd_std > 0:
        peg_gaussian = 1 - norm.cdf(our_ms, loc=rnd_ms, scale=rnd_std)
        # else:
        #     peg_gaussian =  0.0 #float(our_ms <= rnd_ms)
        rq4["PEG"][B] = float(peg_gaussian)
        # ============================================
        # C) PMR — Empirical probability Random > SpreadEx
        # ============================================
        pmr = np.mean(random_scores > our_ms)
        rq4["PMR"][B] = float(pmr)
        # ============================================
        # D) PKHM — Prob Random ≤ half of its mean
        # ============================================
        # if rnd_std == 0:
        #     # Degenerate case
        #     rq4["PKHM"][B] = 1.0 if rnd_ms <= 0.5 * rnd_ms else 0.0
        # else:
        half_point = 0.5 * rnd_ms
        pkhm = norm.cdf(half_point, loc=rnd_ms, scale=rnd_std)
        rq4["PKHM"][B] = float(pkhm)

    return rq4

def save_rq4_table(rq4_dict, subject_program, run_name):
    """
    Save RQ4 metrics (STD, PEG, PMR, PKHM) into a long-format CSV:
       Metric | B | Value
    """

    import csv, os
    out_dir = f"ALL_SUT_RESULTS/{subject_program}/rq4_tables"
    os.makedirs(out_dir, exist_ok=True)
    path = f"{out_dir}/RQ4_{run_name}.csv"

    rows = [["Metric", "B", "Value"]]

    # -----------------------------
    # Save STD(B)
    # -----------------------------
    for B, v in rq4_dict["STD"].items():
        rows.append(["STD", B, v])

    # -----------------------------
    # Save PEG(B)
    # -----------------------------
    for B, v in rq4_dict["PEG"].items():
        rows.append(["PEG", B, v])

    # -----------------------------
    # Save PMR(B)
    # -----------------------------
    if "PMR" in rq4_dict:
        for B, v in rq4_dict["PMR"].items():
            rows.append(["PMR", B, v])

    # -----------------------------
    # Save PKHM(B)
    # -----------------------------
    for B, v in rq4_dict["PKHM"].items():
        rows.append(["PKHM", B, v])

    # -----------------------------
    # Write CSV file
    # -----------------------------
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    print(f"[SAVED] RQ4 table → {path}")




def aggregate_rq4_for_sut(sut_name, base_dir="../ALL_SUT_RESULTS"):
    """
    Aggregates the 10 independent RQ4 CSV files for a given SUT.

    Input:
        ALL_SUT_RESULTS/{sut_name}/rq4_tables/RQ4_runX.csv

    Output:
        ALL_SUT_RESULTS/{sut_name}/rq4_summary/RQ4_GLOBAL_{sut_name}.csv

    Each RQ4_runX.csv contains rows:
        Metric,B,Value
        STD,5, ...
        PEG,5, ...
        PKHM,5, ...
        ...
    """

    sut_dir = os.path.join(base_dir, sut_name, "rq4_tables")
    out_dir = os.path.join(base_dir, sut_name, "rq4_summary")
    os.makedirs(out_dir, exist_ok=True)

    # ---------------------------
    # 1. Collect all experiment files
    # ---------------------------
    csv_files = [
        os.path.join(sut_dir, f) for f in os.listdir(sut_dir)
        if f.endswith(".csv")
    ]

    if len(csv_files) == 0:
        print(f"[WARN] No RQ4 CSV files found for SUT {sut_name}")
        return

    print(f"[INFO] Aggregating {len(csv_files)} RQ4 experiment files for {sut_name}")

    # ---------------------------
    # 2. Load all experiment files
    # ---------------------------
    dfs = [pd.read_csv(f) for f in csv_files]

    # Extract metrics and budgets from first file
    metric_budget_pairs = dfs[0][["Metric", "B"]].values.tolist()

    aggregated_rows = []

    # ---------------------------
    # 3. Compute mean and std for each (Metric,B) across 10 runs
    # ---------------------------
    for metric, B in metric_budget_pairs:

        values_per_experiment = []

        for df in dfs:
            row = df[(df["Metric"] == metric) & (df["B"] == B)]
            value = float(row["Value"].values[0])
            values_per_experiment.append(value)

        aggregated_rows.append([
            metric,
            B,
            float(np.mean(values_per_experiment)),
            float(np.std(values_per_experiment))
        ])

    # ---------------------------
    # 4. Save final aggregated table
    # ---------------------------
    out_df = pd.DataFrame(
        aggregated_rows,
        columns=["Metric", "Budget", "Mean", "Std"]
    )

    out_path = os.path.join(out_dir, f"RQ4_GLOBAL_{sut_name}.csv")
    out_df.to_csv(out_path, index=False)

    print(f"[SAVED] RQ4 summary → {out_path}")

# aggregate_rq4_for_sut("CALC")
# aggregate_rq4_for_sut("BASIC")
# aggregate_rq4_for_sut("RHINO")
# aggregate_rq4_for_sut("NASHORN")
# aggregate_rq4_for_sut("GRAALJS")
# aggregate_rq4_for_sut("KARATEJS")