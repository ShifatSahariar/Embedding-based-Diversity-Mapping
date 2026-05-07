#!/usr/bin/env python3
import os, re
from typing import List, Tuple, Optional, Dict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import spearmanr

# -----------------------------
# Helpers
# -----------------------------
def _parse_configuration_column(
    df: pd.DataFrame, config_col: str = "Configuration", overwrite: bool = True
) -> pd.DataFrame:
    """
    Parse a 'Configuration' column like 'OpenAI + K-Means + 100'
    into: Embedding_Model, Cluster_Algo, K
    """
    if config_col not in df.columns:
        return df

    def parse_config(s: str):
        parts = [p.strip() for p in str(s).split("+")]
        emb = parts[0] if len(parts) > 0 else np.nan
        algo = parts[1] if len(parts) > 1 else np.nan
        k = np.nan
        if len(parts) > 2:
            m = re.search(r"\d+", parts[2])
            if m:
                k = int(m.group())
        return pd.Series({
            "Embedding_Model": emb,
            "Cluster_Algo": algo,
            "K": k
        })

    parsed = df[config_col].apply(parse_config)
    df = pd.concat([df, parsed], axis=1)
    df["K"] = pd.to_numeric(df["K"], errors="coerce")
    return df


def _ensure_numeric(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").to_numpy()


def _sorted_categories_by_stat(df: pd.DataFrame, category: str, value_col: str,
                               stat: str = "median", ascending: bool = True) -> List:
    """Return categories sorted by statistic of value_col within each category."""
    sub = df.dropna(subset=[category, value_col])
    if sub.empty:
        return []

    def stat_func(x):
        if stat == "mean": return np.nanmean(x)
        if stat == "q1": return np.nanquantile(x, 0.25)
        if stat == "q3": return np.nanquantile(x, 0.75)
        if stat == "iqr": return np.nanquantile(x, 0.75) - np.nanquantile(x, 0.25)
        return np.nanmedian(x)

    order = (
        sub.groupby(category)[value_col]
        .apply(stat_func)
        .sort_values(ascending=ascending)
        .index.tolist()
    )
    return order


# -----------------------------
# Plotting functions
# -----------------------------
def make_boxplot_by_category(df, category, value_col,
                             title=None, xlabel=None, ylabel=None,
                             sort_stat="median", ascending=True,
                             out_path=None):
    """Pretty colored boxplots (one per category)."""
    sub = df.dropna(subset=[category, value_col])
    if sub.empty:
        return None

    # Sort categories low → high
    cats = _sorted_categories_by_stat(sub, category, value_col, stat=sort_stat, ascending=ascending)
    if not cats:
        cats = sorted(sub[category].dropna().unique(), key=str)
    groups = [sub.loc[sub[category] == c, value_col].astype(float).values for c in cats]

    # Use pastel colormap for distinction
    cmap = plt.colormaps.get_cmap("tab10")
    colors = [cmap(i % 10) for i in range(len(cats))]

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(max(8, 0.6 * len(cats) + 4), 6))
    bp = plt.boxplot(groups, patch_artist=True, showmeans=True)

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    plt.xticks(range(1, len(cats) + 1), cats, rotation=30, ha="right")
    plt.xlabel(xlabel or category)
    plt.ylabel(ylabel or value_col)
    plt.title(title or f"{value_col} by {category}")
    plt.tight_layout()

    if out_path:
        plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path


def make_scatter_or_hexbin(df, x_col, y_col,
                           title=None, xlabel=None, ylabel=None,
                           out_path=None, hex_threshold=300):
    """Scatter or hexbin with trend line and Spearman correlation."""
    x = _ensure_numeric(df[x_col])
    y = _ensure_numeric(df[y_col])
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    rho = spearmanr(x, y).correlation if n > 1 else np.nan

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(8, 6))
    if n > hex_threshold:
        plt.hexbin(x, y, gridsize=30, cmap="viridis")
        plt.colorbar(label="count")
    else:
        plt.scatter(x, y, c=y, cmap="coolwarm", alpha=0.7, edgecolors="k")

    if n > 1:
        A = np.vstack([x, np.ones_like(x)]).T
        b, a = np.linalg.lstsq(A, y, rcond=None)[0]
        xs = np.linspace(np.min(x), np.max(x), 100)
        ys = b * xs + a
        plt.plot(xs, ys, color="black", linestyle="--", linewidth=1)

    plt.xlabel(xlabel or x_col)
    plt.ylabel(ylabel or y_col)
    plt.title(f"{title or (y_col + ' vs ' + x_col)}\nSpearman ρ={rho:.3f} (n={n})")
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path


