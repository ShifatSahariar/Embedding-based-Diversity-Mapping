#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from pathlib import Path


def compute_jaccard_per_model(cluster_csv: Path, mutation_csv: Path, top_ks=(3,)):
    """
    Compute Jaccard similarity per embedding model for given top-Ks,
    ensuring tool alignment from mutation_metrics.csv.
    """
    cluster_df = pd.read_csv(cluster_csv)
    mutation_df = pd.read_csv(mutation_csv)

    # --------------------------------------------------
    #  Extract tool names from mutation_metrics.csv
    # --------------------------------------------------
    tool_col = "Tool" if "Tool" in mutation_df.columns else "Tools"
    tool_names = mutation_df[tool_col].dropna().unique().tolist()

    # --------------------------------------------------
    # Filter cluster coverage columns to only include these tools
    # --------------------------------------------------
    coverage_tool_cols = [c for c in cluster_df.columns if c in tool_names]
    if not coverage_tool_cols:
        raise ValueError(f"No matching tool columns found in {cluster_csv}")

    if "Model" not in cluster_df.columns:
        raise ValueError("Missing 'Embedding Model' column in cluster coverage CSV")

    # --------------------------------------------------
    #  Prepare mutation scores (sorted descending)
    # --------------------------------------------------
    ms_scores = (
        mutation_df.set_index(tool_col)["MS"]
        .astype(float)
        .sort_values(ascending=False)
    )

    results_by_k = {}

    # --------------------------------------------------
    # Compute Jaccard similarity per embedding model
    # --------------------------------------------------
    for K in top_ks:
        rows = []
        for model_name, sub_df in cluster_df.groupby("Model"):
            # mean coverage for each tool for this model
            coverage_means = (
                sub_df[coverage_tool_cols]
                .apply(pd.to_numeric, errors="coerce")
                .mean()
                .sort_values(ascending=False)
            )

            top_cov = set(coverage_means.head(K).index)
            top_ms = set(ms_scores.head(K).index)

            inter = len(top_cov & top_ms)
            union = len(top_cov | top_ms)
            jaccard = inter / union if union > 0 else 0.0

            rows.append({
                "Embedding_Model": model_name,
                "TopK": K,
                "Jaccard": round(jaccard, 4),
                "Top_Cov_Tools": ", ".join(top_cov),
                "Top_MS_Tools": ", ".join(top_ms),
            })

        results_by_k[K] = pd.DataFrame(rows)

    return results_by_k


def compute_jaccard_for_run(run_dir: Path, top_ks=(3,)):
    """Compute per-model Jaccard similarity for a single run."""
    cluster_csv = run_dir / f"cluster_coverage_summary_{run_dir.name}.csv"
    mutation_csv = run_dir / "mutation_metrics.csv"
    out_dir = run_dir / "jaccard_similarity"
    out_dir.mkdir(exist_ok=True)

    if not cluster_csv.exists() or not mutation_csv.exists():
        print(f"[SKIP] Missing files for {run_dir.name}")
        return None

    print(f"[RUN] Computing Jaccard similarity for {run_dir.name}...")
    results_by_k = compute_jaccard_per_model(cluster_csv, mutation_csv, top_ks=top_ks)

    all_paths = []
    for K, df in results_by_k.items():
        out_file = out_dir / f"topK_{K}.csv"
        df.to_csv(out_file, index=False)
        print(f"[OK] Saved → {out_file}")
        all_paths.append(out_file)
    return all_paths


def compute_jaccard_summary(subject: str, base_dir="FUZZ_TOOL_SELECTION/result", top_ks=(3,)):
    """Compute Jaccard similarity summary across runs."""
    subject_dir = Path(base_dir) / subject.upper()
    run_dirs = sorted(
        [d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
    )
    if not run_dirs:
        print(f"[WARN] No run folders found for {subject}")
        return

    combined = []
    for run_dir in run_dirs:
        run_results = compute_jaccard_for_run(run_dir, top_ks=top_ks)
        if not run_results:
            continue
        for K in top_ks:
            csv_path = run_dir / "jaccard_similarity" / f"topK_{K}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                df["Run"] = run_dir.name
                combined.append(df)

    if not combined:
        print("[WARN] No valid Jaccard results found.")
        return

    summary = (
        pd.concat(combined)
        .groupby(["Embedding_Model", "TopK"])["Jaccard"]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "Jaccard_Mean", "std": "Jaccard_Std"})
    )

    out_dir = subject_dir / "correlations_summary"
    out_dir.mkdir(exist_ok=True)
    summary_csv = out_dir / "jaccard_summary_by_model.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"\nSaved subject-level summary → {summary_csv}")

    return summary


if __name__ == "__main__":
    SUBJECT = "GRAALJS" # RHINO BASIC #CALC GRAALJS NASHORN KARATEJS
    compute_jaccard_summary(SUBJECT, top_ks=(1,2,3,4))
