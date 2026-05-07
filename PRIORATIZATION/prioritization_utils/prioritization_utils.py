from collections import defaultdict
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.cluster import AffinityPropagation

from PRIORATIZATION.input_selection.cluster_strategies.by_centroid_global import cluster_by_centroid_global
from PRIORATIZATION.input_selection.cluster_strategies.by_centroid_spread import cluster_by_centroid_spread
from PRIORATIZATION.input_selection.cluster_strategies.by_medoid_novelty import cluster_by_medoid_novelty
from PRIORATIZATION.input_selection.cluster_strategies.by_size import cluster_by_size
from PRIORATIZATION.input_selection.input_strategies.by_exemplar_distance import inputs_by_exemplar_distance

from PRIORATIZATION.input_selection.input_strategies.by_graph_centrality import select_by_graph_betweenness
from PRIORATIZATION.prioritization_utils.cluster_analysis_inputs_selection import _push_small_clusters_to_end


def cluster_embeddings_once(embeddings_dict):

    all_inputs = list(embeddings_dict.keys())
    X = np.vstack([embeddings_dict[i] for i in all_inputs])
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-8  # L2 normalize

    model = AffinityPropagation()
    labels = model.fit_predict(X)
    exemplar_indices = model.cluster_centers_indices_

    # Build cluster → list of input IDs
    clusters = defaultdict(list)
    for name, label in zip(all_inputs, labels):
        clusters[label].append(name)

    exemplar_map = {}
    for lbl, idx in zip(sorted(clusters.keys()), exemplar_indices):
        exemplar_map[lbl] = all_inputs[idx]

    # Compute centroids
    centroids = {}
    for lbl, members in clusters.items():
        vecs = np.vstack([embeddings_dict[i] for i in members])
        cent = np.mean(vecs, axis=0)
        cent /= np.linalg.norm(cent) + 1e-8
        centroids[lbl] = cent


    print(f"[INFO] Affinity → K={len(clusters)}")
    return clusters, exemplar_map



def compute_all_cluster_orders(embeddings_dict, n_jobs=4, min_cluster_size=None):
    """
    Computes multiple cluster ranking strategies in parallel.

    Parameters
    ----------
    embeddings_dict : dict
        Mapping from input_id -> embedding vector.
    n_jobs : int
        Max workers for ProcessPoolExecutor.
    min_cluster_size : int or None
        If given and > 1, clusters with fewer than this many inputs
        are pushed to the end of the ranking for *all* strategies.
        (We still keep them; they just come later in round-robin.)
    """
    # 1) Cluster once
    clusters, exemplar_map = cluster_embeddings_once(embeddings_dict)

    # 2) Precompute medoids for MedoidNovelty strategy
    from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_medoid
    medoids = {}
    for cluster_id, members in clusters.items():
        if members:
            medoids[cluster_id] = compute_medoid(embeddings_dict, members)

    # 3) Prepare tasks
    tasks = {
        "Size": (cluster_by_size, clusters),
        "CentroidSpread": (cluster_by_centroid_spread, clusters, embeddings_dict),
        "CentroidNovelty": (cluster_by_centroid_global, clusters, embeddings_dict),
        "MedoidNovelty": (cluster_by_medoid_novelty, clusters, embeddings_dict, medoids),
    }

    orders = {}

    if n_jobs == 1:
        for key, (fn, *args) in tasks.items():
            try:
                order = fn(*args)
                if isinstance(order, dict):
                    order = sorted(order.keys(), key=lambda cid: order[cid])
                orders[key] = _push_small_clusters_to_end(order, clusters, min_cluster_size)
            except Exception as e:
                print(f"Strategy {key} failed: {e}")
                fallback = list(clusters.keys())
                orders[key] = _push_small_clusters_to_end(fallback, clusters, min_cluster_size)
        return clusters, orders, exemplar_map

    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        future_to_key = {}

        for key, (fn, *args) in tasks.items():
            future = executor.submit(fn, *args)
            future_to_key[future] = key

        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                order = future.result()

                # Ensure we have a list of cluster IDs
                # (in case a strategy returns something else)
                if isinstance(order, dict):
                    # assume dict: cluster_id -> score; sort by score
                    order = sorted(order.keys(), key=lambda cid: order[cid])

                # Post-process: push small clusters to end
                order = _push_small_clusters_to_end(order, clusters, min_cluster_size)

                orders[key] = order

            except Exception as e:
                print(f"Strategy {key} failed: {e}")
                # Fallback: use cluster IDs in original dictionary order,
                # optionally respecting min_cluster_size as well
                fallback = list(clusters.keys())
                fallback = _push_small_clusters_to_end(fallback, clusters, min_cluster_size)
                orders[key] = fallback

    return clusters, orders, exemplar_map




