from functools import partial


from PRIORATIZATION.input_selection.input_strategies.selector_utils import random_selector, medoid_far_selector, \
    betweenness_selector, get_exemplar_selector_far, combined_selector_fn


# --- All combinations ---
def make_fixed_cluster_order_fn(order):
    def cluster_order_fn(clusters, embeddings):
        return order
    return cluster_order_fn

# we are combining our cluster prioritization with inputs prioritization technique
def build_cluster_methods_with_exemplars(orders, exemplar_map):
    input_fns = {
        "Random": random_selector,
        "Medoid-Far": medoid_far_selector,
        "Betweenness": betweenness_selector,
        "Exemplar_far": get_exemplar_selector_far(exemplar_map)
    }

    combinations = {}

    for cluster_name, order in orders.items():
        cluster_order_fn = make_fixed_cluster_order_fn(order)
        for input_name, input_selector in input_fns.items():
            method_name = f"{cluster_name} + {input_name}"
            combinations[method_name] = partial(
                combined_selector_fn,
                cluster_order_fn=cluster_order_fn,
                input_selector_fn=input_selector
            )

    return combinations



