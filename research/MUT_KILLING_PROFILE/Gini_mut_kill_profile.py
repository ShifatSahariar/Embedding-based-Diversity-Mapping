import os

# Determine Unique Profiles
import os


# Level Inputs with Mutation Killing Profiles
def level_cluster_items_with_mutatants_profiles(cluster_map, mutation_profiles):
    """
    Level the input files in clusters based on their mutation profiles.

    This function maps each file from the cluster map to its corresponding mutation profile
    and counts the occurrences of each profile within its cluster region.

    Args:
        cluster_map: A dictionary mapping file names to cluster regions.
                    Example: {'file1': 'region1', 'file2': 'region2'}

        mutation_profiles: A dictionary mapping file names to their respective mutation profiles.
                           Mutation profiles are lists of integers representing whether specific mutants
                           were killed (1) or not killed (0).
                           Example: {'file1': [0, 1, 0, 1], 'file2': [1, 0, 1, 1]}

    Returns:
        cluster_data: A nested dictionary where each cluster region is mapped to another dictionary.
                      This inner dictionary maps each unique mutation profile (as a tuple) to the
                      count of files in that region with that profile.
                      Example: {'region1': {(0, 1, 0, 1): 2, (1, 0, 1, 0): 1},
                                'region2': {(1, 1, 1, 1): 3}}

    Process:
    - For each file in the cluster map, the function checks if the file's mutation profile exists
      in the mutation_profiles dictionary.
    - If the mutation profile is found, the function converts it to a tuple (to make it hashable)
      and updates the count for that profile within the relevant cluster region.
    - If the file's mutation profile is not found in the mutation_profiles dictionary,
      a warning message is printed.
    - The final result is a dictionary (cluster_data) that helps identify how many files
      within each cluster region share the same mutation profile.


      Cluster_map = {
    "file1": "region1",
    "file2": "region1",
    "file3": "region2",
    "file4": "region2",
    "file5": "region3"
}

mutation_profiles = {
    "file1": [0, 1, 0, 1],
    "file2": [0, 1, 0, 1],
    "file3": [1, 0, 1, 1],
    "file4": [1, 0, 0, 0],
    "file5": [0, 1, 0, 1]
}
 cluster_data dictionary will look like this:
{
    "region1": {
        (0, 1, 0, 1): 2  # Two files in region1 share this profile
    },
    "region2": {
        (1, 0, 1, 1): 1, # One file in region2 has this profile
        (1, 0, 0, 0): 1  # One file in region2 has this profile
    },
    "region3": {
        (0, 1, 0, 1): 1  # One file in region3 has this profile
    }
}


    """

    # Initialize an empty dictionary to store the clustered result
    cluster_data = {}

    # Iterate over each file and its corresponding cluster region in the cluster map
    for file, region in cluster_map.items():
        # Convert the file name to a string (just in case it's not already)
        file_id = str(file)

        # Check if the file's mutation profile exists in the mutation_profiles dictionary
        if file_id in mutation_profiles:
            # Retrieve the mutation profile and convert it to a tuple (to use as a dictionary key)
            profile = tuple(mutation_profiles[file_id])

            # If the region is not already in the cluster_data dictionary, initialize it
            if region not in cluster_data:
                cluster_data[region] = {}

            # If the profile is not already in the region's dictionary, initialize its count to 0
            if profile not in cluster_data[region]:
                cluster_data[region][profile] = 0

            # Increment the count of this profile in the current region
            cluster_data[region][profile] += 1
        else:
            # If the file's mutation profile is not found, print a warning message
            print(f"Warning: Mutation profile for {file_id} not found")

    # Return the final clustered result with profile counts
    return cluster_data


# Step 4: Calculate Gini Impurity
def calculate_gini_impurity(cluster):
    """
    Calculate the Gini impurity for a single cluster.

    Args:
        cluster: A dictionary where the keys are profiles (or categories) and the values
                 are the counts of items that fall into those profiles within the cluster.
                 Example: {profile1: 10, profile2: 20, profile3: 5}

    Returns:
        gini_impurity: The Gini impurity for the cluster, a value between 0 and 1.
    """
    # Calculate the total number of items in the cluster
    total = sum(cluster.values())

    # Initialize Gini impurity to 1 (the maximum value)
    gini_impurity = 1.0

    # Calculate the Gini impurity by subtracting the sum of squared proportions
    for count in cluster.values():
        proportion = count / total  # Proportion of items in this profile
        gini_impurity -= proportion ** 2  # Subtract the square of the proportion from the Gini impurity

    return gini_impurity


def calculate_average_gini_impurity(leveled_clusters):
    """
    Calculate the average Gini impurity across all clusters.

    Args:
        leveled_clusters: A dictionary where each key is a cluster identifier and the value
                          is a dictionary representing the profiles and their counts within
                          that cluster.
                          Example: {cluster1: {profile1: 10, profile2: 20},
                                    cluster2: {profile1: 5, profile3: 15}}

    Returns:
        average_gini_impurity: The average Gini impurity across all clusters.
    """
    total_gini = 0.0  # Initialize the sum of Gini impurities to zero

    # Loop through each cluster to calculate its Gini impurity
    for cluster_id, cluster in leveled_clusters.items():
        # Calculate the Gini impurity for this specific cluster
        gini_impurity = calculate_gini_impurity(cluster)

        # Add this cluster's Gini impurity to the total
        total_gini += gini_impurity

        # Print the Gini impurity for the current cluster (useful for debugging or utils)
        print(f"Gini Impurity for Cluster {cluster_id}: {gini_impurity}")

    # Calculate the average Gini impurity by dividing the total Gini by the number of clusters
    average_gini_impurity = total_gini / len(leveled_clusters)

    return average_gini_impurity