# def compute_all_cluster_orders(embeddings_dict, n_jobs=4):
#     """
#     Computes multiple cluster ranking strategies in parallel.
#
#     """
#     clusters, exemplar_map = cluster_embeddings_once(embeddings_dict)
#
#     # Precompute medoids for MedoidNovelty strategy
#     from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_medoid
#     medoids = {}
#     for cluster_id, members in clusters.items():
#         if members:
#             medoids[cluster_id] = compute_medoid(embeddings_dict, members)
#
#     # Prepare tasks with correct parameters
#     tasks = {
#         "Size": (cluster_by_size, clusters),
#         "CentroidSpread": (cluster_by_centroid_spread, clusters, embeddings_dict),
#         "CentroidNovelty": (cluster_by_centroid_global, clusters, embeddings_dict),
#         "MedoidNovelty": (cluster_by_medoid_novelty, clusters, embeddings_dict, medoids),
#     }
#
#     orders = {}
#
#     with ProcessPoolExecutor(max_workers=n_jobs) as executor:
#         future_to_key = {}
#
#         for key, (fn, *args) in tasks.items():
#             future = executor.submit(fn, *args)
#             future_to_key[future] = key
#
#         for future in concurrent.futures.as_completed(future_to_key):
#             key = future_to_key[future]
#             try:
#                 orders[key] = future.result()
#             except Exception as e:
#                 print(f"Strategy {key} failed: {e}")
#                 # Fallback: use cluster IDs in original order
#                 orders[key] = list(clusters.keys())
#
#     return clusters, orders, exemplar_map


def compute_input_rankings(clusters, embeddings_dict, exemplar_map, n_jobs=4):
    """
    Computes multiple input ranking strategies within each cluster in parallel.

    For each cluster, ranks its inputs using different strategies:
    - ExemplarDistance: Distance to cluster exemplar
    - MedoidDistance: Distance to cluster medoid
    - GraphBetweenness: Betweenness centrality in similarity graph

    Returns
    -------
    dict[str, dict[int, list[str]]]
        Mapping of strategy_name to cluster_input_rankings
        Example: {
            "ExemplarDistance": {0: ["doc2", "doc1", "doc3"], 1: ["doc5", "doc4"]},
            "MedoidDistance": {0: ["doc1", "doc2", "doc3"], 1: ["doc4", "doc5"]},
            "GraphBetweenness": {0: ["doc2", "doc3", "doc1"], 1: ["doc5", "doc4"]}
        }
    """
    # Precompute medoids for MedoidDistance strategy
    from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_medoid
    medoids = {}
    for cluster_id, members in clusters.items():
        if members:
            medoids[cluster_id] = compute_medoid(embeddings_dict, members)

    # Define input ranking strategies
    input_strategies = {
        "ExemplarDistance": (inputs_by_exemplar_distance, clusters, embeddings_dict, exemplar_map),
        "GraphBetweenness": (select_by_graph_betweenness, clusters, embeddings_dict)}
        # "MedoidDistance": (inputs_by_medoid_distance_all_optimized, clusters, embeddings_dict), # kind of similar to exemplar-from observation


    input_rankings = {}

    if n_jobs == 1:
        for strategy_name, (fn, *args) in input_strategies.items():
            try:
                input_rankings[strategy_name] = fn(*args)
            except Exception as e:
                print(f"Input ranking strategy {strategy_name} failed: {e}")
                input_rankings[strategy_name] = {cid: members[:] for cid, members in clusters.items()}
        return input_rankings

    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        future_to_key = {}

        for strategy_name, (fn, *args) in input_strategies.items():
            future = executor.submit(fn, *args)
            future_to_key[future] = strategy_name

        for future in concurrent.futures.as_completed(future_to_key):
            strategy_name = future_to_key[future]
            try:
                input_rankings[strategy_name] = future.result()
            except Exception as e:
                print(f"Input ranking strategy {strategy_name} failed: {e}")
                # Fallback: use original order for all clusters
                input_rankings[strategy_name] = {cid: members[:] for cid, members in clusters.items()}

    return input_rankings
