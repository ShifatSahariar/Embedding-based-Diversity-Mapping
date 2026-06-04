

def select_cluster_size_based_with_pre_clusters(
    clusters,
    cluster_order,
    previously_selected,
    budget,
    debug=False,
    debug_prefix=""
):

    # ------------------------------------------------------------------
    # Step 0 — Normalize/prepare inputs
    # ------------------------------------------------------------------
    # Turn previously_selected into useful forms
    selected_order = list(previously_selected)
    selected_set = set(previously_selected)

    total_selected_before = len(selected_set)
    if debug:
        print(f"{debug_prefix}[DEBUG] --- Cluster-based selection call ---")
        print(f"{debug_prefix}[DEBUG] budget={budget}, prev_selected={total_selected_before}")

    # If we already have >= budget items, just return what we have
    if total_selected_before >= budget:
        if debug:
            print(f"{debug_prefix}[DEBUG] Already have >= budget items; returning previous selection.")
        return selected_order

    # Filter clusters so we don't accidentally reselect previously_selected items
    # NOTE: we create a *local* copy; we do NOT mutate the original `clusters`.
    remaining_in_cluster = {
        lbl: [x for x in members if x not in selected_set]
        for lbl, members in clusters.items()
    }

    # Keep only labels that appear in clusters (for safety)
    ordered_labels = [lbl for lbl in cluster_order if lbl in remaining_in_cluster]
    num_clusters = len(ordered_labels)

    if num_clusters == 0:
        if debug:
            print(f"{debug_prefix}[DEBUG] No clusters available (num_clusters=0).")
        return selected_order  # nothing more can be selected

    # Compute how many *new* inputs we still need
    need_new = budget - total_selected_before

    # Also compute the maximum possible (in case budget > available tests)
    total_available_now = sum(len(v) for v in remaining_in_cluster.values())
    to_add = min(need_new, total_available_now)

    if debug:
        print(f"{debug_prefix}[DEBUG] need_new={need_new}, "
              f"total_available_now={total_available_now}, will_add={to_add}")
        print(f"{debug_prefix}[DEBUG] num_clusters={num_clusters} "
              f"(first 10 labels: {ordered_labels[:10]})")

    if to_add <= 0:
        if debug:
            print(f"{debug_prefix}[DEBUG] Nothing to add (to_add <= 0).")
        return selected_order

    # ------------------------------------------------------------------
    # Step 1 — Round-robin over clusters using global position
    # ------------------------------------------------------------------
    # We will track how many *total* items have been selected so far (old + new).
    # This is our "global index" into the conceptual infinite sequence of picks.
    #
    # global_index = len(previously_selected) before picking each new item.
    #
    # For each new item j (0..to_add-1):
    #   global_index = total_selected_before + j
    #   -> cluster_idx = global_index % num_clusters
    #   -> target cluster = ordered_labels[cluster_idx]
    #
    # If target cluster is empty, we move forward to the next non-empty cluster,
    # wrapping around (so we still follow cluster_order but skip exhausted ones).

    per_cluster_new_counts = defaultdict(int)  # for debug summary only
    added = 0

    while added < to_add:
        # This is the global index *before* adding the next element
        global_index = total_selected_before + added

        # Initial preferred cluster index based on global rotation
        base_idx = global_index % num_clusters
        chosen = None
        chosen_cluster = None

        # Try up to `num_clusters` clusters to find one that still has members
        for offset in range(num_clusters):
            ci = (base_idx + offset) % num_clusters
            lbl = ordered_labels[ci]
            members = remaining_in_cluster[lbl]

            if not members:
                continue  # this cluster is exhausted, skip

            # We found a cluster with remaining members.
            # Randomly pick one from inside this cluster.
            # (You can comment this line and use `.pop(0)` if you want deterministic.)
            idx = random.randrange(len(members))
            chosen = members.pop(idx)
            chosen_cluster = lbl
            break

        if chosen is None:
            # All clusters are exhausted — cannot add more
            if debug:
                print(f"{debug_prefix}[DEBUG] All clusters exhausted before reaching the desired 'to_add'.")
            break

        # Record the newly chosen input
        selected_order.append(chosen)
        selected_set.add(chosen)
        per_cluster_new_counts[chosen_cluster] += 1
        added += 1

        if debug:
            print(
                f"{debug_prefix}[DEBUG] global_index={global_index} -> "
                f"cluster={chosen_cluster}, picked_input={chosen}"
            )

    # ------------------------------------------------------------------
    # Step 2 — Debug summary per call (optional)
    # ------------------------------------------------------------------
    if debug:
        print(f"{debug_prefix}[DEBUG] Added {added} new inputs in this call.")
        # Print how many new inputs came from each cluster (sorted by cluster_order)
        if per_cluster_new_counts:
            print(f"{debug_prefix}[DEBUG] New inputs per cluster in this call:")
            for lbl in ordered_labels:
                cnt = per_cluster_new_counts.get(lbl, 0)
                if cnt > 0:
                    print(f"{debug_prefix}    Cluster {lbl}: +{cnt} new")

        print(f"{debug_prefix}[DEBUG] Total selected after call = {len(selected_order)}")
        print(f"{debug_prefix}[DEBUG] ----------------------------------------------")

    return selected_order


