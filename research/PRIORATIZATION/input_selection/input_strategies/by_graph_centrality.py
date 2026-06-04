import networkx as nx
import numpy as np
from scipy.spatial.distance import squareform, pdist


def select_by_graph_betweenness(clusters, embeddings, threshold=None):
    """
    Ranks cluster members by betweenness centrality in a similarity graph.

    For each cluster, constructs a graph where:
    - Nodes = cluster members
    - Edges = connect members with similarity above threshold
    Then computes betweenness centrality to find 'bridge' nodes that connect
    different subgroups within the cluster.

    Examples
    --------
    >>> clusters = {0: ["A", "B", "C"]}
    >>> embeddings = {"A": [0.1, 0.1], "B": [0.2, 0.2], "C": [0.9, 0.9]}
    >>> select_by_graph_betweenness(clusters, embeddings)
    {0: ["B", "A", "C"]}  # B might be the bridge between A and C
    """
    ranked = {}

    for cluster_id, member_inputs in clusters.items():
        if len(member_inputs) <= 1:
            ranked[cluster_id] = member_inputs[:]
            continue

        # Vectorized distance computation (same as original)
        vecs = np.array([embeddings[i] for i in member_inputs])
        pairwise_dists = squareform(pdist(vecs, metric='euclidean'))
        labels = list(member_inputs)

        # Auto-threshold
        t = threshold if threshold is not None else np.median(pairwise_dists)

        # Vectorized edge construction
        G = nx.Graph()
        G.add_nodes_from(labels)

        # Find all pairs below threshold in one operation
        rows, cols = np.where(pairwise_dists <= t)
        edges = [(labels[i], labels[j], 1.0 - pairwise_dists[i, j])
                 for i, j in zip(rows, cols) if i < j]

        G.add_weighted_edges_from(edges)

        # Handle disconnected graphs
        if G.number_of_edges() == 0:
            # Fallback: use original order or distance-based ranking
            ranked[cluster_id] = member_inputs[:]
            continue

        centrality = nx.betweenness_centrality(G)
        ranked_inputs = sorted(centrality, key=centrality.get, reverse=True)
        ranked[cluster_id] = ranked_inputs

    return ranked