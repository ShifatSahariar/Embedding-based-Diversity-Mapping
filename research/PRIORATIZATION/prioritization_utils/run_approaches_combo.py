from collections import defaultdict

import numpy as np

from PRIORATIZATION.input_selection.baseline.greedy_max_min import select_max_min_diversification
from PRIORATIZATION.input_selection.baseline.random_selection import select_random_lower_baseline
from PRIORATIZATION.prioritization_utils.ms_utils import compute_mutation_score_for_selected_inputs


def build_deterministic_cluster_methods(cluster_orders, input_rankings):
    """
    Build deterministic cluster-based selection methods including both
    exhaustive and round-robin approaches.
    """
    methods = {}

    # Define combinations for both exhaustive and round-robin
    deterministic_combinations = [
        # # EXHAUSTIVE strategies (current approach)
        # ("Size", "ExemplarDistance", "Size_Exemplar"),
        # ("Size", "GraphBetweenness", "Size_Betweenness"),
        # ("CentroidNovelty", "ExemplarDistance", "Novelty_Exemplar"),
        # ("CentroidNovelty", "GraphBetweenness", "Novelty_Betweenness"),
        # ("MedoidNovelty", "ExemplarDistance", "MedoidNovelty_Exemplar"),
        # ("MedoidNovelty", "GraphBetweenness", "MedoidNovelty_Betweenness"),
        # ("CentroidSpread", "ExemplarDistance", "Spread_Exemplar"),
        # ("CentroidSpread", "GraphBetweenness", "Spread_Betweenness"),

        # ROUND-ROBIN strategies (new)
        # ("Size", "ExemplarDistance", "Size_Exemplar_RR"),
        # ("Size", "GraphBetweenness", "Size_Betweenness_RR"),
        # ("CentroidNovelty", "ExemplarDistance", "Novelty_Exemplar_RR"),
        # ("CentroidNovelty", "GraphBetweenness", "Novelty_Betweenness_RR"),
        # ("MedoidNovelty", "ExemplarDistance", "MedoidNovelty_Exemplar_RR"),
        # ("MedoidNovelty", "GraphBetweenness", "MedoidNovelty_Betweenness_RR"),
        ("CentroidSpread", "ExemplarDistance", "SpreadEx_RR"),
        # ("CentroidSpread", "GraphBetweenness", "Spread_Betweenness_RR"),
    ]

    for cluster_strat, input_strat, method_name in deterministic_combinations:
        cluster_order = cluster_orders[cluster_strat]
        input_ranking = input_rankings[input_strat]

        # Choose selector type based on method name suffix
        if method_name.endswith("_RR"):
            methods[method_name] = create_round_robin_cluster_selector(
                cluster_order, input_ranking
            )
        else:
            methods[method_name] = create_deterministic_cluster_selector(
                cluster_order, input_ranking
            )

    return methods


def create_round_robin_cluster_selector(cluster_order, input_ranking):

    cluster_ptr = 0
    input_pointers = {cid: 0 for cid in cluster_order}

    def selector(clusters, previously_selected, needed_inputs, embeddings):

        nonlocal cluster_ptr
        new_inputs = []
        K = len(cluster_order)

        while len(new_inputs) < needed_inputs:

            for _ in range(K):
                cid = cluster_order[cluster_ptr]

                ranked = input_ranking.get(cid, [])
                ip = input_pointers[cid]

                # scan through ranked inputs
                while ip < len(ranked):
                    inp = ranked[ip]
                    ip += 1
                    input_pointers[cid] = ip

                    if inp not in previously_selected and inp not in new_inputs:
                        new_inputs.append(inp)
                        break

                # move to next cluster
                cluster_ptr = (cluster_ptr + 1) % K

                if len(new_inputs) >= needed_inputs:
                    break

            else:
                # no new inputs found
                break

        return new_inputs

    return selector


