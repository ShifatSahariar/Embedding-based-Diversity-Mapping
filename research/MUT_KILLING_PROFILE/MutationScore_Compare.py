import random
from collections import defaultdict

# Example usage
cluster_map = {
    0: ['file2', 'file3'],
    1: ['file1', 'file4'],

}

mutation_profiles = {
    'file1': ['1', '0', '1', '1', '0'],
    'file2': ['0', '0', '0', '0', '0'],
    'file3': ['1', '1', '1', '1', '1'],
    'file4': ['0', '1', '0', '1', '0'],

}


def convert_cluster_map(cluster_map):
    """
    Convert the flat cluster_map to a dictionary where each cluster ID maps to a list of files.
    """
    converted_map = defaultdict(list)
    for file, cluster_id in cluster_map.items():
        converted_map[cluster_id].append(file)
    return dict(converted_map)


def normalize_scores(cluster_scores):
    """
    Normalize the mutation scores across clusters.
    Args:
        cluster_scores: Dictionary mapping cluster IDs to their mutation scores.
    Returns:
        A dictionary mapping each cluster ID to its normalized score.
    """
    total_score = sum(cluster_scores.values())

    if total_score == 0:
        print("Warning: Total mutation score is 0. Assigning uniform probability to clusters.")
        # Assign equal probability to all clusters if total_score is 0
        cluster_count = len(cluster_scores)
        return {cluster_id: 1.0 / cluster_count if cluster_count > 0 else 0 for cluster_id in cluster_scores}

    normalized_scores = {cluster_id: score / total_score for cluster_id, score in cluster_scores.items()}
    return normalized_scores



def proportional_sample_from_clusters_no_random(cluster_map, normalized_scores, sample_size, exclude=None):
    """
    Proportional sampling from clusters based on normalized scores,
    excluding previously selected files to support monotonic growth.

    Args:
        cluster_map: Dictionary mapping cluster IDs to lists of files.
        normalized_scores: Dictionary mapping cluster IDs to their normalized scores.
        sample_size: Number of new items to select.
        exclude: Optional set or list of previously selected items.

    Returns:
        A list of newly sampled files (excluding any already in `exclude`).
    """
    samples = []
    exclude_set = set(exclude) if exclude else set()
    # Sort clusters by normalized scores in descending order
    # Higher-scoring clusters will be sampled first.
    sorted_clusters = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)

    for cluster_id, _ in sorted_clusters:
        # Filter available items in cluster to exclude already selected items
        items = [item for item in cluster_map[cluster_id] if item not in exclude_set]

        if not items:
            continue

        cluster_score = normalized_scores.get(cluster_id, 0)
        num_samples = int(sample_size * cluster_score)

        if num_samples > 0:
            to_sample = min(num_samples, len(items), sample_size - len(samples))
            samples.extend(random.sample(items, to_sample))

        if len(samples) >= sample_size:
            break

    # Ensure we have the desired sample_size by continuing to select from top clusters
    # Second pass: If we haven't collected enough samples, continue sampling.
    # This is necessary because rounding during proportional sampling may leave us short.
    # If rounding or small clusters caused under sampling, fill remaining slots
    if len(samples) < sample_size:
        remaining_samples = sample_size - len(samples)
        for cluster_id, _ in sorted_clusters:
            items = [item for item in cluster_map[cluster_id] if item not in exclude_set and item not in samples]
            if not items:
                continue
            to_sample = min(remaining_samples, len(items))
            samples.extend(random.sample(items, to_sample))
            remaining_samples = sample_size - len(samples)
            if remaining_samples <= 0:
                break

    return samples


def calculate_cluster_mutation_scores(cluster_map, mutation_profiles):
    if not mutation_profiles:
        raise ValueError("mutation_profiles is empty. Please check the result loading/generation process.")

    cluster_scores = {}
    total_mutants = len(next(iter(mutation_profiles.values())))  # Ensure we get the right number of mutants

    for cluster_id, files in cluster_map.items():
        killed_mutants = [0] * total_mutants  # Track mutants killed in this cluster

        for file in files:
            profile = mutation_profiles.get(str(file))  # Ensure key is a string
            if profile is None:
                print(f"No mutation profile found for file {file}")
                continue

            # Debugging: Show before and after profile merging
            # print(f"🔍 Cluster {cluster_id}: Before Updating: {killed_mutants}")
            # print(f"🔍 Profile: {profile}")
            killed_mutants = [max(killed_mutants[i], profile[i]) for i in range(total_mutants)]
            # print(f"🔍 Cluster {cluster_id}: After Updating: {killed_mutants}")

        mutation_score = sum(killed_mutants) / total_mutants if total_mutants > 0 else 0
        cluster_scores[cluster_id] = mutation_score

    return cluster_scores


