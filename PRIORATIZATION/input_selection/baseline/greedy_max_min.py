import random
import numpy as np
from scipy.spatial.distance import cdist
def select_max_min_diversification(embeddings_dict, previously_selected, budget):
    """
    Max–Min Diversification (Upper Baseline)
    -----------------------------------------
    Selects the most diverse set of test inputs from embedding space
    using the Farthest-First Traversal (Max–Min) strategy.

    Parameters
    ----------
    embeddings_dict : dict
        Mapping {input_name: embedding_vector}.
    previously_selected : set or list
        Inputs already chosen in smaller budgets (for monotonic growth).
    budget : int
        Target number of total inputs to select.

    Returns
    -------
    selected_order : list
        Ordered list of selected input names (monotonic selection).
    """

    # ==============================================================
    # Step 1 — Prepare data
    # ==============================================================
    all_inputs = list(embeddings_dict.keys())
    # name_to_index = {name: i for i, name in enumerate(all_inputs)}

    # Initialize selection structures
    selected_order = list(previously_selected)
    selected_set = set(previously_selected)

    # If no seed exists, randomly pick the first input
    if not selected_order:
        first_choice = random.choice(all_inputs)
        selected_order.append(first_choice)
        selected_set.add(first_choice)

    # ==============================================================
    # Step 2 — Compute initial distance array (minDist)
    # ==============================================================
    unselected = [name for name in all_inputs if name not in selected_set]

    X_sel = np.vstack([embeddings_dict[name] for name in selected_order])
    X_unsel = np.vstack([embeddings_dict[name] for name in unselected])

    dists = cdist(X_unsel, X_sel, metric="cosine")
    minDist = dists.min(axis=1)  # Distance to nearest selected input

    # ==============================================================
    # Step 3 — Iterative selection (farthest-first traversal)
    # ==============================================================
    while len(selected_order) < budget and len(unselected) > 0:
        # --- (a) Select farthest input ---
        next_idx = np.argmax(minDist)
        next_choice = unselected[next_idx]

        # --- (b) Add to selection ---
        selected_order.append(next_choice)
        selected_set.add(next_choice)

        # --- (c) Update minDist incrementally ---
        new_embedding = embeddings_dict[next_choice].reshape(1, -1)
        new_dists = cdist(X_unsel, new_embedding, metric="cosine").flatten()
        minDist = np.minimum(minDist, new_dists)

        # --- (d) Remove selected element from unselected pool ---
        del_idx = next_idx
        unselected.pop(del_idx)
        minDist = np.delete(minDist, del_idx)
        X_unsel = np.delete(X_unsel, del_idx, axis=0)

    # ==============================================================
    # Step 4 — Return monotonic, ordered set
    # ==============================================================
    return selected_order