
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

from PRIORATIZATION.prioritization_utils.cluster_analysis_inputs_selection import analyze_cluster_mutation_diversity
from PRIORATIZATION.prioritization_utils.prioritization_utils import compute_all_cluster_orders, compute_input_rankings
from PRIORATIZATION.prioritization_utils.run_approaches_combo import build_deterministic_cluster_methods, \
    run_deterministic_strategies, _single_run_non_deterministic


def run_selection_approaches(embeddings_dict, mut_profiles_dict, budgets=None, n_runs=20, n_jobs=1,cluster_analysis_dir=None):
    """
    Run all selection approaches (Random, Cluster-based, Max–Min) over multiple runs and budgets,
    computing mutation scores in a monotonic way.
    """

    if budgets is None:
        budgets = [5, 10, 20, 40, 80]
    selection_sequences = defaultdict(
        lambda: defaultdict(  # method → run_id → budget → ordered list
            lambda: defaultdict(list)
        )
    )
    results = defaultdict(lambda: defaultdict(list))
    # Clustering + Clusters Ranking + Input Rankings (compute once)
    clusters, cluster_orders, exemplar_map = compute_all_cluster_orders(
        embeddings_dict,
        n_jobs=n_jobs,
        min_cluster_size=None,
    )
    input_rankings = compute_input_rankings(clusters, embeddings_dict, exemplar_map, n_jobs=n_jobs)

    # we want to calculate gini of each cluster by MS values to evaluate clusters quality
    # Analyzing mutation behavior and diversity for each cluster
    analyze_cluster_mutation_diversity(clusters, mut_profiles_dict, cluster_analysis_dir)

    # Separating Deterministic vs Non-deterministic Strategies
    # ============================================================

    # DETERMINISTIC: Build all deterministic cluster-based methods
    deterministic_cluster_methods = build_deterministic_cluster_methods(
        cluster_orders, input_rankings
    )
    # NON-DETERMINISTIC: We'll handle these in the run loop
    # (Random selection within clusters with different strategies)

    # Run Deterministic Strategies ONCE
    # ============================================================
    print("Running deterministic strategies...")
    deterministic_results = run_deterministic_strategies(
        clusters, deterministic_cluster_methods,
        embeddings_dict, mut_profiles_dict, budgets,selection_sequences)
    # Merge deterministic results into main results
    for app, vals in deterministic_results.items():
        for b, scores in vals.items():
            # Repeat the same scores for all runs (since deterministic)
            results[app][b].extend(scores * n_runs)


    # Run Non-deterministic Strategies MULTIPLE TIMES
    # ============================================================
    print("Running non-deterministic strategies...")
    if n_jobs == 1:
        for r in range(n_runs):
            run_res = _single_run_non_deterministic(
                r, embeddings_dict, mut_profiles_dict, budgets,
                clusters, cluster_orders, input_rankings,selection_sequences)
            for app, vals in run_res.items():
                for b, scores in vals.items():
                    results[app][b].extend(scores)
    else:
        with ProcessPoolExecutor(max_workers=n_jobs) as ex:
            futures = [
                ex.submit(
                    _single_run_non_deterministic, r, embeddings_dict, mut_profiles_dict, budgets,
                    clusters, cluster_orders, input_rankings,selection_sequences)
                for r in range(n_runs)
            ]
            for fut in as_completed(futures):
                run_res = fut.result()
                for app, vals in run_res.items():
                    for b, scores in vals.items():
                        results[app][b].extend(scores)

    print("\n All runs completed successfully.")
    return results,selection_sequences
