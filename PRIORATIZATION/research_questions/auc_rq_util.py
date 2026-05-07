import os
import pandas as pd
import numpy as np
from scipy.stats import wilcoxon


# ------------------------------------------------------------
# Cliff's Delta Utility
# ------------------------------------------------------------
def cliffs_delta(x, y):
    n = len(x);
    m = len(y)
    greater = lesser = 0
    for a in x:
        for b in y:
            if a > b:
                greater += 1
            elif a < b:
                lesser += 1
    return (greater - lesser) / (n * m)


# ------------------------------------------------------------
# Main Aggregation + CSV saving function
# ------------------------------------------------------------
def aggregate_auc_all_suts_and_save(base_dir="../ALL_SUT_RESULTS"):
    """
    Aggregates AUC across all SUTs (10 runs per SUT) and saves:

    - One CSV per SUT with:
        SpreadEx_mean_AUC, Random_mean_AUC, Mean_diff, values list

    - One GLOBAL CSV summarizing across all 50 experiments:
        SpreadEx_mean_AUC, Random_mean_AUC, Mean_diff,
        Wilcoxon, p_greater, Cliff's delta
    """

    sut_names = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
           and d not in ["AUC_AGGREGATED"]  # ignore output folder
    ]

    out_dir = os.path.join(base_dir, "AUC_AGGREGATED")
    os.makedirs(out_dir, exist_ok=True)

    all_spreadex_auc = []
    all_random_auc = []

    per_sut_summary = {}

    # ==========================================================
    # Process each SUT
    # ==========================================================
    for sut in sut_names:
        sut_dir = os.path.join(base_dir, sut)

        run_folders = []
        for tool_dir in os.listdir(sut_dir):
            tool_path = os.path.join(sut_dir, tool_dir)
            if os.path.isdir(tool_path):
                run_folders.extend([
                    os.path.join(tool_path, x)
                    for x in os.listdir(tool_path)
                    if x.startswith("run_")
                ])

        spreadex_list = []
        random_list = []

        # Load each run’s AUC summary
        for run_path in run_folders:
            auc_file = os.path.join(run_path, "AUC_Summary.csv")
            if not os.path.exists(auc_file):
                continue

            df = pd.read_csv(auc_file)
            spreadex_auc = float(df[df["Approach"].str.contains("SpreadEx")]["Normalized_AUC"])
            random_auc = float(df[df["Approach"] == "Random"]["Normalized_AUC"])

            spreadex_list.append(spreadex_auc)
            random_list.append(random_auc)

            all_spreadex_auc.append(spreadex_auc)
            all_random_auc.append(random_auc)

        # Per-SUT stats
        per_sut_stats = {
            "SUT": sut,
            "SpreadEx_mean_AUC": float(np.mean(spreadex_list)),
            "Random_mean_AUC": float(np.mean(random_list)),
            "Mean_diff": float(np.mean(spreadex_list) - np.mean(random_list)),
            "SpreadEx_runs": spreadex_list,
            "Random_runs": random_list
        }

        per_sut_summary[sut] = per_sut_stats

        # Save per-SUT CSV
        df_sut = pd.DataFrame({
            "Metric": ["SpreadEx_mean_AUC", "Random_mean_AUC", "Mean_diff"],
            "Value": [
                per_sut_stats["SpreadEx_mean_AUC"],
                per_sut_stats["Random_mean_AUC"],
                per_sut_stats["Mean_diff"]
            ]
        })

        sut_csv_path = os.path.join(out_dir, f"{sut}_AUC.csv")
        df_sut.to_csv(sut_csv_path, index=False)
        print(f"[SAVED] Per-SUT AUC → {sut_csv_path}")

    # ==========================================================
    # Global Stats (All 50 experiments)
    # ==========================================================
    all_spreadex_auc = np.array(all_spreadex_auc)
    all_random_auc = np.array(all_random_auc)

    W, p_greater = wilcoxon(all_spreadex_auc, all_random_auc, alternative="greater")
    cd = cliffs_delta(all_spreadex_auc, all_random_auc)

    global_summary = {
        "SpreadEx_mean_AUC": float(np.mean(all_spreadex_auc)),
        "Random_mean_AUC": float(np.mean(all_random_auc)),
        "Mean_diff": float(np.mean(all_spreadex_auc - all_random_auc)),
        "Wilcoxon_W": float(W),
        "p_greater": float(p_greater),
        "Cliffs_delta": float(cd)
    }

    # Save GLOBAL summary CSV
    df_global = pd.DataFrame({
        "Metric": list(global_summary.keys()),
        "Value": list(global_summary.values())
    })

    global_csv_path = os.path.join(out_dir, "GLOBAL_AUC_SUMMARY.csv")
    df_global.to_csv(global_csv_path, index=False)
    print(f"[SAVED] GLOBAL AUC summary → {global_csv_path}")

    return per_sut_summary, global_summary


per_sut, global_stats = aggregate_auc_all_suts_and_save()