# -----------------------------
# Main driver
# -----------------------------
def generate_plots_from_csv(
    csv_path, output_dir,
    correlation_cols=("Coverage–MS"),
    groupings=("Embedding_Model", "Cluster_Algo", "K"),
    sort_stat="median", ascending=True,
    scatter_pairs=(("CHI", "Coverage–MS"),),
    parse_config=True, config_col="Configuration"
):
    """High-level interface: create boxplots and scatter plots."""
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(csv_path)

    if parse_config:
        df = _parse_configuration_column(df, config_col=config_col)

    box_files, scatter_files = [], []

    for val in correlation_cols:
        for cat in groupings:
            if cat in df.columns and val in df.columns:
                path = os.path.join(output_dir, f"{val}_by_{cat}.png")
                make_boxplot_by_category(
                    df, category=cat, value_col=val,
                    title=f"{val} by {cat} (sorted by {sort_stat})",
                    xlabel=cat, ylabel=f"Spearman ρ ({val})",
                    sort_stat=sort_stat, ascending=ascending,
                    out_path=path
                )
                box_files.append(path)

    for (x_col, y_col) in scatter_pairs:
        if x_col in df.columns and y_col in df.columns:
            path = os.path.join(output_dir, f"scatter_{y_col}_vs_{x_col}.png")
            make_scatter_or_hexbin(
                df, x_col=x_col, y_col=y_col,
                title=f"{y_col} vs {x_col}", out_path=path
            )
            scatter_files.append(path)

    return {"boxplots": box_files, "scatters": scatter_files}


def summarize_correlations(
    corr_csv,
    groupings=["K", "Cluster_Algo", "Embedding_Model"],
    corr_cols=["Coverage–MS"],
    output_dir=None
):
    """
    Summarize correlations (median + IQR) grouped by K, Algo, Embedding.
    Automatically parses Configuration column if K/Algo missing.
    Saves CSVs if output_dir is provided.
    Returns dict of DataFrames.
    """
    df = pd.read_csv(corr_csv)

    # Auto-parse configuration if necessary
    if not all(col in df.columns for col in ["K", "Cluster_Algo", "Embedding_Model"]):
        df = _parse_configuration_column(df)

    summaries = {}
    os.makedirs(output_dir or ".", exist_ok=True)

    for group in groupings:
        if group not in df.columns:
            print(f"[WARN] Column '{group}' not found in CSV. Skipping.")
            continue

        rows = []
        for cat, sub in df.groupby(group):
            row = {group: cat}
            for col in corr_cols:
                if col in sub.columns:
                    vals = sub[col].dropna().values
                    if len(vals) > 0:
                        median = np.nanmedian(vals)
                        q1 = np.nanquantile(vals, 0.25)
                        q3 = np.nanquantile(vals, 0.75)
                        iqr = q3 - q1
                        row[f"{col}_median"] = round(median, 3)
                        row[f"{col}_IQR"] = round(iqr, 3)
            rows.append(row)

        df_summary = pd.DataFrame(rows)
        if not df_summary.empty:
            df_summary = df_summary.sort_values(f"{corr_cols[0]}_median", ascending=False)
            summaries[group] = df_summary
            if output_dir:
                out_file = os.path.join(output_dir, f"correlation_summary_by_{group}.csv")
                df_summary.to_csv(out_file, index=False)
                print(f"[INFO] Saved {out_file}")

    return summaries


