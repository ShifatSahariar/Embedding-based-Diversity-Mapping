import os

import pandas as pd


def remove_context_indexes(coverage_map):
    """
    Remove coverage indexes that are the same (all 0s or all 1s) across all files.

    Args:
        coverage_map: Dictionary mapping file names to coverage profiles as lists of integers.

    Returns:
        A dictionary with the same structure but with constant indexes removed.
    coverage_map = {
    "File1": [0, 1, 1, 0],
    "File2": [0, 1, 0, 0],
    "File3": [0, 1, 1, 0]
    }
    Transposed:
    [
    [0, 0, 0],  # Index 0
    [1, 1, 1],  # Index 1
    [1, 0, 1],  # Index 2
    [0, 0, 0]   # Index 3
    ]
    AFTER REMOVE:
    new_coverage_map = {
    "File1": [1],
    "File2": [0],
    "File3": [1]
    }



    """
    # Transpose the list of coverage profiles to analyze by index
    coverage_profiles = list(coverage_map.values())
    transposed_profiles = list(zip(*coverage_profiles))

    # Find indexes that are not constant (where not all values are the same)
    filtered_indexes = [i for i in range(len(transposed_profiles)) if len(set(transposed_profiles[i])) > 1]

    # Reconstruct the coverage profiles without the constant indexes
    new_coverage_map = {file: [profile[i] for i in filtered_indexes] for file, profile in coverage_map.items()}

    return new_coverage_map


def remove_redundant_indices(coverage_map):
    """
    Remove redundant indices across all files where the pattern of coverage repeats at different indices.

    Args:
        coverage_map: Dictionary mapping file names to coverage profiles.

    Returns:
        A dictionary with reduced coverage profiles retaining only unique index patterns.


        coverage_map = {
    "File1": [1, 0, 1],
    "File2": [1, 0, 1],
    "File3": [0, 1, 0],
    "File4": [0, 1, 0],
    "File5": [1, 1, 1]
    }

    {
    "File1": [1, 0],
    "File2": [1, 0],
    "File3": [0, 1],
    "File4": [0, 1],
    "File5": [1, 1]
    }




    """
    # Transpose the coverage profiles to analyze by index
    coverage_profiles = list(coverage_map.values())
    transposed_profiles = list(zip(*coverage_profiles))

    # Create a dictionary to store the first occurrence of each unique pattern
    unique_pattern_indices = {}
    final_indices = []

    # Check each index (column) for uniqueness
    for i, pattern in enumerate(transposed_profiles):
        pattern_tuple = tuple(pattern)
        if pattern_tuple not in unique_pattern_indices:
            unique_pattern_indices[pattern_tuple] = i
            final_indices.append(i)  # Store the index of the first unique occurrence

    # Rebuild the coverage profiles keeping only the unique indices
    new_coverage_map = {file: [profile[i] for i in final_indices] for file, profile in coverage_map.items()}

    return new_coverage_map

from collections import defaultdict

def cluster_region_map_with_profile(cluster_map, coverage_map):
    """
    Organize coverage result by cluster region.
        1 - [1, 0],[0, 0] # profile of file1 and file4 : dummy
        0 - [0, 1],[1, 1] # profile of file2 and file3 : dummy
    Args:
        cluster_map: Dictionary mapping file names to cluster regions.
        coverage_map: Dictionary mapping file names to coverage profiles.

    Returns:
        Dictionary mapping cluster regions to lists of coverage profiles.
    """
    cluster_data = defaultdict(list)

    for file, region in cluster_map.items():
        file_str = str(file)
        if file_str in coverage_map:
            cluster_data[region].append(coverage_map[file_str])
        else:
            print(f"Warning: File {file_str} not found in coverage_map!")

    return dict(cluster_data)


def load_coverage_data(reports_directory, coverage_filename='CalcParser_profile.txt'):
    """
     MAPPING = [file name ][coverage profile]
     [coverage profile] = ARRAY like [0,1,1,0]
    Load coverage COVERAGE_REPORTS from the specified directory and return a dictionary
    mapping folder names to lists of integers representing coverage COVERAGE_REPORTS.

    :param coverage_filename:
    :param reports_directory: Directory containing coverage report files.
    :return: A dictionary mapping folder names to lists representing coverage report result.
    """
    coverage_map = {}
    folder_names = sorted(os.listdir(reports_directory))
    for folder_name in folder_names:
        folder_path = os.path.join(reports_directory, folder_name)
        if os.path.isdir(folder_path):
            # for now, we are interested only about CalcParser_profile
            coverage_file_path = os.path.join(folder_path, coverage_filename)
            if os.path.exists(coverage_file_path):
                with open(coverage_file_path, 'r') as file:
                    # Read the coverage result and strip any unwanted whitespace
                    coverage_data = file.read().strip()
                    # Convert space-separated string to a list of integers
                    coverage_list = [int(x) for x in coverage_data.split()]
                    # Store the coverage list in the map
                    coverage_map[folder_name] = coverage_list
    return coverage_map


