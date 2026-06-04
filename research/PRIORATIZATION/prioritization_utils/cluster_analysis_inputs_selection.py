import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import spearmanr

def analyze_cluster_mutation_diversity(clusters, mut_profiles_dict, base_dir):
    """
    Analyzing mutation behavior and diversity for each cluster.

    For each cluster: we compute-
      - Ci = cluster size (number of inputs)
      - Ki = total unique mutants killed by cluster
      - Ki/Ci = average mutant kills per input (efficiency)
      - avg_ms = average mutation score of inputs in cluster
      - gini_impurity = diversity of killing patterns (0 = identical, 0.5 = diverse)

    Saves:
      - CSV summary table
      - Plots:
          1. Cluster Size vs Killing Capability (Ki/Ci)
          2. Cluster Size vs Gini Impurity
          3. (Optional) Ki_per_Ci vs Cluster Size (scatter color-coded by Gini)
    """

    # ---------------------------------------------------------------
    # Prepare save directory
    # ---------------------------------------------------------------
    save_dir = Path(base_dir) / "cluster_analysis"
    save_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Compute metrics for each cluster
    # ---------------------------------------------------------------
    records = []
    for cid, members in sorted(clusters.items()):
        cluster_size = len(members)
        if cluster_size == 0:
            continue

        # Collect mutation profiles (ensure boolean)
        member_profiles = np.array([mut_profiles_dict[m] for m in members]).astype(bool)

        # Mean mutation score per input
        input_ms = member_profiles.mean(axis=1)
        avg_ms = np.mean(input_ms)

        # Cluster-level killed mutants (union)
        cluster_union = np.any(member_profiles, axis=0)
        Ki = np.sum(cluster_union)

        # Gini impurity
        p = member_profiles.mean(axis=0)       # fraction of inputs killing each mutant
        gini = np.mean(2 * p * (1 - p))        # average impurity per mutant

        # Record
        records.append({
            "cluster_id": cid,
            "cluster_size": cluster_size,
            "Ki": Ki,
            "Ki_per_Ci": Ki / cluster_size,
            "avg_ms": avg_ms,
            "gini_impurity": gini,
            "inputs": ";".join(members)
        })

    # ---------------------------------------------------------------
    # Create DataFrame + Sort by Cluster Size
    # ---------------------------------------------------------------
    df = pd.DataFrame(records)
    df.sort_values(by="cluster_size", inplace=True)
    csv_path = save_dir / "cluster_mutation_diversity.csv"
    df.to_csv(csv_path, index=False)
    print(f"[INFO] Saved cluster diversity table → {csv_path}")

    # ---------------------------------------------------------------
    # Correlation Analysis (Spearman)
    # ---------------------------------------------------------------
    if len(df) > 1:
        rho_k, p_k = spearmanr(df["cluster_size"], df["Ki_per_Ci"])
        rho_g, p_g = spearmanr(df["cluster_size"], df["gini_impurity"])
        print(f"[STATS] Spearman Corr (size vs Ki/Ci): ρ={rho_k:.3f}, p={p_k:.4f}")
        print(f"[STATS] Spearman Corr (size vs Gini): ρ={rho_g:.3f}, p={p_g:.4f}")

        with open(save_dir / "correlation_stats.txt", "w") as f:
            f.write(f"Spearman Corr (size vs Ki/Ci): ρ={rho_k:.3f}, p={p_k:.4f}\n")
            f.write(f"Spearman Corr (size vs Gini): ρ={rho_g:.3f}, p={p_g:.4f}\n")

    # ---------------------------------------------------------------
    # Plot 1 — Cluster Size vs Ki/Ci (Line + Gini overlay)
    # ---------------------------------------------------------------
    plt.figure(figsize=(10,6))
    plt.plot(df["cluster_size"], df["Ki_per_Ci"], "o-", linewidth=2, label="Ki/Ci (Efficiency)")
    plt.xlabel("Cluster Size (Ci)")
    plt.ylabel("Killing Capability (Ki/Ci)")
    plt.title("Cluster Size vs Mutation Killing Capability")
    plt.grid(alpha=0.4)

    ax2 = plt.twinx()
    ax2.plot(df["cluster_size"], df["gini_impurity"], "s--", color="orange", label="Gini Impurity")
    ax2.set_ylabel("Gini Impurity")

    plt.tight_layout()
    plt.savefig(save_dir / "ClusterSize_vs_KiPerCi_and_Gini.png")
    plt.close()

    # ---------------------------------------------------------------
    # Plot 2 — Cluster Size vs Gini Impurity (trend only)
    # ---------------------------------------------------------------
    plt.figure(figsize=(10,6))
    plt.plot(df["cluster_size"], df["gini_impurity"], "o-", color="purple", linewidth=2)
    plt.xlabel("Cluster Size (Ci)")
    plt.ylabel("Gini Impurity")
    plt.title("Cluster Size vs Diversity (Gini Impurity)")
    plt.grid(alpha=0.4)
    plt.tight_layout()
    plt.savefig(save_dir / "ClusterSize_vs_Gini.png")
    plt.close()

    # ---------------------------------------------------------------
    # Plot 3 — Scatter (color-coded by Gini)
    # ---------------------------------------------------------------
    plt.figure(figsize=(10,6))
    scatter = plt.scatter(df["cluster_size"], df["Ki_per_Ci"],
                          c=df["gini_impurity"], cmap="viridis", s=80, edgecolor="k")
    plt.colorbar(scatter, label="Gini Impurity")
    plt.xlabel("Cluster Size (Ci)")
    plt.ylabel("Killing Capability (Ki/Ci)")
    plt.title("Cluster Killing Capability vs Cluster Size")
    plt.grid(alpha=0.4)
    plt.tight_layout()
    plt.savefig(save_dir / "Scatter_KiPerCi_vs_ClusterSize.png")
    plt.close()

    print(f"[INFO] Plots saved under → {save_dir}")

    return df

def _push_small_clusters_to_end(cluster_order, clusters, min_cluster_size):
    """
    Reorders a given cluster_order so that clusters with size < min_cluster_size
    are moved to the end, preserving the relative order within 'big' and 'small'.
    """
    if min_cluster_size is None or min_cluster_size <= 1:
        return cluster_order  # no change

    big = []
    small = []
    for cid in cluster_order:
        size = len(clusters[cid])
        if size >= min_cluster_size:
            big.append(cid)
        else:
            small.append(cid)

    # Big clusters first, then small ones
    return big + small