# -------------------------------------------------
# 3️⃣ Coverage-plateau utils
# -------------------------------------------------
def coverage_plateau_from_tools(
    cov_csv: str,
    tool_cols: list = None,
    threshold: float = 0.005,
    out_path: str = None,
) -> pd.DataFrame:
    """
    Computes coverage plateau using all tool coverage columns.
    Steps:
    1. Parse configuration → extract K if not present.
    2. Compute mean coverage across all tool columns for each configuration.
    3. Aggregate by K → mean coverage vs K.
    4. Compute incremental gain & detect plateau (gain < threshold).
    5. Plot curve with plateau points.
    """

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    df = pd.read_csv(cov_csv)

    # Step 1: Parse Configuration column if needed
    if "K" not in df.columns:
        if "Configuration" in df.columns:
            print("[INFO] 'K' not found — parsing from Configuration column.")
            df = _parse_configuration_column(df)
        else:
            raise KeyError("No 'K' or 'Configuration' column found in coverage CSV.")

    # Step 2: Automatically detect coverage columns if not provided
    if tool_cols is None:
        tool_cols = [
            c for c in df.columns
            if any(k in c.lower() for k in ["fan", "fuzz", "isla", "open_ai"])
        ]
    if not tool_cols:
        raise KeyError("No tool coverage columns detected.")
    print(f"[INFO] Using tool coverage columns: {tool_cols}")

    # Step 3: Compute mean coverage across tools
    df["Mean_Coverage"] = df[tool_cols].mean(axis=1)

    # Step 4: Aggregate mean coverage by K
    df["K"] = pd.to_numeric(df["K"], errors="coerce")
    cov_by_k = df.groupby("K", as_index=False)["Mean_Coverage"].mean().sort_values("K")
    cov_by_k["Gain"] = cov_by_k["Mean_Coverage"].diff()
    cov_by_k["Plateau"] = cov_by_k["Gain"].abs() < threshold

    # Step 5: Plot
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(8, 6))
    plt.plot(cov_by_k["K"], cov_by_k["Mean_Coverage"], marker="o", label="Mean Coverage")

    # Highlight plateau points
    plateau_points = cov_by_k[cov_by_k["Plateau"]]
    if not plateau_points.empty:
        plt.scatter(
            plateau_points["K"],
            plateau_points["Mean_Coverage"],
            color="red",
            label="Plateau (< threshold)"
        )
        # Annotate first plateau
        first_plateau = plateau_points.iloc[0]
        plt.axvline(first_plateau["K"], color="red", linestyle="--", linewidth=1)
        plt.text(first_plateau["K"], first_plateau["Mean_Coverage"],
                 f"Recommended K={int(first_plateau['K'])}",
                 color="red", fontsize=9, ha="left", va="bottom")

    plt.xlabel("Number of Clusters (K)")
    plt.ylabel("Average Coverage across Tools")
    plt.title(f"Coverage Plateau (gain < {threshold})")
    plt.legend()
    plt.tight_layout()

    if out_path:
        plt.savefig(out_path, dpi=150)
        print(f"[INFO] Saved {out_path}")
    plt.close()

    return cov_by_k




