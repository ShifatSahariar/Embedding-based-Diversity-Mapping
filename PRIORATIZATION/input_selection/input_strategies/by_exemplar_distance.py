import numpy as np


def inputs_by_exemplar_distance(clusters, embeddings, exemplar_map, direction="closest"):
    """
    Ranks cluster members by their distance from the cluster's exemplar.

    For each cluster, computes the Euclidean distance between each member's embedding
    and the exemplar's embedding, then sorts members by proximity to the exemplar.

    - Most representative members (closest to exemplar)
    - Potential outliers (farthest from exemplar)
    - How tightly clustered the group is

    Examples
    --------
    >>> clusters = {"A": [1, 2, 3]}
    >>> embeddings = {1: [0.1, 0.1], 2: [0.9, 0.9], 3: [0.2, 0.2]}
    >>> exemplars = {"A": 1}  # input 1 is exemplar
    >>> inputs_by_exemplar_distance(clusters, embeddings, exemplars)
    {"A": [1, 3, 2]}  # 1 (exemplar) closest, then 3, then 2 farthest
    """
    ranked = {}
    reverse = (direction == "farthest")

    for cluster_id, member_inputs in clusters.items():
        if len(member_inputs) <= 1:
            ranked[cluster_id] = member_inputs[:]
            continue

        exemplar_id = exemplar_map[cluster_id]
        exemplar_vec = embeddings[exemplar_id]

        # Vectorized: stack all member embeddings at once
        member_vectors = np.array([embeddings[inp] for inp in member_inputs])

        # Compute all distances in one operation (much faster for large clusters)
        differences = member_vectors - exemplar_vec
        distances = np.linalg.norm(differences, axis=1)

        # Sort using numpy argsort (often faster for large arrays)
        if reverse:
            sorted_indices = np.argsort(distances)[::-1]
        else:
            sorted_indices = np.argsort(distances)

        ranked[cluster_id] = [member_inputs[i] for i in sorted_indices]

    return ranked
