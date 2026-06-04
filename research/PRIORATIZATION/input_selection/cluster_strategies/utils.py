import numpy as np

def compute_centroid(embeddings, ids):
    return np.mean([embeddings[i] for i in ids], axis=0)

def compute_medoid(embeddings, ids):
    from scipy.spatial.distance import cdist
    if len(ids) == 1:
        return ids[0]
    vecs = np.array([embeddings[i] for i in ids])
    dists = cdist(vecs, vecs, metric='euclidean')
    medoid_idx = np.argmin(np.sum(dists, axis=1))
    return ids[medoid_idx]



