import concurrent.futures
import csv
import os
import random
from itertools import combinations

import numpy as np
import pandas as pd

from CLUSTERING.Clustering_Algo_Operations import clustering
from COVERAGE_REPORTS.Coverage_Profile import cluster_region_map_with_profile
from Gini_Impurity_Analysis import calculate_and_save_gini_impurities
from Helper_Functions.HelperFunctions import load_vectors_from_files

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

def get_cluster_consistency_scores_only(pairs, cluster_map):
    """
    Returns a dictionary like {cluster_id: consistency_score} for compatibility.
    """
    full_result = rank_clusters_contrastive_consistency(pairs, cluster_map)
    return {cid: score for cid, score, _, _, _ in full_result}



def rank_clusters_contrastive_consistency(pairs, cluster_map):
    """
    Rank clusters based on contrastive pair consistency.

    Args:
        pairs: List of (id1, id2, label), where label ∈ {1: pos, 0: neg}
        cluster_map: Dict[int, List[int]] mapping cluster IDs to test input IDs

    Returns:
        List of (cluster_id, score, pos_count, neg_count, total_pairs), sorted by score (desc)
    """
    # Convert to fast lookup table
    pair_lookup = {(min(a, b), max(a, b)): label for a, b, label in pairs}

    ranked = []

    for cluster_id, inputs in cluster_map.items():
        pos = 0
        neg = 0
        total = 0

        for a, b in combinations(inputs, 2):
            key = (min(a, b), max(a, b))
            label = pair_lookup.get(key, None)

            if label is not None:
                total += 1
                if label == 1:
                    pos += 1
                else:
                    neg += 1
            else:
                continue

        score = (pos - neg) / total if total > 0 else 0
        ranked.append((cluster_id, score, pos, neg, total))

    # Sort from most contrastively consistent to least
    return sorted(ranked, key=lambda x: x[1], reverse=True)

def rank_files_within_clusters(cluster_map, file_scores):
    """
    Rank files within each cluster based on their mutation scores.

    Args:
        cluster_map: Dictionary mapping cluster IDs to lists of files.
        file_scores: Dictionary mapping files to their mutation scores.

    Returns:
        A dictionary mapping each cluster ID to a list of files, sorted by their mutation scores.
    """
    ranked_cluster_map = {}
    for cluster_id, files in cluster_map.items():
        ranked_files = sorted(files, key=lambda x: file_scores.get(x, 0), reverse=True)
        ranked_cluster_map[cluster_id] = ranked_files
    return ranked_cluster_map


def reverse_cluster_map(cluster_map):
    """
    Reorganize the cluster map so that each cluster ID maps to a list of inputs.

    Args:
        cluster_map: A dictionary mapping input identifiers to cluster IDs.

    Returns:
        new_cluster_map: A dictionary mapping cluster IDs to lists of input identifiers.
    """
    new_cluster_map = {}

    for input_id, cluster_id in cluster_map.items():
        # Ensure cluster_id is a string
        cluster_id = str(cluster_id)

        if cluster_id not in new_cluster_map:
            new_cluster_map[cluster_id] = []
        new_cluster_map[cluster_id].append(input_id)

    return new_cluster_map


def save_cluster_mapping_to_csv(cluster_map, save_path):
    """
    Save the cluster ID, total items, and corresponding files/inputs to a CSV file, sorted by Cluster ID.

    Args:
        cluster_map: A dictionary mapping cluster IDs to lists of files/inputs.
        save_path: The path where the CSV file should be saved.
    """
    # Reverse the cluster_map to get the correct structure
    corrected_cluster_map = reverse_cluster_map(cluster_map)

    # Create a list to store the rows of the CSV file
    csv_rows = []

    # Iterate through the corrected cluster map and prepare rows for the CSV
    for cluster_id, inputs in corrected_cluster_map.items():
        # Join inputs with commas for a single row
        input_list = ','.join(map(str, inputs))
        total_items = len(inputs)  # Count the total items
        csv_rows.append([cluster_id, total_items, input_list])

    # Convert the list of rows into a DataFrame
    cluster_df = pd.DataFrame(csv_rows, columns=["Cluster ID", "Total Items", "Inputs"])

    # Sort the DataFrame by "Cluster ID"
    cluster_df = cluster_df.sort_values(by="Cluster ID").reset_index(drop=True)

    # Save the DataFrame to a CSV file
    cluster_df.to_csv(save_path, index=False)


