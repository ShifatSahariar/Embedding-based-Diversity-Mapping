
import re
import logging
from pathlib import Path
import pandas as pd


from FUZZ_TOOL_SELECTION.utils.correlations_utils import build_correlations_table
from scipy.stats import wilcoxon
import numpy as np
# ======================== SETTINGS =========================

NON_K_ALGOS = {"Affinity", "OPTICS", "HDBSCAN", "MeanShift"}
CFG_PATTERN = re.compile(r"^(.*?)\s*\+\s*(.*?)\s*(?:\+\s*(\d+))?$")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("corr-builder")
# ============================================================

def combine_cluster_coverage_across_runs(subject_dir: Path):
    """
    Aggregate cluster_coverage_summary_*.csv files across all runs
    and compute mean and standard deviation of cluster coverage
    per model and generator.
    """

    run_dirs = sorted([d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith("run_")])
    if not run_dirs:
        raise FileNotFoundError(f"No run folders found under {subject_dir}")

    all_coverages = []

    for run_dir in run_dirs:
        coverage_path = next(run_dir.glob("cluster_coverage_summary_*.csv"), None)
        if not coverage_path:
            log.warning(f"[SKIP] No cluster coverage file found in {run_dir}")
            continue

        df = pd.read_csv(coverage_path)

        # Normalize column names if needed
        df = df.rename(columns={"DB": "DBI", "CH": "CHI"})

        # Keep only relevant columns (Model + tools)
        tool_cols = [c for c in df.columns if c not in (
            "Run", "Cluster Algo", "K_eff", "Silhouette", "DBI", "CHI"
        )]

        if "Model" not in tool_cols:
            raise KeyError(f"'Model' column missing in {coverage_path}")

        filtered_df = df[tool_cols].copy()
        filtered_df["Run"] = run_dir.name
        all_coverages.append(filtered_df)

    if not all_coverages:
        raise RuntimeError("No valid cluster coverage files found to combine.")

    merged = pd.concat(all_coverages, axis=0, ignore_index=True)

    # Identify tool columns
    tool_columns = [c for c in merged.columns if c not in ("Model", "Run")]

    # --- Compute mean coverage ---
    mean_df = (
        merged.groupby("Model")[tool_columns]
        .mean(numeric_only=True)
        .reset_index()
        .sort_values("Model")
    )

    # --- Compute standard deviation coverage ---
    std_df = (
        merged.groupby("Model")[tool_columns]
        .std(numeric_only=True)
        .reset_index()
        .sort_values("Model")
    )

    # Rename std columns
    std_df = std_df.rename(columns={col: f"{col}_std" for col in tool_columns})

    # --- Merge mean and std side by side ---
    summary_df = pd.merge(mean_df, std_df, on="Model", how="left")

    # --- Save combined summary ---
    output_dir = subject_dir / "correlations_summary"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "cluster_coverage_summary_all_runs.csv"
    summary_df.to_csv(out_path, index=False)

    log.info(f"[OK] Saved cluster coverage mean+std summary across runs → {out_path}")
    return summary_df

# ============================================================
# Helper functions
# ============================================================
def parse_configuration(cfg: str):
    """Parse 'OpenAI + K-Means + 20' -> (model, algo, K or None)."""
    m = CFG_PATTERN.match(cfg.strip())
    if not m:
        raise ValueError(f"Unparsable Configuration: {cfg!r}")
    model = m.group(1).strip()
    algo  = m.group(2).strip()
    k_str = m.group(3)
    K = int(k_str) if k_str is not None else None
    return model, algo, K


def load_generators(run_dir: Path, mutation_metrics_df: pd.DataFrame) -> list[str]:
    """
    Load generator names.
    Priority:
      1. If generators.txt exists → read it (preserves custom order).
      2. Otherwise → infer from mutation_metrics.csv (Tools column).
    """
    gen_file = run_dir / "generators.txt"

    # If a generator file exists, use it
    if gen_file.exists():
        with gen_file.open() as f:
            gens = [line.strip() for line in f if line.strip()]
        if not gens:
            raise ValueError(f"No generators listed in {gen_file}")
        return gens

    # Otherwise, infer from mutation metrics table
    col_name = "Tools" if "Tools" in mutation_metrics_df.columns else "Tool" if "Tool" in mutation_metrics_df.columns else None
    if not col_name:
        raise KeyError("Mutation metrics file must have a 'Tool' or 'Tools' column to infer generator list.")

    gens = list(mutation_metrics_df[col_name].dropna().unique())

    if not gens:
        raise ValueError("No generator names found in mutation metrics table.")
    print(f"[INFO] Inferred generator list from mutation_metrics.csv: {gens}")
    return gens


def read_csv_safe(path: Path, name: str):
    """Read CSV file or raise informative error."""
    if not path.exists():
        raise FileNotFoundError(f"{name} file missing: {path}")
    return pd.read_csv(path)


