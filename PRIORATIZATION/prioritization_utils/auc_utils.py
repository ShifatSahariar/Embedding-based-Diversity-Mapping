import os

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


def plot_auc_curves(mean_std, normalized_auc, save_dir="plots"):
    """
    Plot Mutation Score vs. Budget across all approaches.
    Two plots:
        1. Clean
        2. Shaded (±1 std)
    Legend automatically includes Normalized AUC.
    """

    os.makedirs(save_dir, exist_ok=True)

    plt.rcParams.update({
        "font.size": 12,
        "axes.labelsize": 13,
        "axes.titlesize": 14,
        "legend.fontsize": 11,
        "lines.linewidth": 2.2,
        "axes.grid": True,
        "grid.alpha": 0.3,
    })

    def _plot(ax, show_shading=False):
        for approach, df in mean_std.items():

            label = f"{approach} (nAUC={normalized_auc[approach]:.3f})"

            ax.plot(
                df["Budget"], df["Mean_MS"],
                marker="o", markersize=6,
                label=label,
            )

            if show_shading:
                lower = np.maximum(0, df["Mean_MS"] - df["Std_MS"])
                upper = np.minimum(1, df["Mean_MS"] + df["Std_MS"])
                ax.fill_between(df["Budget"], lower, upper, alpha=0.2)

        ax.set_xlabel("Budget (Number of Selected Inputs)")
        ax.set_ylabel("Mean Mutation Score")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower right", frameon=False)
        ax.grid(True, linestyle="--", alpha=0.25)

    # Clean plot
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    _plot(ax1, show_shading=False)
    ax1.set_title("MS vs Budget — Clean Curve")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "AUC_Clean.png"), dpi=300)

    # Shaded plot
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    _plot(ax2, show_shading=True)
    ax2.set_title("MS vs Budget — Variability Shading")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "AUC_Shaded.png"), dpi=300)

    print(f"✅ Plots saved in {os.path.abspath(save_dir)}")




def aggregate_results(results, save_dir="AUC_TABLES"):
    """
    Aggregate mutation scores and save results per approach (mean & std per budget).
    Computes:
      - AUC (raw)
      - Normalized AUC (AUC / max_budget)
    Returns:
      mean_std: dict[approach → DataFrame]
      normalized_auc_values: dict[approach → float]
    """

    os.makedirs(save_dir, exist_ok=True)

    mean_std = {}
    auc_values = {}
    normalized_auc_values = {}

    # ==========================================================
    # Step 1 — Compute Mean and Std per approach & budget
    # ==========================================================
    for approach, budget_dict in results.items():
        budgets, means, stds = [], [], []

        for budget, scores in sorted(budget_dict.items()):
            if not scores:
                continue

            budgets.append(budget)
            means.append(np.mean(scores))
            stds.append(np.std(scores))

        df = pd.DataFrame({
            "Budget": budgets,
            "Mean_MS": np.round(means, 6),
            "Std_MS": np.round(stds, 6)
        })
        mean_std[approach] = df

        safe_name = approach.replace(" ", "_").replace("(", "").replace(")", "")
        csv_path = os.path.join(save_dir, f"{safe_name}_AUC_Table.csv")
        df.to_csv(csv_path, index=False)
        print(f"[SAVED] {csv_path}")

        # ==========================================================
        # Step 2 — Compute AUC and Normalized AUC
        # ==========================================================
        x = df["Budget"].values
        y = df["Mean_MS"].values

        auc_raw = np.trapz(y, x)
        auc_values[approach] = auc_raw

        max_budget = x[-1]
        auc_normalized = auc_raw / max_budget  # max area = max_budget × 1.0
        normalized_auc_values[approach] = auc_normalized

    # ==========================================================
    # Step 3 — Save AUC Summary
    # ==========================================================
    auc_df = pd.DataFrame({
        "Approach": list(auc_values.keys()),
        "AUC": list(auc_values.values()),
        "Normalized_AUC": list(normalized_auc_values.values())
    })
    auc_path = os.path.join(save_dir, "AUC_Summary.csv")
    auc_df.to_csv(auc_path, index=False)
    print(f"[SAVED] AUC summary → {auc_path}")

    return mean_std, normalized_auc_values