def create_deterministic_cluster_selector(cluster_order, input_ranking):
    cluster_pointer = 0  # persist across budgets

    def selector(clusters, previously_selected, needed_inputs, embeddings):

        nonlocal cluster_pointer
        new_inputs = []

        # total clusters
        K = len(cluster_order)

        while len(new_inputs) < needed_inputs:
            cluster_id = cluster_order[cluster_pointer]

            if cluster_id in clusters:
                ranked = input_ranking.get(cluster_id, [])
                for inp in ranked:
                    if inp not in previously_selected and inp not in new_inputs:
                        new_inputs.append(inp)
                        if len(new_inputs) >= needed_inputs:
                            break

            # move to next cluster
            cluster_pointer = (cluster_pointer + 1) % K

        return new_inputs

    return selector


def run_deterministic_strategies(
        clusters, deterministic_methods, embeddings_dict, mut_profiles_dict, budgets, selection_sequences, run_id=0 ):

    results = defaultdict(lambda: defaultdict(list))

    for method_name, selector in deterministic_methods.items():

        previously_selected = set()
        ordered_selection = []
        method_scores = []
        last_budget_size = 0

        for budget in budgets:
            needed = budget - last_budget_size

            new_inputs = selector(
                clusters=clusters,
                previously_selected=previously_selected,
                needed_inputs=needed,
                embeddings=embeddings_dict,
            )
            for inp in new_inputs:
                if inp not in previously_selected:
                    ordered_selection.append(inp)
            previously_selected.update(new_inputs)
            last_budget_size = len(previously_selected)
            selection_sequences[method_name][run_id][budget] = ordered_selection.copy()

            # compute MS on cumulative set
            full_selected = list(previously_selected)
            score = compute_mutation_score_for_selected_inputs(full_selected, mut_profiles_dict)
            method_scores.append(score)

        for b, s in zip(budgets, method_scores):
            results[method_name][b].append(s)

    return results


def _single_run_non_deterministic(
        run_idx: int,
        embeddings_dict: dict,
        mut_profiles_dict: dict,
        budgets: list,
        clusters: dict,
        cluster_orders: dict,
        input_rankings: dict,
        selection_sequences
):
    """
    Run non-deterministic strategies for a single run.
    """
    local_results = defaultdict(lambda: defaultdict(list))  # FIXED: Remove lambda

    # Non-cluster-based non-deterministic methods
    non_cluster_methods = {
        "Random": select_random_lower_baseline,
        # "Max-Min": select_max_min_diversification,
    }

    # Build random cluster methods (these create new functions each run)
    random_cluster_methods = build_random_cluster_methods(clusters, cluster_orders, input_rankings)

    # --- Non-cluster-based ---
    for function_name, func in non_cluster_methods.items():
        previously_selected = set()
        ordered_selection = []
        run_scores = []  # Track scores for this run

        for budget in budgets:
            selected_inputs = func(embeddings_dict, previously_selected, budget)
            for inp in selected_inputs:
                if inp not in previously_selected:
                    ordered_selection.append(inp)
            ms_score = compute_mutation_score_for_selected_inputs(selected_inputs, mut_profiles_dict)
            run_scores.append(ms_score)
            previously_selected.update(selected_inputs)
            selection_sequences[function_name][run_idx][budget] = ordered_selection.copy()

        # Store all budget scores for this run
        for budget, score in zip(budgets, run_scores):
            local_results[function_name][budget].append(score)

    # --- Cluster-based RANDOM ---
    # for function_name, func in random_cluster_methods.items():
    #     previously_selected = set()
    #     ordered_selection = []
    #     run_scores = []
    #     last_size = 0
    #
    #     for budget in budgets:
    #         needed = budget - last_size
    #
    #         new_inputs = func(
    #             clusters=clusters,
    #             previously_selected=previously_selected,
    #             needed_inputs=needed,  # <-- FIXED
    #             embeddings=embeddings_dict,
    #         )
    #         for inp in selected_inputs:
    #                 if inp not in previously_selected:
    #                     ordered_selection.append(inp)
    #         previously_selected.update(new_inputs)
    #         selection_sequences[method_name][run_idx][budget] = ordered_selection.copy()

    #         last_size = len(previously_selected)
    #
    #         # cumulative MS
    #         full_selected = list(previously_selected)
    #         ms_score = compute_mutation_score_for_selected_inputs(
    #             full_selected, mut_profiles_dict
    #         )
    #         run_scores.append(ms_score)
    #
    #     for budget, score in zip(budgets, run_scores):
    #         local_results[function_name][budget].append(score)
    #
    print(f"[Run {run_idx + 1}] ✅ Completed non-deterministic.")
    return local_results


