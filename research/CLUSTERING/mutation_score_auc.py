import os
import random

import numpy as np
from scipy.stats import ranksums
from sklearn.metrics import auc


from Helper_Functions.HelperFunctions import calculate_rse
from Helper_Functions.Mutation_Helping_Functions import compute_random_mutation_scores, calculate_random_run

from MUT_KILLING_PROFILE.MutationScore_Compare import convert_cluster_map, calculate_cluster_mutation_scores, \
    normalize_scores, evaluate_mutation_scores, \
    proportional_sample_from_clusters_no_random, run_greedy_mutation_multiple_times, calculate_fair_greedy_run


def calculate_cluster_diversity_scores(cluster_map, mutation_profiles):
    """
    Calculates a diversity score for each cluster based on the number of unique mutants killed by all inputs in that cluster.
    :param cluster_map: Dictionary: cluster_id -> list of input file names
    :param mutation_profiles: Dictionary: input file name -> list of 0/1 indicating killed mutants
    :return: Dictionary: cluster_id -> diversity score (float between 0 and 1)
    """
    total_mutants = len(next(iter(mutation_profiles.values())))
    cluster_diversity_scores = {}

    for cluster_id, input_ids in cluster_map.items():
        killed_mutants = set()
        for inp in input_ids:
            profile = mutation_profiles.get(str(inp), [])
            killed_mutants.update(i for i, val in enumerate(profile) if val == 1)

        diversity_score = len(killed_mutants) / total_mutants if total_mutants > 0 else 0
        cluster_diversity_scores[cluster_id] = diversity_score

    return cluster_diversity_scores


def prepare_profiles_for_pairing(profiles_dict, input_ids):
    """
    Takes a dictionary of mutation profiles and returns:
    - A list of binary int lists (0/1)
    - A list of corresponding input IDs
    """
    cleaned_profiles = []
    cleaned_ids = []

    for input_id in input_ids:
        profile = profiles_dict.get(input_id)
        if profile is not None:
            # Convert to int in case some values are still strings
            cleaned_profiles.append([int(b) for b in profile])
            cleaned_ids.append(input_id)
        else:
            print(f"Warning: Missing profile for {input_id}")

    return cleaned_profiles, cleaned_ids

def prepare_profiles_for_threshold_selection(mutation_profiles):
    """
    Ensures all profile values are ints (0 or 1).
    """
    return {
        k: [int(bit) for bit in v]
        for k, v in mutation_profiles.items()
    }

TRAIN_TEST_SPLIT_RATIO = 0.7