def combine_coverage_and_correlation(plateau_df, corr_summary_dict, output_dir):
    """
    Combine coverage plateau info (Mean_Coverage, gain) with correlation medians (MS, SKI).
    Produces CSV and plot for correlation-informed K selection.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get correlation summary by K
    corr_by_k = corr_summary_dict.get("K")
    if corr_by_k is None or corr_by_k.empty:
        print("[WARN] No correlation summary found for K. Skipping combined utils.")
        return None

    # Merge coverage info with correlation medians by K
    merged = pd.merge(
        plateau_df,
        corr_by_k,
        on="K",
        how="inner"
    )

    out_csv = os.path.join(output_dir, "combined_analysis_by_K.csv")
    merged.to_csv(out_csv, index=False)
    print(f"[INFO] Saved {out_csv}")

    # Plot: coverage + correlation vs K
    plt.figure(figsize=(9, 6))
    plt.plot(merged["K"], merged["Mean_Coverage"], marker="o",
             label="Average Coverage", color="tab:blue")
    plt.plot(merged["K"], merged["Coverage–MS_median"], marker="s",
             label="Coverage–MS (median ρ)", color="tab:green")
    plt.plot(merged["K"], merged["Coverage–SKI_median"], marker="^",
             label="Coverage–SKI (median ρ)", color="tab:red")

    # Highlight plateau K (first True in Plateau column)
    if "Plateau" in merged.columns and merged["Plateau"].any():
        plateau_k = merged.loc[merged["Plateau"]].iloc[0]["K"]
        plt.axvline(plateau_k, color="black", linestyle="--", linewidth=1)
        plt.text(
            plateau_k,
            merged["Mean_Coverage"].max() * 0.95,
            f"Plateau ≈ K={int(plateau_k)}",
            color="black",
            fontsize=9,
            ha="left",
            va="top"
        )

    plt.xlabel("Number of Clusters (K)")
    plt.ylabel("Score / Correlation")
    plt.title("Combined Coverage & Correlation Analysis by K")
    plt.legend()
    plt.tight_layout()

    out_fig = os.path.join(output_dir, "combined_analysis_by_K.png")
    plt.savefig(out_fig, dpi=150)
    plt.close()
    print(f"[INFO] Saved {out_fig}")

    return merged


# -------------------------------------------------
# 4️⃣ Combined entry-point function
# -------------------------------------------------
def generate_analysis_reports(corr_csv, cov_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: correlation summaries
    corr_summary = summarize_correlations(corr_csv, output_dir=output_dir)

    # Step 2: coverage-plateau utils
    plateau_df = coverage_plateau_from_tools(
        cov_csv,
        out_path=os.path.join(output_dir, "coverage_plateau_from_tools.png")
    )
    plateau_df.to_csv(os.path.join(output_dir, "coverage_plateau_from_tools.csv"), index=False)
    print("[INFO] Saved coverage_plateau_from_tools.csv")

    # Step 3: combined report
    combine_coverage_and_correlation(plateau_df, corr_summary, output_dir)

    return corr_summary, plateau_df


def plot_mutation_scores(csv_path: str, out_path: str = None):
    """
    Plots Mutation Score (MS) by Tool, sorted ascending.
    CSV must include columns like 'Tool' or 'Tools', 'MS', and 'mutants_selected' (case-insensitive).
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import os

    df = pd.read_csv(csv_path)

    # --- Normalize column names ---
    df.columns = [c.strip().lower() for c in df.columns]

    # --- Resolve alternate column names ---
    col_map = {}
    col_map["tool"] = next((c for c in df.columns if "tool" in c), None)
    col_map["ms"] = next((c for c in df.columns if c.startswith("ms")), None)
    col_map["mutants"] = next((c for c in df.columns if "mutant" in c and "selected" in c), None)

    if not all(col_map.values()):
        raise ValueError(
            f"Missing required columns. Found: {df.columns.tolist()}, "
            f"expected something like: 'Tools'/'Tool', 'MS', 'mutants_selected'."
        )

    # --- Rename for consistency ---
    df = df.rename(columns={
        col_map["tool"]: "Tools",
        col_map["ms"]: "MS",
        col_map["mutants"]: "mutants_selected"
    })

    # --- Sort and plot ---
    df = df.sort_values("MS", ascending=True)
    mutants_left = int(df["mutants_selected"].iloc[0])

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(8, 5))

    sns.barplot(
        x="Tools",
        y="MS",
        hue="Tools",
        data=df,
        palette="viridis",
        legend=False,
        edgecolor="black"
    )

    plt.ylim(0, 1.0)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Mutation Score (MS)")
    plt.xlabel("Tools")
    plt.title(f"Mutation Scores by Tool  |  Mutants Remaining: {mutants_left}")

    for i, v in enumerate(df["MS"]):
        plt.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)

    plt.tight_layout()
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=150)
        print(f"[INFO] Saved mutation score plot → {out_path}")
    plt.close()



#!/usr/bin/env python3
"""
analysis_reports.py

Generates run-level and summary-level visualization reports:
- Boxplots & scatter plots from correlation tables.
- Mutation score bar plots.
- Optional summary-level plots (for average correlation table).

Updated for the current structure:
FUZZ_TOOL_SELECTION/result/<SUBJECT>/run_x/
and FUZZ_TOOL_SELECTION/result/<SUBJECT>/correlations_summary/
"""

import os
import pandas as pd
from pathlib import Path