# def calculate_cluster_mutation_scores(cluster_map, mutation_profiles):
#
#
#     """
#     Calculate the mutation score for each cluster based on the profiles of inputs within that cluster.
#
#     Args:
#         cluster_map: Dictionary mapping cluster IDs to lists of files.
#         mutation_profiles: Dictionary mapping files to their mutation profiles.
#
#     Returns:
#         A dictionary mapping each cluster ID to its mutation score.
#
#     Example:
#         Consider a cluster with the following input profiles:
#
#         Cluster 1:
#             File 1: [0, 1, 0, 0, 1]  # Mutant 2 and Mutant 5 killed
#             File 2: [1, 1, 0, 0, 0]  # Mutant 1 and Mutant 2 killed
#             File 3: [0, 0, 0, 0, 1]  # Mutant 5 killed
#
#         Initialization:
#             killed_mutants = [0, 0, 0, 0, 0] # Initially, no mutants are killed
#
#         Process:
#             After processing File 1:
#                 killed_mutants = [0, 1, 0, 0, 1]  # Mutants 2 and 5 killed
#             After processing File 2:
#                 killed_mutants = [1, 1, 0, 0, 1]  # Mutants 1, 2, and 5 killed
#             After processing File 3:
#                 killed_mutants = [1, 1, 0, 0, 1]  # No change
#
#         Mutation Score:
#             For Cluster 1: mutation_score = sum(killed_mutants) / total_mutants = 3/5 = 0.6
#     """
#     # Check if mutation_profiles is empty
#     if not mutation_profiles:
#         raise ValueError("mutation_profiles is empty. Please check the result loading or generation process.")
#     cluster_scores = {}
#
#     for cluster_id, files in cluster_map.items():
#         # Initialize counters
#         total_mutants = len(next(iter(mutation_profiles.values())))
#         killed_mutants = [0] * total_mutants
#
#         # Check if each mutant is killed in any of the files within the cluster
#         for file in files:
#             profile = mutation_profiles.get(file)
#             if profile:
#                 killed_mutants = [max(killed_mutants[i], profile[i]) for i in range(total_mutants)]
#
#         # Calculate mutation score for the cluster
#         mutation_score = sum(killed_mutants) / total_mutants
#         cluster_scores[cluster_id] = mutation_score
#     # return all the mutation score for all the clusters
#     return cluster_scores


def evaluate_mutation_scores(input_files_selected_as_sample, mutation_profiles):
    """
    Calculate the mutation score for a given list of selected input files, treating them as a single entity.

    Args:
        input_files_selected_as_sample: List of selected input files (samples).
        mutation_profiles: Dictionary mapping files to their mutation profiles.

    Returns:
        The mutation score for the combined samples.

            __>>> SELECTED SAMPLE FILES LETS SAY
            File 1: [0, 1, 0, 0, 1]  # Mutant 2 and Mutant 5 killed
            File 2: [1, 1, 0, 0, 0]  # Mutant 1 and Mutant 2 killed
            File 3: [0, 0, 0, 0, 1]  # Mutant 5 killed

        Initialization:
            killed_mutants = [0, 0, 0, 0, 0] # Initially, no mutants are killed

        Process:
            After processing File 1:
                killed_mutants = [0, 1, 0, 0, 1]  # Mutants 2 and 5 killed
            After processing File 2:
                killed_mutants = [1, 1, 0, 0, 1]  # Mutants 1, 2, and 5 killed
            After processing File 3:
                killed_mutants = [1, 1, 0, 0, 1]  # No change

        Mutation Score:
            For Cluster 1: mutation_score = sum(killed_mutants) / total_mutants = 3/5 = 0.6
    """
    # Return 0 if no input files are selected
    if not input_files_selected_as_sample:
        return 0

    # Determine the total number of mutants by checking the length of any mutation profile
    total_mutants = len(next(iter(mutation_profiles.values())))

    # Initialize a list to track whether each mutant has been killed across all selected input files
    killed_mutants = [0] * total_mutants

    # Process each input file's mutation profile
    for input_file in input_files_selected_as_sample:
        # Getting the mutation profile for the current input file
        profile = mutation_profiles.get(str(input_file))  # Converting input_file to string
        if profile is None:
            print(f"No profile found for input file {input_file}")
            continue  # Skip if no profile is found

            # Update killed_mutants list
        killed_mutants = [max(killed_mutants[i], profile[i]) for i in range(total_mutants)]

        # if profile:
        #     # Update the killed_mutants list:
        #     if any mutant is killed in the current profile, mark it as killed
        #     killed_mutants = [max(killed_mutants[i], profile[i]) for i in range(total_mutants)]

    # Calculate the mutation score as the ratio of killed mutants to the total number of mutants
    mutation_score = sum(killed_mutants) / total_mutants

    # Return the mutation score for the combined input files
    return mutation_score