def test_profiles_mutation_score(vectors, identifiers, clustering_func,main_mutation_profiles,
                                 train_mutation_profiles,test_mutation_profiles,
                                all_random_scores, all_greedy_scores,greedy_selected_counts,
                                 sample_sizes, runs=10):
    """
        Running clustering multiple times and compute the mean and standard deviation of mutation scores,
        including both cluster-based and random-based scores.

        Returns:
            A list of summary results for each sample size containing mean mutation scores
            (cluster-based and random-based),
            standard deviation, RSE, and p-value for both methods.
            :param profile_limit:
            :param sample_sizes:List of sample sizes to evaluate scores.
            :param clustering_func:The clustering function to use.
            :param identifiers:The identifiers corresponding to the vectors.
        """

    # Initializing storage for mutation scores across different sample sizes
    all_cluster_scores = {sample_size: [] for sample_size in sample_sizes}
    all_greedy_scores = {size: [] for size in sample_sizes}
    all_random_scores = {size: [] for size in sample_sizes}
    # total number of mutants from the main profiles
    if not main_mutation_profiles:
        raise ValueError("main_mutation_profiles is empty.")
    total_mutants = len(next(iter(main_mutation_profiles.values())))

    for run in range(runs):
        # 1- 20 let's say
        print(f"Run {run + 1}/{runs} of Clustering :")

        all_mutant_indices = list(range(total_mutants))
        random.shuffle(all_mutant_indices)
        split_point = int(total_mutants * TRAIN_TEST_SPLIT_RATIO)
        train_indices_for_run = all_mutant_indices[:split_point]
        test_indices_for_run = all_mutant_indices[split_point:]
        # 3. Create the profile dictionaries dynamically for THIS RUN
        current_run_train_profiles = {
            input_file: [profile[i] for i in train_indices_for_run]
            for input_file, profile in main_mutation_profiles.items()
        }
        current_run_test_profiles = {
            input_file: [profile[i] for i in test_indices_for_run]
            for input_file, profile in main_mutation_profiles.items()
        }
        # Run clustering to get the cluster map
        cluster_map, _ = clustering_func(vectors, identifiers)
        cluster_map = convert_cluster_map(cluster_map)

        # SHUFFLING THE MUTANT INDICES TO INTRODUCE VARIABILITY ACROSS MULTIPLE RUNS

        # Get mutant indices for training and testing (Assuming first input's profile gives total count)
        # main_mutant_indices = list(range(len(next(iter(main_mutation_profiles.values())))))
        # train_mutant_indices = list(range(len(next(iter(train_mutation_profiles.values())))))
        # test_mutant_indices = list(range(len(next(iter(test_mutation_profiles.values())))))

        # # Shuffle train mutants while keeping them separate from test mutants
        # random.shuffle(train_mutant_indices)
        # # Shuffle test mutants separately without mixing with train mutants
        # random.shuffle(test_mutant_indices)
        #
        #
        # # APPLY SHUFFLED MUTANT ORDER TO ALL INPUT PROFILES TO ENSURE CONSISTENCY ACROSS INPUT FILES
        # shuffled_train_profiles = {
        #     input_file: [profile[i] for i in train_mutant_indices] for input_file, profile in
        #     train_mutation_profiles.items()
        # }
        # shuffled_test_profiles = {
        #     input_file: [profile[i] for i in test_mutant_indices] for input_file, profile in
        #     test_mutation_profiles.items()
        # }


        # PRIORITIZING THE CLUSTER - WITH TRAINING SET OF MUTATION PROFILES (AFTER SHUFFLING)
        cluster_scores = calculate_cluster_mutation_scores(cluster_map, current_run_train_profiles)
        # print(cluster_scores)
        # cluster_scores = get_cluster_consistency_scores_only(pairs, cluster_map)

        # Clean up the output just for printing
        readable_cluster_scores = {int(k): v for k, v in cluster_scores.items()}
        print("Cluster Scores Before Normalization:", readable_cluster_scores)

        # Normalize the mutation scores across clusters
        normalized_scores_for_clusters = normalize_scores(cluster_scores)
        cluster_diversity_scores = calculate_cluster_diversity_scores(cluster_map, current_run_train_profiles)

        # Normalize diversity scores like you do for Gini:
        normalized_diversity_scores = normalize_scores(cluster_diversity_scores)
        cumulative_cluster_samples = []

        for sample_size in sample_sizes:
            new_needed = sample_size - len(cumulative_cluster_samples)

            if new_needed > 0:
                new_samples = proportional_sample_from_clusters_no_random(
                    cluster_map,
                    normalized_scores_for_clusters,
                    new_needed,
                    exclude=cumulative_cluster_samples  # Avoid reelecting
                )
                cumulative_cluster_samples.extend(new_samples)

            # COMPUTE CLUSTER-BASED MUTATION SCORE USING THE SHUFFLED TESTING PROFILES
            # cluster_based_score = evaluate_mutation_scores(proportional_samples, shuffled_test_profiles)
            cluster_score = evaluate_mutation_scores(cumulative_cluster_samples, current_run_test_profiles)
            all_cluster_scores[sample_size].append(cluster_score)

        # --- B. Random Baseline Scores for this Run ---
        random_scores_this_run = calculate_random_run(current_run_test_profiles, sample_sizes)
        for sample_size in sample_sizes:
            all_random_scores[sample_size].append(random_scores_this_run[sample_size])

            # --- C. Greedy Baseline Scores for this Run (Fair Method) ---
        greedy_scores_this_run = calculate_fair_greedy_run(
            current_run_train_profiles,
            current_run_test_profiles,
            sample_sizes
            )
        for sample_size in sample_sizes:
            all_greedy_scores[sample_size].append(greedy_scores_this_run[sample_size])

            # SUMMARIZING FINAL MUTATION SCORE STATISTICS AFTER ALL RUNS
    summary_results = calculate_mutation_score_statistics(sample_sizes, all_cluster_scores, all_random_scores,
                                                                  runs,
                                                                  all_greedy_scores, greedy_selected_counts)

    return summary_results