# ===============================================================
# Main driver
# ===============================================================
def generate_reports_for_all_runs(subject: str,BASE_DIR):

    run_dirs = sorted([d for d in BASE_DIR.iterdir() if d.is_dir() and d.name.startswith("run_")])
    if not run_dirs:
        print(f"[WARN] No run directories found for {subject}")
        return

    for run_dir in run_dirs:
        print(f"\n[INFO] Processing → {run_dir.name}")

        corr_csv = run_dir / "correlations_table.csv"
        mut_csv  = run_dir / "mutation_metrics.csv"
        plots_dir = run_dir / "analysis_plots"
        plots_dir.mkdir(exist_ok=True)

        # --- Correlation table plots ---
        if corr_csv.exists():
            print(f"[PLOT] Generating plots for {corr_csv.name}")
            generate_plots_from_csv(
                csv_path=corr_csv,
                output_dir=plots_dir,
                correlation_cols=["Coverage–MS"],   # only MS correlation
                groupings=["Embedding_Model", "Cluster_Algo", "K"],
                scatter_pairs=[("CHI", "Coverage–MS")]
            )

        # --- Mutation score bar plot ---
        if mut_csv.exists():
            print(f"[PLOT] Generating mutation score plot for {mut_csv.name}")
            plot_mutation_scores(
                csv_path=str(mut_csv),
                out_path=str(plots_dir / "mutation_scores.png")
            )

    print(f"\n Completed all run-level plots for {subject}")


def generate_summary_reports(BASE_DIR):
    """
    Generates final summary plots only for the average correlation table
    under correlations_summary folder.
    """
    summary_dir = BASE_DIR / "correlations_summary"
    corr_csv = summary_dir / "final_correlation_summary.csv"
    plots_dir = summary_dir / "summary_plots"
    plots_dir.mkdir(exist_ok=True)

    if not corr_csv.exists():
        print(f"[WARN] No average correlation table found at {corr_csv}")
        return

    print(f"[PLOT] Generating summary plots for {corr_csv.name}")
    generate_plots_from_csv(
        csv_path=corr_csv,
        output_dir=plots_dir,
        correlation_cols=["Mean_Coverage–MS"],
        groupings=["Embedding_Model", "Cluster_Algo"],
        scatter_pairs=[]
    )
    print(f" Saved summary plots to {plots_dir}")
def plot_jaccard_trends(summary_csv: str, out_path: str = None):
    """
    Plot Jaccard similarity trends for each embedding model across different K values.
    Input CSV must include columns:
        ['Embedding_Model', 'TopK', 'Jaccard_Mean', 'Jaccard_Std']
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    df = pd.read_csv(summary_csv)
    if not {'Embedding_Model', 'TopK', 'Jaccard_Mean'}.issubset(df.columns):
        raise ValueError("Missing required columns in jaccard_summary_by_model.csv")

    df["TopK"] = pd.to_numeric(df["TopK"], errors="coerce")
    df = df.dropna(subset=["TopK"])

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(9, 6))

    # Main lineplot: Jaccard Mean vs K, grouped by Model
    sns.lineplot(
        data=df,
        x="TopK",
        y="Jaccard_Mean",
        hue="Embedding_Model",
        marker="o",
        linewidth=2.0,
        palette="tab10"
    )

    # Optional error bars (±std)
    if "Jaccard_Std" in df.columns:
        for model, sub in df.groupby("Embedding_Model"):
            plt.fill_between(
                sub["TopK"],
                sub["Jaccard_Mean"] - sub["Jaccard_Std"],
                sub["Jaccard_Mean"] + sub["Jaccard_Std"],
                alpha=0.2
            )

    plt.xlabel("Top-K Tools Selected")
    plt.ylabel("Jaccard Similarity (Coverage vs MS)")
    plt.title("Per-Model Jaccard Similarity Across Different K")
    plt.legend(title="Embedding Model", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=150)
        print(f"[INFO] Saved Jaccard similarity trend plot → {out_path}")
    plt.close()


# ===============================================================
# Entry point
# ===============================================================
if __name__ == "__main__":
    SUBJECT = "GRAALJS" #RHINO #KARATEJS #NASHORN
    BASE_DIR = Path("FUZZ_TOOL_SELECTION/result") / SUBJECT

    print(f"[RUN] Generating analysis reports for {SUBJECT} ...")
    generate_reports_for_all_runs(SUBJECT,BASE_DIR)
    generate_summary_reports(BASE_DIR)
    # --- New: Plot Jaccard trend ---
    jaccard_summary_path = BASE_DIR / "correlations_summary" / "jaccard_summary_by_model.csv"
    jaccard_plot_path = BASE_DIR / "correlations_summary" / "jaccard_similarity_trends.png"

    if jaccard_summary_path.exists():
        print(f"[PLOT] Generating Jaccard similarity trend for {SUBJECT} ...")
        plot_jaccard_trends(str(jaccard_summary_path), str(jaccard_plot_path))
    else:
        print("[WARN] No Jaccard summary found to plot.")
