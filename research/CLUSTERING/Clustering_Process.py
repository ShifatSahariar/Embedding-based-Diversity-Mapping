import concurrent.futures
import os
import shutil
import pandas as pd
from sklearn.metrics import auc

from CLUSTERING.Clustering_Algo_Operations import clustering
from CLUSTERING.mutation_score_auc import test_profiles_mutation_score, calculate_greedy_and_random_scores
from COVERAGE_REPORTS.Coverage_Profile import cluster_region_map_with_profile, process_coverage_data
from Gini_Impurity_Analysis import calculate_and_save_gini_impurities, save_summary_gini_impurity
from Helper_Functions.Cluster_Helping_Functions import save_cluster_mapping_to_csv, save_best_k_to_csv, \
    save_tracking_table_to_csv, k_selection_guided_by_Coverage_profile
from Helper_Functions.Coverage_Helping_Functions import get_coverage_filename
from Helper_Functions.HelperFunctions import load_vectors_from_files
from Helper_Functions.Visualization import plot_combined_mutation_scores
from MUT_KILLING_PROFILE.Mutation_killing_filter import load_mutation_killing_profiles


def clustering_process(vector_directories, clustering_algorithms, base_results_directory,save_cluster_result_path,
                       pca=1.0, runs=10, decimal_places=3, process_type="mutation",
                       subject_program='CALC',profile_limit=None):
    """
    → Clustering vectors from different directories and calculating the average Gini impurity.
    → Processes the specified profiles (mutation killing or statement coverage)
    → Runs clustering multiple times,
    → And saves relevant statistics.

    """
    # Samples: NUMBER OF INPUTS we want to retrieve from the CLUSTERS or RANDOMLY
    sample_sizes = list(range(1, 65, 1))

    os.makedirs(base_results_directory, exist_ok=True)

    base_train_test_profile_dir = f"../MUT_KILLING_PROFILE/{subject_program.upper()}"

    # Load training and testing profiles only ONCE, since we no longer have epochs
    main_profiles_dir = os.path.join(base_train_test_profile_dir, "mutants_killing_profiles")
    train_profiles_dir = os.path.join(base_train_test_profile_dir, "train_mut_kill_profiles")
    test_profiles_dir = os.path.join(base_train_test_profile_dir, "test_mut_kill_profiles")

    print("Loading Training Profiles from: " + train_profiles_dir)
    print("Loading Testing Profiles from: " + test_profiles_dir)

    # Loading mutation profiles for training and testing sets
    # default we will always load the first set of inputs [ means profiles for the first set of inputs for testing ]
    main_mutation_profiles = load_mutation_killing_profiles(main_profiles_dir, profile_limit=profile_limit)
    train_mutation_profiles = load_mutation_killing_profiles(train_profiles_dir, profile_limit=profile_limit)
    test_mutation_profiles = load_mutation_killing_profiles(test_profiles_dir, profile_limit=profile_limit)

    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>  START : OTHERS APPROACHES TO COMPARE <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    # Greedy and Random Mutation Score Calculation
    (combined_results_random_greedy, all_greedy_scores,
     selected_inputs_per_size, greedy_selected_counts,
     all_random_scores)= calculate_greedy_and_random_scores(test_mutation_profiles, sample_sizes,
                                                                           runs)
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>  END : OTHERS APPROACHES TO COMPARE <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # Get Unique Coverage Profile Count and Filtered Mutation Killing Profiles
    coverage_profile_count, _ = process_coverage_profile_for_K_selection(subject_program, save_cluster_result_path, profile_limit=profile_limit)


    save_results_path = save_cluster_result_path
    if os.path.exists(save_results_path):
        shutil.rmtree(save_results_path)
    os.makedirs(save_results_path)

    # Best K Selection for each our_trained_models + Cluster_algorithm
    # - coverage_profile_count + label with train mut profiles
    # tracking_table: details about the process to see all together.
    # Best_k_per_model_algo: Chosen K for each model+ cluster algo combo
    """ Best K according GINI IMPURITY """
    best_k_per_model_algo, tracking_table = k_selection_guided_by_Coverage_profile(clustering_algorithms,
                                                                                   coverage_profile_count,
                                                                                   vector_directories,
                                                                                   main_mutation_profiles,
                                                                                   profile_limit=profile_limit)

    # Loop through each vector our_trained_models and run clustering, Gini, and mutation score operations
    combined_results, gini_impurity_summary_data = clustering_gini_and_ms(vector_directories,
                                                                          clustering_algorithms,
                                                                          best_k_per_model_algo,
                                                                          train_mutation_profiles,
                                                                          main_mutation_profiles,
                                                                          test_mutation_profiles,
                                                                          combined_results_random_greedy,
                                                                          all_random_scores, all_greedy_scores,
                                                                          greedy_selected_counts,
                                                                          save_results_path,
                                                                          sample_sizes, pca, runs,
                                                                          process_type, decimal_places,
                                                                          profile_limit=profile_limit
                                                                          )

    # Generate a combined graph and summary Gini impurity report
    # save Csv for K values for our_trained_models+ cluster algo Combo
    # Save Gini Impurity
    # save AUC
    generate_final_reports(combined_results, gini_impurity_summary_data,
                           best_k_per_model_algo, tracking_table,sample_sizes, save_results_path, process_type, runs)

    return combined_results


