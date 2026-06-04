import os

import pandas as pd

from Helper_Functions.HelperFunctions import get_fraction_value


def select_best_gini(gini_df, probability_df):
    """
        Select the best Gini impurity for each statement based on the highest probability of coverage.

        Args:
            gini_df: DataFrame containing Gini impurities for each cluster and statement.
            probability_df: DataFrame containing the probability of coverage for each cluster and statement.

        Returns:
            selected_gini_df: DataFrame with the best Gini impurities selected based on the highest probability.
            clusters_df: DataFrame with the corresponding cluster IDs for the selected Gini impurities.
        """
    selected_ginis = []
    selected_clusters = []

    for statement in gini_df.columns[1:]:
        max_probability = 0
        max_clusters = []

        # Find the maximum probability and corresponding clusters
        for i, row in probability_df.iterrows():
            probability = get_fraction_value(row[statement])
            if probability > max_probability:
                max_probability = probability
                max_clusters = [row["Cluster ID"]]
            elif probability == max_probability:
                max_clusters.append(row["Cluster ID"])

        # Select Gini values from the clusters with max probability
        gini_values = [gini_df.loc[gini_df["Cluster ID"] == cluster, statement].values[0] for cluster in max_clusters]

        # Calculate average Gini if there are ties
        best_gini = sum(gini_values) / len(gini_values)
        selected_ginis.append(best_gini)
        selected_clusters.append(max_clusters)

    # Create a DataFrame for the selected Ginis and corresponding clusters
    selected_gini_df = pd.DataFrame([selected_ginis], columns=gini_df.columns[1:])
    clusters_df = pd.DataFrame([selected_clusters], columns=gini_df.columns[1:])

    return selected_gini_df, clusters_df


# Function to Calculate Probability of Each Statement Being Covered in Each Cluster
def calculate_probability_each_index_of_each_cluster(coverage_profiles):
    """
    Calculate the probability of each statement being visited in a given set of coverage profiles at each index.
    Args:
        coverage_profiles: List of lists where each sublist is a coverage profile.
    Returns:
        List of probability values for each index.

    coverage_profiles =
    [
        [1, 0, 1],
        [1, 0, 0],
        [0, 1, 0]
    ]
    Transposed_profiles:
        Index 0: [1, 1, 0]
        Index 1: [0, 0, 1]
        Index 2: [1, 0, 0]
    """
    # Transpose to get values by index
    transposed_profiles = list(zip(*coverage_profiles))
    probabilities = []

    """
    If transposed_profiles is [[1, 1, 0], [0, 0, 1], [1, 0, 0]], 
    index_values will be [1, 1, 0] in the first iteration.
    """
    for index_values in transposed_profiles:
        # index_values = [1, 1, 0], total will be 3.
        total = len(index_values)
        # index_values = [1, 1, 0], ones_count will be 2.
        # We count how many 1s we have since we have only 1 or 0.
        ones_count = sum(index_values)
        # probability is calculated as ones_count / total.
        # For index_values = [1, 1, 0], probability will be 2/3.
        probability = ones_count / total
        # Append the probability in the form of a fraction string '2/3'.
        probabilities.append(f"{ones_count}/{total}")

    return probabilities


def calculate_gini_impurity_each_index_of_each_cluster(coverage_profiles):
    """
    ⇒ For Each REGION getting all coverage_profiles
    ⇒ The coverage_profiles contains Multiple Profiles -
    for example, the following region has two profiles in binary formate
    ⇒ 0 ---> [0,1,0],[1,0,1]

    Calculate the Gini impurity for a given set of coverage profiles at each index.
    Args:
        coverage_profiles: List of lists where each sublist is a coverage profile.
    Returns:
        List of Gini impurity values for each index.

    Coverage_profiles =
    [
    [1, 0, 1],
    [1, 0, 0],
    [0, 1, 0]
    ]
    Transposed_profiles:
        Index 0: [1,1,0]
        Index 1: [0,0,1]
        Index 2: [1,0,0]

    """
    # Transpose to get values by index
    transposed_profiles = list(zip(*coverage_profiles))
    gini_impurities = []
    """
    If transposed_profiles is [[1, 1, 0], [0, 0, 1], [1, 0, 0]], 
    index_values will be [1, 1, 0] in the first iteration.
    """
    for index_values in transposed_profiles:
        # index_values = [1, 1, 0], total will be 3.
        total = len(index_values)
        # index_values = [1, 1, 0], ones_count will be 2
        # we can count how many 1 we have : since we have only 1 or 0
        ones_count = sum(index_values)
        # index_values = [1, 1, 0], zeros_count will be 1
        # total - ones_count = 3 - 2
        zeros_count = total - ones_count
        # Computes the proportion of 1 in the index_values
        # index_values = [1, 1, 0], p1 will be 2/3.
        p1 = ones_count / total
        # Computes the proportion of 0 in the index_values.
        # index_values = [1, 1, 0], p0 will be 1/3.
        p0 = zeros_count / total
        # for the current index
        gini_impurity = 1 - (p1 ** 2 + p0 ** 2)
        # for each index we will append
        # it will contain gini_impurity for each index separately as a list
        gini_impurities.append(gini_impurity)

    return gini_impurities