def proportional_sample_from_ranked_clusters(cluster_map, normalized_scores, sample_size):
    """
    Sample proportionally from ranked clusters based on their mutation scores.

    Args:
        cluster_map: Dictionary mapping cluster IDs to lists of ranked files.
        normalized_scores: Dictionary mapping cluster IDs to their normalized mutation scores.
        sample_size: The total number of samples to draw proportionally from all clusters.

    Returns:
        A list of sampled files.
    """
    samples = []
    for cluster_id, ranked_files in cluster_map.items():
        cluster_score = normalized_scores.get(cluster_id, 0)
        num_samples = int(sample_size * cluster_score)

        if num_samples > 0:
            samples.extend(ranked_files[:num_samples])

    # Ensure we have the desired sample_size by adding remaining samples randomly
    if len(samples) < sample_size:
        remaining_samples = sample_size - len(samples)
        all_items = [item for sublist in cluster_map.values() for item in sublist]
        additional_samples = random.sample(all_items, remaining_samples)
        samples.extend(additional_samples)

    return samples


def save_best_k_to_csv(best_k_per_model_algo, save_results_path):
    """
    Save the best K values for each our_trained_models and algorithm to a CSV file.

    :param best_k_per_model_algo: Dictionary containing best K values for each our_trained_models and algorithm.
    :param save_results_path: Directory where the CSV file should be saved.
    """
    # Ensure the directory exists
    os.makedirs(save_results_path, exist_ok=True)

    # Define the CSV file path
    csv_file_path = os.path.join(save_results_path, "chosen_k_per_model_algo.csv")

    # Open the CSV file for writing
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Write the header row
        writer.writerow(["Model Name", "Cluster Algorithm", "Chosen K"])

        # Iterate through the best_k_per_model_algo dictionary and write each row
        for model_name, algo_k_map in best_k_per_model_algo.items():
            for algo, best_k in algo_k_map.items():
                writer.writerow([model_name, algo, best_k])

    print(f"Best K values have been saved to {csv_file_path}")


def save_tracking_table_to_csv(tracking_table, save_results_path):
    """
    Save the tracking table (our_trained_models name, algorithm, K, gini_impurity) to a CSV file.

    :param tracking_table: List of lists where each row contains [model_name, algo, K, gini_impurity].
    :param save_results_path: Path to save the CSV file.
    """
    # Ensure the directory exists
    os.makedirs(save_results_path, exist_ok=True)

    # Define the CSV file path
    csv_file_path = os.path.join(save_results_path, "K_Selection_Details.csv")

    # Write the table to the CSV
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow(["Model Name", "Algorithm", "K", "Gini Impurity"])

        # Write each row from the tracking table
        for row in tracking_table:
            writer.writerow(row)

    print(f"Tracking table saved to {csv_file_path}")


def filter_algorithms_requiring_k(clustering_algorithms):
    """
        Filters out the clustering algorithms that do not determine K themselves.

        :param clustering_algorithms: List of tuples (algorithm name, self_determining boolean)
        :return: A list of algorithms that require K (self_determining == False).
        """
    return [algo[0] for algo in clustering_algorithms if not algo[1]]


