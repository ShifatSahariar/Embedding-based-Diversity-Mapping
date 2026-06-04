import os
from pathlib import Path

import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

PRIORITIZATION_ROOT = Path(__file__).resolve().parents[1]


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
def aggregate_auc_all_suts_and_save(base_dir=None, subjects=None):
    """
    Aggregates AUC across all SUTs (10 runs per SUT) and saves:

    - One CSV per SUT with:
        SpreadEx_mean_AUC, Random_mean_AUC, Mean_diff, values list

    - One GLOBAL CSV summarizing across all 50 experiments:
        SpreadEx_mean_AUC, Random_mean_AUC, Mean_diff,
        Wilcoxon, p_greater, Cliff's delta
    """
    if base_dir is None:
        base_dir = PRIORITIZATION_ROOT / "ALL_SUT_RESULTS"
    base_dir = Path(base_dir)

    if not base_dir.is_dir():
        raise FileNotFoundError(
            f"Phase 2 result folder not found: {base_dir}. "
            "Run Step 1 input prioritization before aggregating AUC results."
        )

    if subjects:
        sut_names = [subject.upper() for subject in subjects]
    else:
        sut_names = [
            d.name for d in base_dir.iterdir()
            if d.is_dir() and d.name not in ["AUC_AGGREGATED"]
        ]

    out_dir = base_dir / "AUC_AGGREGATED"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_spreadex_auc = []
    all_random_auc = []

    per_sut_summary = {}

    # ==========================================================
    # Process each SUT
    # ==========================================================
    for sut in sut_names:
        sut_dir = base_dir / sut
        if not sut_dir.is_dir():
            print(f"[WARN] Skipping missing SUT folder: {sut_dir}")
            continue

        run_folders = []
        for tool_path in sut_dir.iterdir():
            if tool_path.is_dir():
                run_folders.extend([
                    x for x in tool_path.iterdir()
                    if x.is_dir() and x.name.startswith("run_")
                ])

        spreadex_list = []
        random_list = []

        # Load each run’s AUC summary
        for run_path in run_folders:
            auc_file = run_path / "AUC_Summary.csv"
            if not auc_file.exists():
                continue

            df = pd.read_csv(auc_file)
            spreadex_rows = df[df["Approach"].str.contains("SpreadEx", na=False)]["Normalized_AUC"]
            random_rows = df[df["Approach"] == "Random"]["Normalized_AUC"]
            if spreadex_rows.empty or random_rows.empty:
                print(f"[WARN] Skipping incomplete AUC summary: {auc_file}")
                continue

            spreadex_auc = float(spreadex_rows.iloc[0])
            random_auc = float(random_rows.iloc[0])

            spreadex_list.append(spreadex_auc)
            random_list.append(random_auc)

            all_spreadex_auc.append(spreadex_auc)
            all_random_auc.append(random_auc)

        if not spreadex_list:
            print(f"[WARN] No AUC_Summary.csv files found for {sut}; skipping.")
            continue

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

        sut_csv_path = out_dir / f"{sut}_AUC.csv"
        df_sut.to_csv(sut_csv_path, index=False)
        print(f"[SAVED] Per-SUT AUC → {sut_csv_path}")

    if not all_spreadex_auc:
        raise RuntimeError(
            f"No AUC summaries found under {base_dir}. "
            "Run Step 1 input prioritization first."
        )

    # ==========================================================
    # Global Stats (All 50 experiments)
    # ==========================================================
    all_spreadex_auc = np.array(all_spreadex_auc)
    all_random_auc = np.array(all_random_auc)

    try:
        W, p_greater = wilcoxon(all_spreadex_auc, all_random_auc, alternative="greater")
    except ValueError as exc:
        print(f"[WARN] Wilcoxon could not be computed: {exc}")
        W, p_greater = np.nan, np.nan
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

    global_csv_path = out_dir / "GLOBAL_AUC_SUMMARY.csv"
    df_global.to_csv(global_csv_path, index=False)
    print(f"[SAVED] GLOBAL AUC summary → {global_csv_path}")

    return per_sut_summary, global_summary

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate Phase 2 AUC summaries across SUTs.")
    parser.add_argument(
        "--base-dir",
        type=str,
        default=str(PRIORITIZATION_ROOT / "ALL_SUT_RESULTS"),
        help="Phase 2 result root containing per-SUT folders.",
    )
    parser.add_argument(
        "--subjects",
        type=str,
        default=None,
        help="Optional comma-separated SUT list, e.g., KARATEJS,CALC. Omit to aggregate all available SUTs.",
    )
    args = parser.parse_args()

    subject_list = None
    if args.subjects:
        subject_list = [part.strip() for part in args.subjects.split(",") if part.strip()]

    aggregate_auc_all_suts_and_save(base_dir=args.base_dir, subjects=subject_list)