def calculate_mutation_score_statistics(sample_sizes, all_cluster_scores, all_random_scores, runs, all_greedy_scores,
                                        greedy_selected_counts):
    summary_results = []

    for sample_size in sample_sizes:
        # for each sample size calculating the mean score from all the CLUSTER-BASED mutation scores
        # we will calculate the error
        # Calculate RSE to understand the stability of the variance of the selected profiles
        cluster_mean_score = np.mean(all_cluster_scores[sample_size])
        cluster_std_dev = np.std(all_cluster_scores[sample_size])
        cluster_rse = calculate_rse(cluster_mean_score, cluster_std_dev, runs)  # Calculate RSE

        # for each sample size calculating the mean score from all the RANDOM-BASED mutation scores
        # Calculate RSE to understand the stability of the variance of the selected profiles
        random_mean_score = np.mean(all_random_scores[sample_size])
        random_std_dev = np.std(all_random_scores[sample_size])
        random_rse = calculate_rse(random_mean_score, random_std_dev, runs)  # Calculate RSE

        # for each sample size calculating the mean score from all the Greedy-based scores
        greedy_mean_score = np.mean(all_greedy_scores[sample_size])
        greedy_std_dev = np.std(all_greedy_scores[sample_size])
        greedy_rse = calculate_rse(greedy_mean_score, greedy_std_dev, runs)
        # GOAL: Computer P-VALUE to understand the HYPOTHESIS
        # If we can reject the Null Hypothesis
        # Calculate p-value with Wilcoxon
        # since result in cluster_scores_for_each_sample and random_scores_for_each_sample are not paired:
        # we will use scipy.stats.ranksums
        cluster_scores_for_each_sample = all_cluster_scores[sample_size]
        random_scores_for_each_sample = all_random_scores[sample_size]

        # Wilcoxon test is not applicable if all differences are zero
        differences = np.array(cluster_scores_for_each_sample) - np.array(random_scores_for_each_sample)
        if np.all(differences == 0):
            p_value = 'N/A'
        else:
            # scipy.stats.ranksums is suitable when the result in the two lists are not paired or dependent,
            # which seems to be in our case since the cluster-based and random-based mutation scores are independent
            # across different runs.

            _, p_value = ranksums(cluster_scores_for_each_sample, random_scores_for_each_sample)

        # Prepare a summary for the mutation score comparison
        summary_results.append({
            "Sample Size": sample_size,
            "Cluster-Based Score[Mean]": cluster_mean_score,
            "RSE-Cluster[Ratio]": cluster_rse,
            "Random-Based Score[Mean]": random_mean_score,
            "RSE-Random[Ratio]": random_rse,
            "p-value [Cluster & Random]": p_value,
            "Greedy Mean Score": greedy_mean_score,
            # each run could be different input counts selected
            "Inputs Needed[Greedy]": np.mean(greedy_selected_counts[sample_size]),
            # # Inputs ID's such as [132,934,133]
            # "Selected Inputs I'd's[Greedy]": selected_inputs_per_size[sample_size],
            "RSE-Greedy[Ratio]": greedy_rse,
        })

    return summary_results

def calculate_greedy_and_random_scores(test_profiles, sample_sizes,runs):
    """
    Runs greedy and random mutation score calculations and returns the combined results.
    """


    combined_results = {}


    """GREEDY APPROACH: Compute Mutation Score using greedy selection ONLY ON TEST PROFILES 
    to select input profiles that maximize the number 
    of killed mutants, prioritizing input profiles that kill the most previously non-killed mutants. - we will 
    compare with this approach with other mutation scores such as (cluster based and random based mutation score"""
    # Greedy mutation score calculation
    all_greedy_scores, selected_inputs_per_size, greedy_selected_counts = run_greedy_mutation_multiple_times(
        test_profiles, sample_sizes, runs=runs)

    if all_greedy_scores and len(all_greedy_scores) > 0:
        # Compute mean greedy mutation scores per sample size
        mean_greedy_scores = [np.mean(all_greedy_scores[sample_size]) for sample_size in sample_sizes]
        # Compute AUC for greedy mutation scores
        greedy_auc = auc(sample_sizes, mean_greedy_scores)

        # Store greedy mutation results for the combined graph
        combined_results["Greedy"] = {"scores": mean_greedy_scores, "AUC": greedy_auc}

    """RANDOM APPROACH: Computing random-based mutation scores ONLY FROM TEST PROFILES
    # First, compute the random-based mutation scores ONCE
    """
    # Random mutation score calculation
    # We reuse these for each combination of vector our_trained_models and clustering algorithm
    all_random_scores = compute_random_mutation_scores(test_profiles, sample_sizes, runs)
    # Check if all_random_scores is not empty and is in the correct format
    if all_random_scores and len(all_random_scores) > 0:
        # Access the scores from the dictionary (assuming all_random_scores is a dictionary)
        mean_random_scores = [np.mean(all_random_scores[sample_size]) for sample_size in sample_sizes]
        # Compute AUC using sample sizes and their corresponding mean mutation scores
        random_auc = auc(sample_sizes, mean_random_scores)

        # Store results for the combined graph
        combined_results["Random"] = {"scores": mean_random_scores, "AUC": random_auc}

    # print(f"Final combined_results in calculate_greedy_and_random_scores: {combined_results}")
    print(f"Random Scores Generated: {all_random_scores}")

    return (combined_results, all_greedy_scores, selected_inputs_per_size,
            greedy_selected_counts, all_random_scores)
