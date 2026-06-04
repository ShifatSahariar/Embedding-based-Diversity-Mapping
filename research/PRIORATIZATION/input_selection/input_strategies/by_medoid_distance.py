import numpy as np
from PRIORATIZATION.input_selection.cluster_strategies.utils import compute_medoid

def inputs_by_medoid_distance(clusters, embeddings, direction="closest"):
    """
        Ranks cluster members by distance to the cluster's medoid.

        The medoid is the actual cluster member that is most central (minimizes
        average distance to all other members). This provides a data-driven
        representative for ranking cluster members by representativeness.
        Examples
        --------
        >>> clusters = {0: ["A", "B", "C"]}
        >>> embeddings = {"A": [0.1, 0.1], "B": [0.2, 0.2], "C": [0.9, 0.9]}
        >>> # If B is medoid (most central), returns:
        >>> inputs_by_medoid_distance(clusters, embeddings)
        {0: ["B", "A", "C"]}  # B (medoid) closest to itself, then A, then C farthest
    """

    reverse = (direction == "farthest")
    ranked = {}

    for cluster_id, member_inputs in clusters.items():

        # trivial case
        if len(member_inputs) <= 1:
            ranked[cluster_id] = member_inputs[:]
            continue

        # ---- compute medoid for this cluster ----
        medoid_id = compute_medoid(embeddings, member_inputs)
        medoid_vec = embeddings[medoid_id]

        # ---- vectorized distance computation ----
        member_vectors = np.array([embeddings[i] for i in member_inputs])
        diffs = member_vectors - medoid_vec
        distances = np.linalg.norm(diffs, axis=1)

        # ---- sort ----
        idx_sorted = np.argsort(distances)
        if reverse:
            idx_sorted = idx_sorted[::-1]

        ranked_inputs = [member_inputs[i] for i in idx_sorted]
        ranked[cluster_id] = ranked_inputs

    return ranked
