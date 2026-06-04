from functools import partial

from PRIORATIZATION.input_selection.input_strategies.by_exemplar_distance import inputs_by_exemplar_distance
from PRIORATIZATION.input_selection.input_strategies.by_graph_centrality import select_by_graph_betweenness
from PRIORATIZATION.input_selection.input_strategies.by_medoid_distance import inputs_by_medoid_distance
from PRIORATIZATION.input_selection.input_strategies.random_in_cluster import select_random_in_cluster



def random_selector(cluster_inputs, embeddings, label=None):
    return select_random_in_cluster(cluster_inputs, embeddings)

def medoid_far_selector(cluster_inputs, embeddings, label=None):
    return inputs_by_medoid_distance(cluster_inputs, embeddings, direction='farthest')

def betweenness_selector(cluster_inputs, embeddings, label=None):
    return select_by_graph_betweenness(cluster_inputs, embeddings)

def exemplar_selector_far(cluster_inputs, embeddings, label, exemplar_map):
    exemplar_id = exemplar_map[label]
    return inputs_by_exemplar_distance(cluster_inputs, embeddings, exemplar_id=exemplar_id, direction="farthest")

# NEW: expose a top-level partial creator (pickleable)
def get_exemplar_selector_far(exemplar_map):
    return partial(exemplar_selector_far, exemplar_map=exemplar_map)


def combined_selector_fn(clusters, previously_selected, budget, embeddings, cluster_order_fn, input_selector_fn):
    cluster_order = cluster_order_fn(clusters, embeddings)

    selected_order = list(previously_selected)
    selected_set = set(previously_selected)
    total_before = len(selected_order)
    need_new = budget - total_before

    if need_new <= 0:
        return selected_order

    remaining = {
        lbl: [x for x in members if x not in selected_set]
        for lbl, members in clusters.items()
    }

    ordered_labels = [lbl for lbl in cluster_order if lbl in remaining and remaining[lbl]]
    num_clusters = len(ordered_labels)
    added = 0

    while added < need_new and ordered_labels:
        global_index = total_before + added
        base_idx = global_index % num_clusters
        chosen = None

        for offset in range(num_clusters):
            idx = (base_idx + offset) % num_clusters
            label = ordered_labels[idx]
            cluster_inputs = remaining[label]

            if not cluster_inputs:
                continue

            ranked = input_selector_fn(cluster_inputs, embeddings, label)
            for candidate in ranked:
                if candidate not in selected_set:
                    chosen = candidate
                    remaining[label].remove(candidate)
                    break

            if chosen:
                break

        if not chosen:
            break

        selected_order.append(chosen)
        selected_set.add(chosen)
        added += 1

    return selected_order


def make_combined_selector(cluster_order_fn, input_selector_fn):
    return partial(
        combined_selector_fn,
        cluster_order_fn=cluster_order_fn,
        input_selector_fn=input_selector_fn
    )
