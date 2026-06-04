
import numpy as np


def cluster_by_medoid_novelty(clusters, embeddings,medoids=None):
    """
    Ranks clusters by the novelty of their medoids relative to the global data distribution.

    Computes the global centroid (mean of all embeddings), then measures how far
    each cluster's medoid is from this global center. Clusters with medoids farther
    from the global centroid are considered more novel/unusual and ranked higher.

    Examples
    --------
    >>> clusters = {0: ["A", "B"], 1: ["C", "D"]}
    >>> embeddings = {
    ...     "A": [1.0, 1.0], "B": [1.1, 1.1],  # Cluster 0 medoid ~ "A" or "B"
    ...     "C": [5.0, 5.0], "D": [5.1, 5.1]   # Cluster 1 medoid ~ "C" or "D"
    ... }
    >>> # Global centroid ~ [3.025, 3.025]
    >>> # Cluster 1 medoid is farther from global center → more novel
    >>> cluster_by_medoid_novelty(clusters, embeddings)
    [1, 0]  # Cluster 1 first (most novel), then Cluster 0
    """

    if not clusters:
        return []

    # Vectorized global centroid computation
    all_embeddings = []
    for members in clusters.values():
        if members:
            all_embeddings.extend([embeddings[i] for i in members])

    if not all_embeddings:
        return []

    global_centroid = np.mean(all_embeddings, axis=0)

    # Compute distances
    distances = {}
    for label, members in clusters.items():
        if not members:
            continue

        # Get medoid - with better fallback strategy
        if medoids and label in medoids:
            medoid_id = medoids[label]
        else:
            # Better fallback: use actual medoid computation if available
            # This is more accurate than using first member
            from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_medoid
            medoid_id = compute_medoid(embeddings, members)

        dist = np.linalg.norm(embeddings[medoid_id] - global_centroid)
        distances[label] = dist

    return sorted(distances, key=distances.get, reverse=True)