def process_coverage_data(reports_directory, coverage_filename, save_cluster_result_path,profile_limit=None, profile_set="first"):
    # Load Coverage DataMAP: file identifiers to their coverage profiles
    """
    Processes coverage result while applying filtering steps and optional profile limiting.

    MAPPING = [file name ][coverage profile]
    [coverage profile] = ARRAY like [0,1,1,0]
    """
    # We can use the filename which we want to create map for
    coverage_map = load_coverage_data(reports_directory, coverage_filename)

    # Convert to List of Tuples for Sorting & Selection
    profile_data = list(coverage_map.items())  # [(file_id, coverage_profile), ...]

    # Apply Profile Limit (Select first N or last N)
    if profile_limit is not None:
        if profile_set == "first":
            profile_data = profile_data[:profile_limit]
        elif profile_set == "last":
            profile_data = profile_data[-profile_limit:]
        else:
            raise ValueError(f"Invalid profile_set: {profile_set}. Must be 'first' or 'last'.")

    # Convert Back to Dictionary
    coverage_map = dict(profile_data)
    # print("Coverage Map :")
    # pprint.pprint(coverage_map)

    # dummy_coverage_map = {
    #     "File1": [0, 1, 1, 0, 0],
    #     "File2": [0, 1, 0, 1, 1],
    #     "File3": [0, 1, 1, 1, 1],
    #     "File4": [0, 1, 0, 0, 0]
    # }
    # dummy_cluster_map = {
    #     "File1": 1,
    #     "File2": 0,
    #     "File3": 0,
    #     "File4": 1
    # }
    """
    ##  1st Filter  ##
    Remove Common Indexes: Identify and remove indexes ::  
    [0, 0, 0],  # Index 0
    [1, 1, 1],  # Index 3
    will remove both indexes
    """
    filtered_coverage_map = remove_context_indexes(coverage_map)
    # print("Filtered Coverage Map")
    # print(filtered_coverage_map)

    """
    ##  2nd Filter  ##
    Remove Redundant Patterns :
    [0, 1, 0],  # Index 0
    [0, 1, 0],  # Index 2
    here we will keep one index
    """
    final_coverage_map = remove_redundant_indices(filtered_coverage_map)  # REFINED COVERAGE MAP

    # Step 2: Convert the filtered profiles to tuples and add them to a set to remove duplicates
    unique_profiles_coverage = set(tuple(profile) for profile in final_coverage_map.values())

    # Step 4: Calculate the number of profiles (i.e., how many files were loaded)
    profile_count = len(unique_profiles_coverage)

    # Step 5: Calculate the original number of statements (based on any file's profile length)
    original_statement_count = len(next(iter(coverage_map.values()))) if profile_count > 0 else 0

    # Step 6: Calculate the number of statements after filtering (based on any file's filtered profile length)
    filtered_statement_count = len(next(iter(final_coverage_map.values()))) if profile_count > 0 else 0

    stats_df = pd.DataFrame({
        "Profile Count": [profile_count],
        "Original Statement Count": [original_statement_count],
        "Filtered Statement Count": [filtered_statement_count]
    })

    # Specify the path to save the CSV file
    stats_save_path = f"{save_cluster_result_path}/coverage_profile_stats.csv"

    print(f"Save results path: {stats_save_path}")
    # Save the DataFrame to CSV
    stats_df.to_csv(stats_save_path, index=False)

    return final_coverage_map, profile_count


def concatenate_statement_coverage_profiles(directory, sut_program, subject_program_config):
    # read expected classes (legacy contract)
    class_files = subject_program_config.get(sut_program, {}).get("class_files", [])
    class_names = [os.path.splitext(os.path.basename(cf))[0] for cf in class_files]

    aggregated_profile_data = []

    # Build a quick index of available profiles in the directory
    available_profiles = {name: os.path.join(directory, name) for name in os.listdir(directory) if name.endswith("_profile.txt")}

    for class_name in class_names:
        # 1) legacy filename
        legacy = f"{class_name}_profile.txt"
        # 2) new (pkg-prefixed) pattern
        #    e.g., "basic__BASIC_profile.txt" or "_default___CalcParser_profile.txt"
        #    We'll match any prefix ending with "__"
        candidates = [legacy] + [fn for fn in available_profiles.keys() if fn.endswith(f"__{class_name}_profile.txt")]

        found_path = None
        for cand in candidates:
            if cand in available_profiles:
                found_path = available_profiles[cand]
                break

        if found_path:
            with open(found_path, "r", encoding="utf-8") as f:
                profile_content = " ".join(f.read().split())
                aggregated_profile_data.append(profile_content)
        else:
            print(f"Warning: Expected profile for class '{class_name}' not found in {directory}")

    aggregated_profile_content = " ".join(aggregated_profile_data)
    aggregated_profile_path = os.path.join(directory, "aggregated_profile.txt")
    with open(aggregated_profile_path, "w", encoding="utf-8") as aggregated_file:
        aggregated_file.write(aggregated_profile_content)

    print(f"Aggregated profile created at {aggregated_profile_path}")

