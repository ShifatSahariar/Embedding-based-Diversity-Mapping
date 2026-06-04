import numpy as np

from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_centroid


def cluster_by_centroid_spread(clusters, embeddings):
    """
    Prioritizes clusters using max-min diversity selection to maximize coverage.

    Starts with the smallest cluster, then iteratively selects the cluster that
    is most different (farthest cosine distance) from all currently selected
    clusters. This ensures diverse cluster selection across the embedding space.

    Examples
    --------
    >>> clusters = {0: ["A", "B"], 1: ["C", "D"], 2: ["E", "F"]}
    >>> # If cluster centroids are: 0=[1,0], 1=[0,1], 2=[-1,0]
    >>> # Start with smallest cluster, then pick farthest in cosine space
    >>> cluster_by_centroid_spread(clusters, embeddings)
    [2, 1, 0]  # Example diverse ordering
    """
    """
    Optimized version with precomputed distance matrix and vectorized operations.
    """
    if not clusters:
        return []

    # Compute centroids and create label mapping
    valid_clusters = {lbl: members for lbl, members in clusters.items() if members}
    if not valid_clusters:
        return []

    labels = list(valid_clusters.keys())
    centroids = [compute_centroid(embeddings, valid_clusters[lbl]) for lbl in labels]
    centroids_array = np.array(centroids)

    # Precompute all pairwise cosine distances
    # Cosine distance = 1 - cosine similarity
    from sklearn.metrics.pairwise import cosine_similarity
    similarity_matrix = cosine_similarity(centroids_array)
    distance_matrix = 1 - similarity_matrix

    # Create label to index mapping
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    # THIS PART WE COMMENTED SINCE ITS OMMIT THE DETERMINISTIC BEHAVIOR AND WE HAVE REFINED BELLOW
    # # Start with smallest cluster
    # smallest_label = min(valid_clusters, key=lambda l: len(valid_clusters[l]))
    # selected = [smallest_label]
    # selected_indices = {label_to_idx[smallest_label]}
    # --- Deterministic seed selection (Algorithm 1, refined) ---
    # Find smallest cluster size

    """
    If multiple clusters are equally small, we start with the one whose centroid is most isolated from the others.
    - preserves diversity-first logic + determinism
    """
    min_size = min(len(members) for members in valid_clusters.values())

    # All clusters with smallest size
    smallest_labels = [lbl for lbl, members in valid_clusters.items()
                       if len(members) == min_size]

    if len(smallest_labels) == 1:
        smallest_label = smallest_labels[0]
    else:
        # Tie-break by centroid isolation (average distance to others)
        def isolation_score(lbl):
            idx = label_to_idx[lbl]
            return np.mean([
                distance_matrix[idx, j]
                for j in range(len(labels)) if j != idx
            ])

        smallest_label = max(smallest_labels, key=isolation_score)

    selected = [smallest_label]
    selected_indices = {label_to_idx[smallest_label]}


    remaining_indices = set(range(len(labels))) - selected_indices

    # Optimized max-min selection using precomputed distances
    while remaining_indices:
        # For each remaining cluster, find min distance to any selected cluster
        min_distances = []
        for rem_idx in remaining_indices:
            min_dist = min(distance_matrix[rem_idx, sel_idx] for sel_idx in selected_indices)
            min_distances.append((rem_idx, min_dist))

        # Select cluster with maximum minimum distance
        next_idx, _ = max(min_distances, key=lambda x: x[1])
        next_label = labels[next_idx]

        selected.append(next_label)
        selected_indices.add(next_idx)
        remaining_indices.remove(next_idx)

    return selected