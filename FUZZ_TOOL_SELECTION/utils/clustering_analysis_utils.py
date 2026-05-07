import os


import numpy as np

from sklearn.cluster import (
    KMeans, AgglomerativeClustering, SpectralClustering,
    Birch, AffinityPropagation, OPTICS, MeanShift
)
from hdbscan import HDBSCAN
from sklearn.preprocessing import normalize
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


def load_all_vectors(vectors_directory):
    """
    Reads *.txt vectors. Expects filenames like '<tool>_<id>_vector.txt'
    and infers tool name from the prefix.
    Returns (vectors, identifiers, id_to_tool).
    """
    vecs, ids, id2tool = [], [], {}
    for fname in os.listdir(vectors_directory):
        if not fname.endswith("_vector.txt"):
            continue
        base = fname[:-len("_vector.txt")]
        parts = base.split("_")
        tool = "_".join(parts[:-1]) if len(parts) >= 2 else base
        v = np.loadtxt(os.path.join(vectors_directory, fname))
        vecs.append(np.asarray(v, dtype=float))
        ids.append(fname)
        id2tool[fname] = tool
    return vecs, ids, id2tool




def perform_clustering(vectors, identifiers, algo, K=None, random_seed=42):
    """
    Simplified clustering wrapper without PCA.
    Returns (id2label, K_eff, quality).
    """
    X = normalize(np.vstack(vectors))

    if algo == "K-Means":
        if K is None:
            raise ValueError("K must be provided for K-Means")
        model = KMeans(n_clusters=K, n_init=10, random_state=random_seed)
        labels = model.fit_predict(X)

    elif algo == "Agglomerative":
        if K is None:
            raise ValueError("K must be provided for Agglomerative")
        model = AgglomerativeClustering(n_clusters=K, linkage="ward")
        labels = model.fit_predict(X)

    elif algo == "Spectral":
        if K is None:
            raise ValueError("K must be provided for Spectral")
        model = SpectralClustering(
            n_clusters=K, affinity="nearest_neighbors", assign_labels="kmeans",
            random_state=random_seed
        )
        labels = model.fit_predict(X)

    elif algo == "Birch":
        if K is None:
            raise ValueError("K must be provided for Birch")
        model = Birch(n_clusters=K)
        labels = model.fit_predict(X)

    elif algo == "Affinity":
        model = AffinityPropagation() #,max_iter=500
        labels = model.fit_predict(X)

    elif algo == "OPTICS":
        model = OPTICS(min_samples=30, xi=0.04, min_cluster_size=30)
        labels = model.fit_predict(X)

    elif algo == "HDBSCAN":
        model = HDBSCAN(min_cluster_size=30, min_samples=30)
        labels = model.fit_predict(X)

    elif algo == "MeanShift":
        model = MeanShift(bin_seeding=False)
        labels = model.fit_predict(X)

    else:
        raise ValueError(f"Unsupported algo: {algo}")

    labels = np.asarray(labels)
    unique_wo_noise = np.unique(labels[labels != -1])
    K_eff = int(unique_wo_noise.size) if unique_wo_noise.size > 0 else len(np.unique(labels))

    # --- Quality metrics ---
    try:
        mask = labels != -1
        if np.any(mask) and len(np.unique(labels[mask])) > 1:
            sil = silhouette_score(X[mask], labels[mask])
            dbi = davies_bouldin_score(X[mask], labels[mask])
            chi = calinski_harabasz_score(X[mask], labels[mask])
        else:
            sil = dbi = chi = np.nan
    except Exception:
        sil = dbi = chi = np.nan

    quality = {
        "silhouette": sil,
        "dbi": dbi,
        "chi": chi,
        "n_points": X.shape[0],
        "n_clusters_excl_noise": K_eff,
        "has_noise": bool(np.any(labels == -1)),
        "noise_fraction": float(np.mean(labels == -1))
    }

    print(f"[INFO] {algo} → K_eff={K_eff} | Sil={sil:.3f} DBI={dbi:.3f} CHI={chi:.3f}")
    return dict(zip(identifiers, labels.tolist())), K_eff, quality




def cluster_coverage_pipeline(
    embedding_models: dict,
    algorithms: list,
    k_values: list,
    generator_order: list,
    output_csv: str | None = None,
    random_seed: int = 42
):
    """
    For each (model, algo, K): cluster inputs and compute coverage per generator.
    Returns:
        rows (list of dicts), coverage_vectors (list of tuples)
    """
    import numpy as np
    import pandas as pd

    nonK_algos = {"Affinity", "OPTICS", "HDBSCAN", "MeanShift"}
    rows, coverage_vectors = [], []

    for model_name, vectors_dir in embedding_models.items():
        vecs, ids, id2tool = load_all_vectors(vectors_dir)
        if not vecs:
            print(f"[WARN] No vectors in {vectors_dir}; skipping {model_name}")
            continue

        for algo in algorithms:

            # helper to build a single result row
            def build_row(K_eff, quality, cov, algo_name, k_suffix=None):
                return {
                    "Model": model_name,
                    "Cluster Algo": algo_name,
                    "K_eff": K_eff,
                    "Silhouette": quality.get("silhouette", None),
                    "DBI": quality.get("dbi", None),
                    "CHI": quality.get("chi", None),
                    **cov
                }

            # ---------- Non-K algorithms ----------
            if algo in nonK_algos:
                print(f"[CFG] {model_name} + {algo}")
                id2label, K_eff, quality = perform_clustering(vecs, ids, algo=algo, random_seed=random_seed)

                tool2clusters = {t: set() for t in generator_order}
                for fid, lab in id2label.items():
                    tool2clusters[id2tool[fid]].add(lab)

                cov = {t: len(c) / max(1, K_eff) for t, c in tool2clusters.items()}
                row = build_row(K_eff, quality, cov, algo)
                rows.append(row)
                coverage_vectors.append((f"{model_name} + {algo}", np.array(list(cov.values())), K_eff))

            # ---------- K-based algorithms ----------
            else:
                for K in k_values:
                    print(f"[CFG] {model_name} + {algo} + {K}")
                    id2label, K_eff, quality = perform_clustering(
                        vecs, ids, algo=algo, K=K, random_seed=random_seed
                    )

                    tool2clusters = {t: set() for t in generator_order}
                    for fid, lab in id2label.items():
                        tool2clusters[id2tool[fid]].add(lab)

                    cov = {t: len(c) / max(1, K_eff) for t, c in tool2clusters.items()}
                    row = build_row(K_eff, quality, cov, algo, k_suffix=K)
                    rows.append(row)
                    coverage_vectors.append((f"{model_name} + {algo} + {K}", np.array(list(cov.values())), K_eff))

    df = pd.DataFrame(rows)

    # Sort for consistency: model → algo → K_eff
    if not df.empty:
        df = df.sort_values(by=["Model", "Cluster Algo", "K_eff"], ignore_index=True)

    if output_csv:
        df.to_csv(output_csv, index=False)
        print(f"[OK] Wrote cluster coverage → {output_csv}")
    else:
        print(f"[INFO] Skipped CSV writing (output_csv=None)")

    return rows, coverage_vectors