def average_gini_impurities(gini_impurities):
    """
    ⇒ List of Gini Impurities for a Cluster Region
    ⇒ gini_impurities = [4/9, 4/9, 4/9]

    Calculate the average Gini impurity from a list of Gini impurities.
    Args:
        gini_impurities: List of Gini impurity values.
    Returns:
        Average Gini impurity.
    """
    if gini_impurities:
        return sum(gini_impurities) / len(gini_impurities)
    return 0


# #######################  GINI IMPURITY ANALYSIS #######################

# Function to calculate and save Gini impurities and probabilities for statement coverage
def calculate_and_save_gini_impurities(cluster_data, save_results_path, model_name, algo_name):
    """
    Calculate and save Gini impurities, probabilities, and related statistics to CSV files.

    Args:
        cluster_data: A dictionary mapping cluster regions to lists of profiles.
        save_results_path: The base path where results should be saved.
        model_name: The name of the embedding our_trained_models.
        algo_name: The name of the clustering algorithm.

    Returns:
        gini_df: DataFrame containing Gini impurity values for each cluster and statement.
        probability_df: DataFrame containing probability values for each cluster and statement.
        overall_average_gini_per_statement_from_all_cluster:
        overall_average_gini_selected_best_gini:
    """
    # Create directories for saving results
    # Ensure that the path components are strings
    algo_folder = None
    if save_results_path is not None:
        save_results_path = str(save_results_path)
        model_name = str(model_name)
        algo_name = str(algo_name)

        model_folder = os.path.join(save_results_path, model_name)
        algo_folder = os.path.join(model_folder, algo_name)
        os.makedirs(algo_folder, exist_ok=True)

    # MAP : Region -> Gini
    # 0 -> 0.25, 1 -> 00.22
    gini_impurity_map = {}

    # Dictionary to store probabilities
    probability_map = {}
    """
    -> Iterate through items in Cluster Data MAPS
    -> For each region get the profiles 0 ---> [0,1,0],[1,0,1]
    -> Calculate the list of gini for all the indexes : gini_impurities = [4/9, 4/9, 4/9]
    -> Average and get the gini value for that specific region ::  0 -> 0.25
    """
    # Calculate Gini impurities and probabilities for each cluster
    for region, profiles in cluster_data.items():
        gini_impurities = calculate_gini_impurity_each_index_of_each_cluster(profiles)
        # Limit Gini values to 3 decimal places
        gini_impurities = [round(gini, 3) for gini in gini_impurities]
        gini_impurity_map[region] = gini_impurities

        probabilities = calculate_probability_each_index_of_each_cluster(profiles)
        probability_map[region] = probabilities

    # Creating column names based on the number of statements(indexes)
    num_statements = len(next(iter(gini_impurity_map.values())))
    columns = ["Cluster ID"] + [f"Statement {i + 1}" for i in range(num_statements)]

    # Convert the Gini impurity map to a DataFrame
    """
        ----------------------------------------------------
                             GINI MAP
        ----------------------------------------------------
        CLUSTER ID | mutant 1 | mutant 2 | mutant 3
        ----------------------------------------------------
        2          |    0.15     |     0.04    |  0.32      
        1          |    0.17     |     0.24    |  0.03      
        0          |    0.14     |     0.04    |  0.29      
        """

    gini_data = [[region] + gini_values for region, gini_values in gini_impurity_map.items()]
    gini_df = pd.DataFrame(gini_data, columns=columns)

    if algo_folder:
        # Save the Gini DataFrame to a CSV file
        gini_csv_path = os.path.join(algo_folder, f"{model_name}_{algo_name}_Gini_MAP.csv")
        gini_df.to_csv(gini_csv_path, index=False)
        # print(f"CSV file saved to {gini_csv_path}")

    # Convert the probability map to a DataFrame
    """
        ----------------------------------------------------
                             PROBABILITY MAP
        ----------------------------------------------------
        CLUSTER ID | mutant 1 | mutant 2 | mutant 3
        ----------------------------------------------------
        2          |    2/3     |     3/3    |  0/3      
        1          |    1/3     |     2/3    |  1/3      
        0          |    3/3     |     1/3    |  1/3      
    """
    # Convert the probability map to a DataFrame
    prob_data = [[region] + prob_values for region, prob_values in probability_map.items()]
    probability_df = pd.DataFrame(prob_data, columns=columns)

    if algo_folder:
        # Save the probabilities DataFrame to a CSV file
        prob_csv_path = os.path.join(algo_folder, f"{model_name}_{algo_name}_Probability_MAP.csv")
        probability_df.to_csv(prob_csv_path, index=False)

    # Get the selected Gini values and corresponding clusters

    """
        ---------------------------------------
                  SELECTED GINI MAP
        ---------------------------------------
        mutant 1 | mutant 2 | mutant 3
        -----------------------------------------
            0.15    |     0.04    |    0.32      
         
     
    """
    # Select the best Gini values based on the highest probability
    selected_gini_df, clusters_df = select_best_gini(gini_df, probability_df)
    if algo_folder:
        # Save the selected Gini values to a CSV file
        selected_gini_csv_path = os.path.join(algo_folder, f"{model_name}_{algo_name}_Selected_Gini_MAP.csv")
        selected_gini_df.to_csv(selected_gini_csv_path, index=False)
        # print(f"Selected Gini values saved to {csv_gini_path}")

    """
    ---------------------------------------
              SELECTED GINI CLUSTER ID'S
    ---------------------------------------
    mutant 1 | mutant 2 | mutant 3
    -----------------------------------------
        1       |     3       |      2      
    
    
    """
    if algo_folder:
        # Save the cluster information to a separate CSV file
        clusters_csv_path = os.path.join(algo_folder, f"{model_name}_{algo_name}_Selected_Gini_Clusters.csv")
        clusters_df.to_csv(clusters_csv_path, index=False)
        # print(f"Cluster information saved to {csv_clusters_path}")

    # Calculate the average Gini value for each statement
    """
    ------------------------------------------------
              AVERAGE GINI - FOR EACH MUTANT
    ------------------------------------------------
    mutant 1 | mutant 2 | mutant 3
    -----------------------------------------
        0.5     |     0.4     |      0.3       
    
    
    """
    # Calculate the average Gini value for each statement
    average_gini_values = gini_df.drop(columns=["Cluster ID"]).mean()

    # Create a new DataFrame with the average values
    average_gini_df = pd.DataFrame([average_gini_values], columns=average_gini_values.index)

    if algo_folder:
        # Save the average Gini values to a CSV file
        avg_per_statement_csv_path = os.path.join(algo_folder,
                                                  f"{model_name}_{algo_name}_Average_Gini_Per_Statement.csv")
        average_gini_df.to_csv(avg_per_statement_csv_path, index=False)

    # Calculate the overall average Gini impurity across all statements
    # overall_average_gini_per_statement_from_all_cluster = average_gini_df.mean(axis=1).mean()
    overall_average_gini_selected_best_gini = selected_gini_df.mean(axis=1).mean()
    return overall_average_gini_selected_best_gini


def save_summary_gini_impurity(save_results_path, summary_data):
    summary_csv_path = os.path.join(save_results_path, "Summary_Gini_Impurity_Model_Cluster.csv")

    # Convert the summary result to a DataFrame
    summary_df = pd.DataFrame(summary_data, columns=["Embedding Model", "Cluster Algorithm", "Number of Clusters",
                                                     "Gini Impurity"])

    # Round the result to 4 decimal places
    summary_df = summary_df.round(4)

    # Save the DataFrame to a CSV file
    summary_df.to_csv(summary_csv_path, index=False)