def process_coverage_profile_for_K_selection(subject_program, save_cluster_result_path, profile_limit=None):
    """
    Processes the coverage and mutation profiles for a given subject program.
    """
    # depending on the subject program, we will select which file we should look for coverage result
    coverage_file = get_coverage_filename(subject_program)
    coverage_data_path = f"../COVERAGE_REPORTS/{subject_program.upper()}"
    print(f"Coverage Data path : {coverage_data_path}")
    coverage_filtered_data_map, coverage_profile_count = process_coverage_data(coverage_data_path,
                                                                               coverage_file,
                                                                               save_cluster_result_path,
                                                                               profile_limit=profile_limit,profile_set="first")

    return coverage_profile_count, coverage_filtered_data_map


def clustering_gini_and_ms(vector_directories, clustering_algorithms, best_k_per_model_algo,train_mutation_profiles,main_mutation_profiles,test_mutation_profiles,
                           combined_results_random_greedy,all_random_scores, all_greedy_scores,greedy_selected_counts,
                           save_results_path,sample_sizes, pca, runs, process_type,decimal_places, profile_limit=None):

    gini_impurity_summary_data = []


    def process_algorithm(c_algo, e_model_name, vectors_profiles, identifiers):
        """
        Processing clustering for each algorithm and model.
        """
        algorithm_name = c_algo[0]

        if algorithm_name in best_k_per_model_algo[e_model_name]:
            chosen_k = best_k_per_model_algo[e_model_name][algorithm_name]
        else:
            chosen_k = 0

        print(f"Processing {algorithm_name} with K={chosen_k} for {e_model_name}")

        if chosen_k is None or chosen_k < 1:
            print(f"Invalid chosen K={chosen_k} for {algorithm_name} on {e_model_name}. Using default K=2.")
            chosen_k = 2



        # -------------------------------------------------- CLUSTERING  and MAPPING with inputs with cluster id ----------
        """
        identifiers = ['input1.txt', 'input6.txt']
        vectors_profiles = [
          [1.0, 1.0],  # input1
          [5.0, 5.0],  # input3
          [9.1, 9.0]   # input6
        ]
        cluster_map = {
          'input1.txt': 0,
          'input3.txt': 1,
          'input6.txt': 2
        }       
        num_clusters = 3
        """

        # Running clustering
        cluster_map, num_clusters = clustering(vectors_profiles, chosen_k,
                                               f"{save_results_path}/{e_model_name}_{algorithm_name.lower()}.png",
                                               identifiers, algo=algorithm_name, pca_variance=pca)

        # Saving cluster mappings
        cluster_csv_path = os.path.join(save_results_path, e_model_name, algorithm_name, f"{e_model_name}_cluster_inputs_map.csv")
        os.makedirs(os.path.dirname(cluster_csv_path), exist_ok=True)
        save_cluster_mapping_to_csv(cluster_map, cluster_csv_path)
        # --------------------------------------------- CLUSTER MAP SAVE DONE ------------------------------------------


        # Gini impurities with testing profiles
        """
        Organizing profile result by cluster region.
        1 - [1, 0],[0, 0] # profile of input_1 and input_4 
        0 - [0, 1],[1, 1] # profile of input_2 and input_3 
        """
        cluster_data = cluster_region_map_with_profile(cluster_map, test_mutation_profiles)
        overall_avg_gini = calculate_and_save_gini_impurities(cluster_data, save_results_path, e_model_name, algorithm_name)

        # Storing Gini impurity summary
        gini_impurity_summary_data.append([e_model_name, algorithm_name, num_clusters, overall_avg_gini])

        """
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> MUTATION SCORE : TESTING PROFILES <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        --- Cluster Prioritization
        ---- Input selection from clusters
        -----MS Score calculation for selected inputs
        """
        cluster_based_results = test_profiles_mutation_score(vectors_profiles, identifiers,
                                                       lambda v, i: (cluster_map, num_clusters),
                                                             main_mutation_profiles,
                                                       train_mutation_profiles,
                                                       test_mutation_profiles,all_random_scores,
                                                       all_greedy_scores,
                                                       greedy_selected_counts,
                                                       sample_sizes,runs=runs)

        # Round results to the specified number of decimal places
        cluster_based_results = [
            {k: round(v, decimal_places) if isinstance(v, (int, float)) else v for k, v in result.items()} for
            result in cluster_based_results]


        score_csv_path = os.path.join(save_results_path, e_model_name, algorithm_name,
                                      f"{e_model_name}_{algorithm_name}_{process_type}_Score_Comparison.csv")
        pd.DataFrame(cluster_based_results).to_csv(str(score_csv_path), index=False)

        cluster_based_scores = [res['Cluster-Based Score[Mean]'] for res in cluster_based_results]
        cluster_auc = auc(sample_sizes, cluster_based_scores)


        return e_model_name, algorithm_name, {"scores": cluster_based_scores, "AUC": cluster_auc}

    # Process each model and algorithm concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for model_name, directory in vector_directories.items():
            # vectors: list of vectors (embedding representations).
            # identifiers: A list of identifiers corresponding to each vector.
            vectors, identifiers = load_vectors_from_files(directory, profile_limit=profile_limit)
            print(f"Loaded {len(vectors)} vectors and {len(identifiers)} identifiers from {directory}")

            for algo in clustering_algorithms:
                futures.append(executor.submit(process_algorithm, algo, model_name, vectors, identifiers))

        # Collect results
        for future in concurrent.futures.as_completed(futures):
            model_name, algo_name, result = future.result()
            combined_results_random_greedy[f"{model_name}_{algo_name}"] = result

    # Sort and return Gini impurity results
    gini_impurity_summary_data.sort(key=lambda x: x[0])
    return combined_results_random_greedy, gini_impurity_summary_data