def select_cluster_by_centroid_with_pre_clusters(
    clusters,
    cluster_order,
    previously_selected,
    budget,
    debug=False,
    debug_prefix="[Centroid] "
):
    """
    Cluster–Centroid–Based Prioritization (Rotation Version)
    ========================================================
    Selects test inputs using a *global* round-robin across clusters
    following the given centroid-based `cluster_order`.

    Key idea:
      - We see the whole experiment as one long sequence of picks.
      - global_index = how many inputs this method has already selected
                       before adding each new one.
      - For each new pick, we map global_index -> a cluster via:
          cluster_idx = global_index % num_clusters
          cluster_label = cluster_order[cluster_idx]
        (with skipping of exhausted clusters).

    This ensures:
      - Monotonicity across budgets (larger budget = superset).
      - We don't get stuck in C1..Ck only; we visit all clusters early.
      - We still respect `cluster_order` as the rotation order.

    Parameters
    ----------
    clusters : dict
        {cluster_label: [list_of_input_names]} precomputed once per run.
        (This function does NOT mutate the original dict.)
    cluster_order : list
        Cluster labels prioritized by centroid distances (farthest-first).
    previously_selected : set | list
        Inputs already chosen in smaller budgets (for monotonic selection).
    budget : int
        Target number of total inputs to select.
    debug : bool
        If True, prints detailed information.
    debug_prefix : str
        Prefix for debug lines.

    Returns
    -------
    selected_order : list[str]
        Ordered list of selected input names (monotonic selection).
    """

    # --------------------------------------------------------------
    # Step 0 — Prepare previous selection & early exit
    # --------------------------------------------------------------
    selected_order = list(previously_selected)
    selected_set = set(previously_selected)

    total_before = len(selected_set)
    if debug:
        print(f"{debug_prefix}call: budget={budget}, prev_selected={total_before}")

    if total_before >= budget:
        if debug:
            print(f"{debug_prefix}already have >= budget; returning previous selection")
        return selected_order

    # --------------------------------------------------------------
    # Step 1 — Build local copy of remaining elements per cluster
    # --------------------------------------------------------------
    # Remove previously selected inputs from each cluster
    remaining_in_cluster = {
        lbl: [x for x in members if x not in selected_set]
        for lbl, members in clusters.items()
    }

    # Keep only labels that actually exist and have at least one member
    ordered_labels = [lbl for lbl in cluster_order if remaining_in_cluster.get(lbl)]
    num_clusters = len(ordered_labels)

    if num_clusters == 0:
        if debug:
            print(f"{debug_prefix}no clusters with remaining inputs.")
        return selected_order

    # How many NEW inputs do we still need to reach `budget`?
    need_new = budget - total_before
    total_avail = sum(len(v) for v in remaining_in_cluster.values())
    to_add = min(need_new, total_avail)

    if debug:
        print(f"{debug_prefix}need_new={need_new}, total_avail={total_avail}, will_add={to_add}")
        print(f"{debug_prefix}num_clusters={num_clusters} (labels: {ordered_labels[:10]}...)")

    if to_add <= 0:
        return selected_order

    # --------------------------------------------------------------
    # Step 2 — Rotation selection using global_index
    # --------------------------------------------------------------
    per_cluster_new_counts = defaultdict(int)  # just for debug
    added = 0

    while added < to_add:
        # Global index = how many this method has already selected *before*
        # adding the next one (old + newly added so far in this call).
        global_index = total_before + added

        # "Base" cluster index by rotation
        base_idx = global_index % num_clusters

        chosen = None
        chosen_cluster = None

        # Try up to `num_clusters` clusters, starting from base_idx and wrapping around,
        # to find one that still has remaining members.
        for offset in range(num_clusters):
            ci = (base_idx + offset) % num_clusters
            lbl = ordered_labels[ci]
            members = remaining_in_cluster.get(lbl, [])

            if not members:
                continue  # exhausted cluster, skip

            # We found a non-empty cluster: pick a random member from it
            idx = random.randrange(len(members))
            chosen = members.pop(idx)
            remaining_in_cluster[lbl] = members  # store back (not strictly needed)
            chosen_cluster = lbl
            break

        if chosen is None:
            # All clusters exhausted before we could add `to_add` items
            if debug:
                print(f"{debug_prefix}all clusters exhausted early.")
            break

        # Record selection
        selected_order.append(chosen)
        selected_set.add(chosen)
        per_cluster_new_counts[chosen_cluster] += 1
        added += 1

        if debug:
            print(
                f"{debug_prefix}global_index={global_index} -> "
                f"cluster={chosen_cluster}, picked={chosen}"
            )

    # --------------------------------------------------------------
    # Step 3 — Debug summary
    # --------------------------------------------------------------
    if debug:
        print(f"{debug_prefix}added {added} new inputs in this call.")
        if per_cluster_new_counts:
            print(f"{debug_prefix}new inputs per cluster in this call:")
            for lbl in ordered_labels:
                cnt = per_cluster_new_counts.get(lbl, 0)
                if cnt > 0:
                    print(f"{debug_prefix}  {lbl}: +{cnt}")
        print(f"{debug_prefix}total selected after call = {len(selected_order)}")
        print(f"{debug_prefix}----------------------------------------")

    return selected_order
import random
from collections import defaultdict

