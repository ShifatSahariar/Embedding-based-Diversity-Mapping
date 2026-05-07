import numpy as np


def cluster_by_centroid_global(clusters, embeddings):
    """
    Ranks clusters by their distinctiveness from the overall dataset.

    Computes the global centroid (mean of all embeddings), then measures how
    far each cluster's centroid is from this global center. Clusters farther
    from the global centroid are considered more distinctive/unusual.

    Examples
    --------
    >>> clusters = {0: ["A", "B"], 1: ["C", "D"]}
    >>> embeddings = {
    ...     "A": [1.0, 1.0], "B": [1.1, 1.1],  # Cluster 0: centered around [1.05, 1.05]
    ...     "C": [5.0, 5.0], "D": [5.1, 5.1]   # Cluster 1: centered around [5.05, 5.05]
    ... }
    >>> # Global centroid ~ [3.025, 3.025]
    >>> # Cluster 1 is farther from global centroid → more distinctive
    >>> cluster_by_centroid_global(clusters, embeddings)
    [1, 0]  # Cluster 1 first (most distinctive), then Cluster 0
    """
    """
    Optimized version with vectorized operations and single pass.
    """
    # Precompute all embeddings as array for vectorization
    all_inputs = []
    cluster_sizes = {}
    cluster_indices = {}

    start_idx = 0
    for cluster_id, members in clusters.items():
        if members:  # Skip empty clusters
            all_inputs.extend(members)
            cluster_sizes[cluster_id] = len(members)
            cluster_indices[cluster_id] = (start_idx, start_idx + len(members))
            start_idx += len(members)

    if not all_inputs:
        return []

    # Single vectorized embedding lookup
    embedding_matrix = np.array([embeddings[inp] for inp in all_inputs])

    # Global centroid (once)
    global_centroid = np.mean(embedding_matrix, axis=0)

    # Compute cluster centroids and distances in vectorized way
    distances = {}
    for cluster_id, (start, end) in cluster_indices.items():
        cluster_vectors = embedding_matrix[start:end]
        cluster_centroid = np.mean(cluster_vectors, axis=0)
        dist = np.linalg.norm(cluster_centroid - global_centroid)
        distances[cluster_id] = dist

    return sorted(distances, key=distances.get, reverse=True)