# ============================================================
# Main correlation analysis (per run)
# ============================================================
def build_correlation_for_run(run_dir: Path):
    """Compute Spearman correlations for one run folder."""
    log.info(f"\n[RUN] Processing: {run_dir.name}")

    coverage_path = next(run_dir.glob("cluster_coverage_summary_*.csv"), None)
    mutation_path = run_dir / "mutation_metrics.csv"
    output_corr = run_dir / "correlations_table.csv"

    if not coverage_path:
        raise FileNotFoundError(f"No cluster coverage CSV found in {run_dir}")

    # ---- Load Data ----
    cluster_coverage_df = read_csv_safe(coverage_path, "Cluster coverage")
    mutation_metrics_df = read_csv_safe(mutation_path, "Mutation metrics")
    generators = load_generators(run_dir, mutation_metrics_df)

    # Normalize possible legacy names
    cluster_coverage_df = cluster_coverage_df.rename(columns={"DB": "DBI", "CH": "CHI"})

    # Ensure Model and Cluster Algo exist
    if not {"Model", "Cluster Algo"}.issubset(cluster_coverage_df.columns):
        raise KeyError(f"Expected columns 'Model' and 'Cluster Algo' in {coverage_path}")

    # Build mutation metric dictionary (keyed by Tool)
    col_name = "Tools" if "Tools" in mutation_metrics_df.columns else "Tool"
    mutation_metrics = mutation_metrics_df.set_index(col_name).to_dict(orient="index")

    # Build results list for correlation
    results = []
    for _, row in cluster_coverage_df.iterrows():
        model = str(row["Model"]).strip()
        algo = str(row["Cluster Algo"]).strip()

        # Build unique configuration key
        cfg = f"{model} + {algo}"
        if "K" in row and not pd.isna(row["K"]):
            cfg += f" + {int(row['K'])}"

        # Collect per-generator coverage scores
        scores = {g: float(row[g]) for g in generators if g in row}

        results.append({
            "Configuration": cfg,
            "Embedding Model": model,
            "Cluster Algo": algo,
            "Scores": scores
        })
    # ---- Compute correlation table ----
    corr_df = build_correlations_table(
        results,
        mutation_metrics,
        generators,
        nan_fallback=0.0,  # backup value for missing data
    )

    # --- Save simple correlation table (2 columns only) ---
    corr_df = corr_df[["Configuration", "Coverage–MS"]]
    corr_df.to_csv(output_corr, index=False)

    log.info(f"[OK] Saved correlation table: {output_corr}")
    return corr_df


# ============================================================
# Combine all runs to computer avg correlation score
# ============================================================
def combine_all_runs(subject_dir: Path):
    """Aggregate correlation tables across all runs and compute final summary."""
    run_dirs = sorted([d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith("run_")])
    if not run_dirs:
        raise FileNotFoundError(f"No run folders found under {subject_dir}")

    all_corrs = []
    for run_dir in run_dirs:
        log.info(f"[REBUILD] Computing correlation for {run_dir.name} ...")
        corr_df = build_correlation_for_run(run_dir)
        all_corrs.append(corr_df)

    # --- Merge all runs into one table ---
    merged = pd.concat(all_corrs, axis=0, ignore_index=True)

    # --- Compute average correlation per configuration ---
    avg_corr = (
        merged.groupby("Configuration")["Coverage–MS"]
        .mean()
        .reset_index()
        .rename(columns={"Coverage–MS": "Mean_Coverage–MS"})
    )

    # --- Compute Wilcoxon p-value per configuration (stability test) ---
    p_values = []
    for cfg, sub_df in merged.groupby("Configuration"):
        corrs = sub_df["Coverage–MS"].dropna().astype(float).values
        if len(corrs) < 2:
            pval = np.nan  # Not enough data for statistical test
        else:
            try:
                res = wilcoxon(corrs, alternative="greater")
                pval = res.pvalue


            except Exception:
                pval = np.nan
        p_values.append({"Configuration": cfg, "Wilcoxon_p": round(pval, 6)})

    df_pvals = pd.DataFrame(p_values)

    # --- Merge average correlation with p-values ---
    final_df = avg_corr.merge(df_pvals, on="Configuration", how="left")

    # --- Save final unified summary ---
    output_dir = subject_dir / "correlations_summary"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / "final_correlation_summary.csv"
    final_df.to_csv(final_path, index=False)

    log.info(f"[OK] Saved unified correlation summary → {final_path}")

    # --- Compute and save cluster coverage mean/std summary ---
    try:
        log.info("[RUN] Aggregating cluster coverage across runs...")
        coverage_summary = combine_cluster_coverage_across_runs(subject_dir)
        log.info(f"[OK] Cluster coverage summary saved ({len(coverage_summary)} rows).")
    except Exception as e:
        log.warning(f"[WARN] Failed to compute cluster coverage summary: {e}")

    return final_df



# ============================================================
#  Main Entry
# ============================================================
def main():
    SUBJECT = "GRAALJS" # RHINO BASIC # CALC NASHORN GRAALJS KARATEJS
    DATA_ROOT = Path("FUZZ_TOOL_SELECTION/result")
    subject_dir = DATA_ROOT / SUBJECT
    combine_all_runs(subject_dir)


if __name__ == "__main__":
    main()