def k_selection_guided_by_Coverage_profile(clustering_algorithms, coverage_profile_count, vector_directories,
                                           filtered_data_map,profile_limit= None,min_k=2):
    """
        Perform clustering → calculate Gini impurity across different K values,
        and return the best K for each embedding our_trained_models and each clustering algorithm.

        :param min_k:
        :param profile_limit:
        :param clustering_algorithms: Full list of clustering_algorithms: we will filter which required K
        :param coverage_profile_count: Unique coverage profile counts from the filtered profiles.
        :param vector_directories: Dictionary containing our_trained_models names as keys and their
        corresponding vector profiles directories as values.
        :param filtered_data_map: A filtered mutation result map used for calculating Gini impurities.

        Returns:
            A dictionary where each our_trained_models name maps to a dictionary of clustering algorithms and their best K value.
            {

        "Model_A": {
            "KMeans": 8,
            "Agglomerative": 6,
            "GMM": 6,
            "Birch": 12
        },
        "Model_B": {
            "KMeans": 8,
            "Agglomerative": 12,
            "GMM": 8,
            "Birch": 8
        }
    }

        """
    print("k selection under process..")
    # Storing the best K for each our_trained_models and each algorithm
    best_k_per_model_algo = {}

    # List to track all combinations and their gini scores for easy summary (our_trained_models, algo, K, gini_impurity)
    K_details_tracking_table = []

    # Filtering the Cluster Algorithms from the list which has flag[FALSE]
    # meaning that they need to assign K by us
    # Sublist of algorithms that need to be assigned a number of clusters (K)
    clustering_algorithms_with_k = filter_algorithms_requiring_k(clustering_algorithms)

    # Ensure coverage_profile_count is meaningful for K selection
    if coverage_profile_count < min_k:
        print(f"coverage_profile_count={coverage_profile_count} is too small for clustering.")
        return best_k_per_model_algo, K_details_tracking_table

    # # Dynamically generate K values based on the filtered coverage count
    k_values = [max(coverage_profile_count // i, min_k) for i in range(20,40)]

    # # Remove duplicates and sort to avoid weird jumps
    # k_values_full = sorted(set(k_values))
    #
    # # Select 10 evenly spaced indices from the full list
    # indices = np.linspace(0, len(k_values_full) - 1, num=10, dtype=int)
    # k_values = [k_values_full[i] for i in indices]
    # Lower and upper bound
    # low_k = 1267
    # high_k = 1887
    #
    # # Generate 10 evenly spaced K values between 17 and 71
    # k_values = np.linspace(low_k, high_k, num=3, dtype=int).tolist()

    # Loop through vector models
    # For Each Embedding Model we are analyzing all the different combination with clustering algorithm
    # and choosing the K for each combination
    for model_name, directory in vector_directories.items():
        print(f"Processing our_trained_models: {model_name}")
        # Dictionary to store best K for each algorithm for the current our_trained_models
        best_k_for_algorithms = {}

        # Load vectors and their identifiers
        vectors, identifiers = load_vectors_from_files(directory, profile_limit=profile_limit)

        # Debugging: Print the number of loaded vectors and identifiers
        print(f"Loaded {len(vectors)} vectors and {len(identifiers)} identifiers from {directory}")

        # For each clustering algorithm, we are trying all the K
        # Select the best K with GINI(min) for each clustering Algo under the our_trained_models

        for algo in clustering_algorithms_with_k:
            print(f"Processing algorithm: {algo} for our_trained_models: {model_name}")
            best_k = None
            # Initialize to a large number
            best_gini_impurity_selected = float('inf')

            def process_k(k):
                """
                Function to perform clustering and compute Gini impurity for a given K.
                """
                print(f"Processing K={k} for {algo} on {model_name}")

                try:
                    # Perform clustering
                    cluster_map, _ = clustering(vectors, k, None, identifiers, algo=algo)

                    # Compute Gini impurity
                    cluster_data = cluster_region_map_with_profile(cluster_map, filtered_data_map)
                    gini_impurity = calculate_and_save_gini_impurities(cluster_data, None, model_name, algo)

                    # Track results
                    K_details_tracking_table.append([model_name, algo, k, gini_impurity])

                    return k, gini_impurity
                except Exception as e:
                    print(f"Error processing K={k} for {algo} on {model_name}: {e}")
                    return k, float('inf')  # Assign high impurity in case of failure


            # Use ThreadPoolExecutor to parallelize K selection
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(process_k, k) for k in k_values]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        k, gini_impurity = future.result()
                        # Select the best K based on lowest Gini impurity
                        if gini_impurity < best_gini_impurity_selected:
                            best_gini_impurity_selected = gini_impurity
                            best_k = k
                    except Exception as e:
                        print(f"Unexpected error during K processing: {e}")

            # Store the best K for the current algorithm
            best_k_for_algorithms[algo] = best_k
            # Store best Ks for the current model
        best_k_per_model_algo[model_name] = best_k_for_algorithms

    return best_k_per_model_algo, K_details_tracking_table

from collections import defaultdict

# Contrastive pairs (id1, id2, label)
# 1 = positive (similar), 0 = negative (dissimilar)
pairs = [
    (1, 2, 1),  # pos
    (1, 3, 1),  # pos
    (2, 3, 0),  # neg
    (4, 5, 0),  # neg
    (4, 6, 0),  # neg
    (5, 6, 0),  # neg
    (7, 8, 1),  # pos
    (7, 9, 1),  # pos
    (8, 9, 1),  # pos
    (10, 11, 0),  # neg
    (10, 12, 1),  # pos
    (11, 12, 0)   # neg
]

# Cluster assignments
cluster_map = {
    0: [1, 2, 3],     # Mixed cluster: 2 pos, 1 neg
    1: [4, 5, 6],     # All negative pairs
    2: [7, 8, 9],     # All positive pairs
    3: [10, 11, 12]   # Mixed again
}

cluster_scores = get_cluster_consistency_scores_only(pairs, cluster_map)
print(cluster_scores)
# for cid, score in cluster_scores:
#     print(f"Cluster {cid}: Score={score}")

