# Loading Embeddings with Prefix & Limit
# ============================================================
import os

import numpy as np


def load_embeddings_to_prioritize(run_dir, prefix, limit=1000):
    """
    Load embedding vectors for a given generator tool prefix from a specific run folder.
    """
    embeddings = {}
    count = 0

    for file in sorted(os.listdir(run_dir)):
        if not file.startswith(prefix) or not file.endswith("_vector.txt"):
            continue
        if count >= limit:
            break

        path = os.path.join(run_dir, file)
        try:
            vec = np.loadtxt(path)
            vec = np.ravel(vec)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            name = file.replace("_vector.txt", "")
            embeddings[name] = vec
            count += 1
        except Exception as e:
            print(f"[Warning] Skipped {file}: {e}")

    print(f"[INFO] Loaded {len(embeddings)} embeddings from {run_dir}")
    return embeddings