def generate_final_reports(combined_results,
                           gini_impurity_summary_data,
                           best_k_per_model_algo, tracking_table,sample_sizes, save_results_path,
                           process_type, runs):
    # Generate combined graph with random mutation scores and all 16 combinations of models and algorithms
    combined_graph_path = os.path.join(save_results_path, f"Combined_{process_type}_Score_Graph.png")
    # print("Final Combined Results Structure:", combined_results)

    plot_combined_mutation_scores(combined_results, combined_graph_path,sample_sizes, process_type, runs)
    # save the best K values
    save_best_k_to_csv(best_k_per_model_algo, save_results_path)
    # Save the tracking table to a CSV file
    save_tracking_table_to_csv(tracking_table, save_results_path)
    # Save Gini Details for each combination
    # this gini value is for selected statements
    save_summary_gini_impurity(save_results_path, gini_impurity_summary_data)

import os

def count_unique_profiles_by_hamming(directory_path):
    """
    Counts the number of unique mutation kill profiles based on Hamming distance.

    Args:
        directory_path (str): Path to the directory containing .txt files.

    Returns:
        int: Number of unique profiles.
    """
    unique_profiles = set()

    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r') as f:
                # Read the profile as a single flat string of 0s and 1s
                bits = f.read().replace('\n', '').replace(' ', '')
                unique_profiles.add(bits)

    return len(unique_profiles)
dir_path = "/Users/usi/Desktop/EXPERIMENTS/pythonProject/MUT_KILLING_PROFILE/BASIC/main"
unique_count = count_unique_profiles_by_hamming(dir_path)
print(f"Number of unique profiles: {unique_count}")
coverage_data_path = f"../COVERAGE_REPORTS/BASIC"
save_cluster_result_path ="/Users/usi/Desktop/EXPERIMENTS/pythonProject/MUT_KILLING_PROFILE/BASIC"
print(f"Coverage Data path : {coverage_data_path}")
coverage_file = get_coverage_filename("basic")
_, coverage_profile_count = process_coverage_data(coverage_data_path,
                                                                           coverage_file,
                                                                           save_cluster_result_path,
                                                                           profile_limit=2000,
                                                                           profile_set="first")

print(f"unique coverage profiles : {coverage_profile_count}")