def run_greedy_mutation_multiple_times(test_profiles, sample_sizes, runs=10):
    """
    Run the greedy mutation score multiple times for different sample sizes and store the results.

    Args:
        test_profiles: Dictionary mapping input IDs to their mutation profiles (lists of 0s and 1s).
        sample_sizes: List of sample sizes to evaluate.
        runs: Number of runs to perform.

    Returns:
        all_greedy_scores: A dictionary with sample sizes as keys and a list of mutation scores per run as values.
        selected_inputs_per_size: A dictionary with sample sizes as keys and lists of selected inputs per run.
        greedy_selected_counts: A dictionary storing how many inputs were actually selected per run for each sample size.
    """
    # sample sizes as keys and a list of mutation scores per run as values
    all_greedy_scores = {sample_size: [] for sample_size in sample_sizes}
    # sample sizes as keys and lists of selected inputs per run.
    selected_inputs_per_size = {sample_size: [] for sample_size in sample_sizes}
    greedy_selected_counts = {sample_size: [] for sample_size in sample_sizes}

    for _ in range(runs):
        for sample_size in sample_sizes:
            # Selecting input profiles greedily - only from test profiles
            selected_inputs, mutation_score = greedy_mutation_score_with_sample_size(test_profiles, sample_size)
            all_greedy_scores[sample_size].append(mutation_score)
            selected_inputs_per_size[sample_size].append(selected_inputs)
            greedy_selected_counts[sample_size].append(len(selected_inputs))  # Track the actual number of inputs selected

    return all_greedy_scores, selected_inputs_per_size, greedy_selected_counts


def calculate_fair_greedy_run(train_profiles, test_profiles, sample_sizes):
    """
    Performs one run of a fair greedy selection and scoring process.
    - Selection is guided by train_profiles.
    - Scoring is done on test_profiles.

    Args:
        train_profiles: Mutation profiles for the training mutants of the current run.
        test_profiles: Mutation profiles for the testing mutants of the current run.
        sample_sizes: List of sample sizes to evaluate.

    Returns:
        A dictionary of {sample_size: mutation_score} for this single run.
    """
    scores_for_this_run = {}
    max_sample = max(sample_sizes) if sample_sizes else 0

    # --- 1. SELECTION PHASE (using train_profiles) ---
    # Determine the greedy order of inputs based on the training result.

    selected_inputs_in_order = []
    # Use a copy of the keys to avoid modifying the original dict during iteration
    remaining_input_ids = list(train_profiles.keys())

    # Set of mutants killed so far, according to the TRAIN profiles
    killed_train_mutants = set()
    train_total_mutants = len(next(iter(train_profiles.values())))

    while len(selected_inputs_in_order) < max_sample and len(remaining_input_ids) > 0:
        best_input = None
        max_new_kills = -1  # Use -1 to select an input even if it kills 0 new mutants

        for input_id in remaining_input_ids:
            profile = train_profiles[input_id]
            # Count how many NEW mutants this input kills
            new_kills = len(set(i for i, val in enumerate(profile) if val == 1) - killed_train_mutants)

            if new_kills > max_new_kills:
                max_new_kills = new_kills
                best_input = input_id

        # If no input can kill any new mutants, break the loop
        if best_input is None:
            break

        # Add the best input to our ordered list and update the state
        selected_inputs_in_order.append(best_input)
        remaining_input_ids.remove(best_input)
        # Update the set of killed mutants from the training perspective
        for i, val in enumerate(train_profiles[best_input]):
            if val == 1:
                killed_train_mutants.add(i)

    # --- 2. SCORING PHASE (using test_profiles) ---
    # Now, evaluate the performance of the greedily selected inputs on the test result.

    total_test_mutants = len(next(iter(test_profiles.values())))

    for sample_size in sample_sizes:
        # Take the first `n` inputs from our greedy ordering
        current_sample = selected_inputs_in_order[:sample_size]

        # Calculate the score for this sample on the test profiles
        killed_test_mutants = set()
        for input_id in current_sample:
            if input_id in test_profiles:
                for i, val in enumerate(test_profiles[input_id]):
                    if val == 1:
                        killed_test_mutants.add(i)

        mutation_score = len(killed_test_mutants) / total_test_mutants if total_test_mutants > 0 else 0
        scores_for_this_run[sample_size] = mutation_score

    return scores_for_this_run