def build_random_cluster_methods(clusters, cluster_orders, input_rankings):
    """
    Build methods that use deterministic cluster ordering but random input selection.
    Includes both exhaustive and round-robin approaches.
    """
    methods = {}

    random_combinations = [
        # # EXHAUSTIVE random strategies
        # ("Size", "Random", "Size_Random"),
        # ("CentroidNovelty", "Random", "Novelty_Random"),
        #
        # ("CentroidSpread", "Random", "Spread_Random"),

        # ROUND-ROBIN random strategies (new)
        # ("Size", "Random", "Size_Random_RR"),
        # ("CentroidNovelty", "Random", "Novelty_Random_RR"),
        # ("CentroidSpread", "Random", "Spread_Random_RR"),
    ]

    for cluster_strat, input_strat, method_name in random_combinations:
        # Choose selector type based on method name suffix
        if method_name.endswith("_RR"):
            methods[method_name] = create_random_round_robin_selector(
                cluster_orders[cluster_strat],
                clusters
            )
        else:
            methods[method_name] = create_random_cluster_selector(
                cluster_orders[cluster_strat],
                clusters
            )

    return methods


def create_random_cluster_selector(cluster_order, clusters):

    # Persistent pointers + persistent RNG shuffles
    cluster_ptr = 0
    rng = np.random.RandomState()
    per_cluster_lists = {
        cid: rng.permutation(clusters[cid]).tolist()
        for cid in cluster_order if cid in clusters
    }
    per_cluster_pointers = {cid: 0 for cid in cluster_order}

    def selector(clusters, previously_selected, needed_inputs, embeddings):
        nonlocal cluster_ptr
        new_inputs = []
        K = len(cluster_order)

        while len(new_inputs) < needed_inputs:

            cid = cluster_order[cluster_ptr]
            ranked = per_cluster_lists.get(cid, [])
            ptr = per_cluster_pointers[cid]

            # Consume from shuffled list
            while ptr < len(ranked):
                inp = ranked[ptr]
                ptr += 1
                per_cluster_pointers[cid] = ptr

                if inp not in previously_selected and inp not in new_inputs:
                    new_inputs.append(inp)
                    break

            cluster_ptr = (cluster_ptr + 1) % K

            if all(per_cluster_pointers[c]*1 == len(per_cluster_lists.get(c, []))
                   for c in cluster_order):
                break

        return new_inputs

    return selector



def create_random_round_robin_selector(cluster_order, clusters):

    cluster_ptr = 0
    rng = np.random.RandomState()

    per_cluster_lists = {
        cid: rng.permutation(clusters[cid]).tolist()
        for cid in cluster_order if cid in clusters
    }
    per_cluster_pointers = {cid: 0 for cid in cluster_order}

    def selector(clusters, previously_selected, needed_inputs, embeddings):
        nonlocal cluster_ptr
        new_inputs = []
        K = len(cluster_order)

        while len(new_inputs) < needed_inputs:

            for _ in range(K):

                cid = cluster_order[cluster_ptr]
                ranked = per_cluster_lists.get(cid, [])
                ptr = per_cluster_pointers[cid]

                # Consume items round-robin
                while ptr < len(ranked):
                    inp = ranked[ptr]
                    ptr += 1
                    per_cluster_pointers[cid] = ptr

                    if inp not in previously_selected and inp not in new_inputs:
                        new_inputs.append(inp)
                        break

                cluster_ptr = (cluster_ptr + 1) % K

                if len(new_inputs) >= needed_inputs:
                    break
            else:
                break

        return new_inputs

    return selector