def greedy_mutation_score_with_sample_size(profiles, sample_size):
    """
   Greedy algorithm to select input profiles that maximize the number of killed mutants,
    prioritizing input profiles that kill the most previously non-killed mutants.

    Args:
        profiles: A dictionary where keys are input IDs and values are lists (mutation profiles)
                  representing which mutants are killed (1 for killed, 0 for not killed).
                  Example:
                  {
                      1: [0, 0, 0, 0, 0, 1, 1, 1, 1, 0],  # Input 1 kills mutants 6, 7, 8, 9
                      4: [1, 1, 1, 1, 0, 0, 0, 0, 0, 0],  # Input 4 kills mutants 1, 2, 3, 4
                      5: [0, 0, 0, 1, 0, 0, 0, 1, 1, 0],  # Input 5 kills mutants 4, 8, 9
                      7: [0, 1, 1, 0, 0, 0, 0, 1, 0, 0]   # Input 7 kills mutants 2, 3, 8
                  }

    Returns:
        selected_inputs: A list of selected input IDs (in the order they were selected).
        mutation_score: The final mutation score, calculated as the ratio of killed mutants
                        to the total number of mutants.

    Example Walkthrough:
        Suppose we have the following profiles:
        Input 1: [0, 0, 0, 0, 0, 1, 1, 1, 1, 0]  # Mutants 6, 7, 8, 9 are killed
        Input 4: [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]  # Mutants 1, 2, 3, 4 are killed
        Input 5: [0, 0, 0, 1, 0, 0, 0, 1, 1, 0]  # Mutants 4, 8, 9 are killed
        Input 7: [0, 1, 1, 0, 0, 0, 0, 1, 0, 0]  # Mutants 2, 3, 8 are killed

        Step 1: Start by selecting the input that kills the most mutants.
        - Input 1 kills mutants 6, 7, 8, 9 (4 mutants)
        - Input 4 kills mutants 1, 2, 3, 4 (4 mutants)
        - Input 5 kills mutants 4, 8, 9 (3 mutants, but 2 are already killed by Input 1)
        - Input 7 kills mutants 2, 3, 8 (3 mutants, but 2 are already killed by Input 1)

        Choose Input 4 because it kills 4 new mutants: Mutants 1, 2, 3, 4.

        Step 2: Continue by selecting the input that kills the most previously unkilled mutants.
        - Remaining mutants: [0, 0, 0, 0, 0, 1, 1, 1, 1, 0]
        - Input 1 kills mutants 6, 7, 8, 9 (all new)
        - Input 5 kills mutants 8, 9 (no new mutants)
        - Input 7 kills mutant 7 (already killed by Input 1)

        Step 3: Repeat until all mutants are killed or no more new mutants can be killed.
        :param profiles:
        :param sample_size:
    """

    profiles = {int(k): v for k, v in profiles.items()}

    total_mutants = len(profiles[next(iter(profiles))])  # Assuming all profiles have the same length
    killed_mutants = set()  # Set to track the killed mutants
    selected_inputs = []  # Track which inputs are selected

    while len(killed_mutants) < total_mutants and len(selected_inputs) < sample_size:
        best_input = None
        max_new_kills = 0

        # Iterate over each input to find the one that kills the most new mutants
        for input_id, profile in profiles.items():
            new_kills = 0
            for mutant_id, mutant_status in enumerate(profile):
                if mutant_status == 1 and mutant_id not in killed_mutants:
                    new_kills += 1

            # If this input kills more new mutants, update the best input
            if new_kills > max_new_kills:
                max_new_kills = new_kills
                best_input = input_id

        if best_input is None:
            break  # No more new mutants can be killed

        # Select the best input and update killed mutants
        selected_inputs.append(best_input)
        for mutant_id, mutant_status in enumerate(profiles[best_input]):
            if mutant_status == 1:
                killed_mutants.add(mutant_id)

    mutation_score = len(killed_mutants) / total_mutants
    return selected_inputs, mutation_score
