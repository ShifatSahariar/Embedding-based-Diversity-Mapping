import os

import pandas as pd

from COVERAGE_REPORTS.Coverage_Profile import remove_context_indexes, remove_redundant_indices


def rewrite_filtered_profiles(new_coverage_map, profiles_directory):
    """
    Overwrites each original *_mut_killing_profile.txt with the newly filtered killing profile.
    """
    for profile_name, filtered_profile in new_coverage_map.items():
        # Overwriting the *same* filename as original
        output_filename = f"{profile_name}.txt"

        output_path = os.path.join(profiles_directory, output_filename)

        # Converting back to space-separated string
        data_str = " ".join(map(str, filtered_profile))

        # filtered result to the file
        with open(output_path, "w") as f:
            f.write(data_str + "\n")

    print(f"Overwritten mutation killing profiles after filtering in: {profiles_directory}")

# MUTANTS DISCARDING PROCESS
def load_mutation_killing_profiles(profiles_directory,profile_limit=None, profile_set='first',discard_empty=True):
    """
     # dummy mutation_killing_map = {
    #     "File1": [0, 1, 1, 0, 0],
    #     "File2": [0, 1, 0, 1, 1],
    #     "File3": [0, 1, 1, 1, 1],
    #     "File4": [0, 1, 0, 0, 0]
    # }
    Load mutation killing profiles from the specified directory and return a dictionary
    mapping profile names to lists of integers representing mutation killing result.

    :param discard_empty:
    :param profile_set:
    :param limit:
    :param profiles_directory: Directory containing mutation killing profile files.
    :return: A dictionary mapping profile names to lists representing mutation killing result.
    """
    mutation_killing_map = {}
    profile_data = []  # Store (profile_name, killing_list)

    profile_files = sorted(
        [f for f in os.listdir(profiles_directory) if f.endswith('.txt')],
        key=lambda x: int(x.split('.')[0]) # Sorting by numeric ID
    )

    # Apply limit early to improve efficiency (only load required files)
    if profile_limit is not None:
        if profile_set == 'first':
            profile_files = profile_files[:profile_limit]
        elif profile_set == 'last':
            profile_files = profile_files[-profile_limit:]
        else:
            raise ValueError(f"Invalid profile_set: {profile_set}. Must be 'first' or 'last'.")


    for profile_file in profile_files:
        if profile_file.endswith('.txt'):
            file_path = os.path.join(profiles_directory, profile_file)
            with open(file_path, 'r') as file:
                # Read the mutation killing result and strip any unwanted whitespace
                killing_data = file.read().strip()
                # Convert space-separated string to a list of integers
                killing_list = [int(x) for x in killing_data.split()]
                # Store the killing list in the map with the profile name (without extension)
                # Extract profile identifier (assuming file name starts with profile ID)
            profile_name = profile_file.split('.')[0]  # Extracts profile number
            # (e.g., '9991' from '9991_mut_killing_profile.txt'

            # Discard profiles with no mutants killed if `discard_empty=True`
            # if discard_empty and sum(killing_list) == 0:
            # # print(f"Warning: Profile {profile_name} is empty (all 0s) but will be retained for consistency.")

            # profile_data.append((profile_name, killing_list))
            mutation_killing_map[profile_name] = killing_list


    # Populate final dictionary and input list
    # mutation_killing_map = {name: result for name, result in profile_data}
    # input_ids = list(mutation_killing_map.keys())

    print(f"Loaded {len(mutation_killing_map)} mutation profiles (limit={profile_limit}, set={profile_set})")

    return mutation_killing_map


def filter_mutants_by_killing_profile(mutation_killing_map):
    """
    Remove mutant indexes that are the same (all 0s or all 1s) across all profiles.

    Args:
        mutation_killing_map: Dictionary mapping profile names to mutation killing profiles as lists of integers.

    Returns:
        A dictionary with the same structure but with constant mutant indexes removed.
    """

    # Step 1: Extract all the profiles (lists of integers) from the dictionary.
    killing_profiles = list(mutation_killing_map.values())

    # Step 2: Transpose the list of profiles to group result by index.
    # This means converting:
    # killing_profiles = [[0, 1, 0, 1, 1, 1, 0],  # input_1
    #                     [0, 0, 1, 1, 1, 0, 1],  # input_2
    #                     [0, 0, 0, 1, 0, 1, 1]]  # input_3
    # into:
    # transposed_profiles = [(0, 0, 0),  # Index 0 across all inputs
    #                        (1, 0, 0),  # Index 1 across all inputs
    #                        (0, 1, 0),  # Index 2 across all inputs
    #                        (1, 1, 1),  # Index 3 across all inputs
    #                        (1, 1, 0),  # Index 4 across all inputs
    #                        (1, 0, 1),  # Index 5 across all inputs
    #                        (0, 1, 1)]  # Index 6 across all inputs
    transposed_profiles = list(zip(*killing_profiles))

    # Step 3: Identify indexes where the values are not all the same.
    # For example, an index with values (0, 0, 0) or (1, 1, 1) would be considered constant and removed.
    filtered_indexes = [i for i in range(len(transposed_profiles)) if len(set(transposed_profiles[i])) > 1]

    # Step 4: Reconstruct the mutation killing profiles by excluding the constant indexes.
    # This results in a new dictionary where the profiles only contain relevant indexes.
    new_mutation_killing_map = {profile: [profile_data[i] for i in filtered_indexes]
                                for profile, profile_data in mutation_killing_map.items()}

    return new_mutation_killing_map


def process_mutation_killing_profiles(mutation_killing_profile_path, subject_program,base_results_directory=None):
    """
    Process mutation killing profiles by loading, filtering, and calculating relevant statistics.

    Args:
        mutation_killing_profile_path: Path to the directory containing mutation killing profiles.
        save_results_path: Path to the directory where the results will be saved.

    Returns:
        filtered_mutation_killing_map: The filtered mutation killing map.
        original_mutant_count: The number of mutants before filtering.
        filtered_mutant_count: The number of mutants after filtering.
        profile_count: The number of profiles (i.e., the number of files).
        :param subject_program:
        :param base_results_directory:
        :param mutation_killing_profile_path:
        :param mutation_tool:

    """
    # Load the original mutation killing profiles
    mutation_killing_map = load_mutation_killing_profiles(mutation_killing_profile_path)
    profile_length_main = len(next(iter(mutation_killing_map.values())))
    print("Before filtering , each file has:", profile_length_main, " mutants")

    # Filter the mutants that were killed by all inputs or by none
    # filtered_mutation_killing_map = filter_mutants_by_killing_profile(mutation_killing_map)
    filtered_mutation_killing_map = remove_context_indexes(mutation_killing_map) # removing trivial + equivalent
    first_filter_profile_length = len(next(iter(filtered_mutation_killing_map.values())))
    print("After filtering [trivial+equivalent], each file has:", first_filter_profile_length, " mutants")

    mutation_profile_after_remove_redundant=remove_redundant_indices(filtered_mutation_killing_map)
    second_filter_profile_length = len(next(iter(mutation_profile_after_remove_redundant.values())))
    print("After filtering [redundant], each file has:", second_filter_profile_length, " mutants")


    """
     Until here we have removed - trivial + equivalent + redundant mutants::
     -----------------------------------------------------------------------
     now for the experiement with hard mutants we would like to go with a filtering process where 
     - train mutants should not contain test mutants.
     - since we are not tracking spesific mutants numbers we know if we filter with one threashold , it will also contain testing mutants.
     - so we will go in a way that we will filter with first filter for hard mutants for now for CALC with 45% survival rate .
     - after that from this mutants (1050) we want to do another filter with two threashold in a way that most harest kind of 5 for now which is less than 0.4
     - so we will have two filtered_profiles collection one is 0-40% another is 41-45%
    """
    hard_mutant_filtered_profiles = filter_difficult_mutants(mutation_profile_after_remove_redundant, difficulty_threshold=0.3)

    # # Splitting into test mutants (≤40%) and train mutants (41%-45%) for now only for CALC this one
    # test_hard_filtered_profiles, train_hard_filtered_profiles = split_filtered_profiles(hard_mutant_filtered_profiles, test_threshold=0.40)

    first_hard_filter_profile_length = len(next(iter(hard_mutant_filtered_profiles.values())))
    print("After keeping [difficult], each file has:", first_hard_filter_profile_length, " mutants")

    # length_test_hard_filter_profile = len(next(iter(test_hard_filtered_profiles.values())))
    # length_train_hard_filter_profile = len(next(iter(train_hard_filtered_profiles.values())))

    # print("hard mutants - testing :", length_test_hard_filter_profile, ":: hard mutants - training : ", length_train_hard_filter_profile)


    # Re-writing Filtered killing profiles and overwriting original profiles.
    test_mutation_killing_profile_path = f"MUT_KILLING_PROFILE/{subject_program.upper()}/test_mut_kill_profiles"
    train_mutation_killing_profile_path = f"MUT_KILLING_PROFILE/{subject_program.upper()}/train_mut_kill_profiles"

    rewrite_filtered_profiles(hard_mutant_filtered_profiles, mutation_killing_profile_path)
    # rewrite_filtered_profiles(test_hard_filtered_profiles, test_mutation_killing_profile_path)
    # rewrite_filtered_profiles(train_hard_fwe
    # iltered_profiles, train_mutation_killing_profile_path)


    # Removing the duplicate Profiles only for count - but we are not removing any inputs
    #     "File1": [0, 1, 1, 0, 0],
    #     "File2": [0, 1, 1, 0, 0],
    #     "File3": [0, 1, 1, 1, 1],
    # here file 1 and 2 is similar so we will keep one for counting
    # Step 2: Convert the filtered profiles to tuples and add them to a set to remove duplicates
    unique_profiles_mutation = set(tuple(profile) for profile in filtered_mutation_killing_map.values())

    # Step 3: Calculate the number of profiles (i.e., how many files were loaded)
    profile_count = len(unique_profiles_mutation)

    # Step 4: Calculate the original number of mutants (based on any file's profile length)
    original_mutant_count = len(next(iter(mutation_killing_map.values()))) if profile_count > 0 else 0

    # Step 5: Calculate the number of mutants after filtering (based on any file's filtered profile length)
    filtered_mutant_count = len(next(iter(filtered_mutation_killing_map.values()))) if profile_count > 0 else 0

    # If a base results directory is provided, proceed to save results
    if base_results_directory:
        # Step 6: Save these statistics in the same Excel file
        stats_df = pd.DataFrame({
            "Profile Count": [profile_count],
            "Original Mutant Count": [original_mutant_count],
            "Filtered Mutant Count": [filtered_mutant_count]
        })

        # Specify the path to save the Excel file
        save_results_path = f"{base_results_directory}"
        if not os.path.exists(save_results_path):
            os.makedirs(save_results_path, exist_ok=True)
        stats_save_path = f"{save_results_path}/mutation_profile_stats.csv"

        print(f"Save results path: {save_results_path}")
        # Save the DataFrame to Excel
        stats_df.to_csv(stats_save_path, index=False)
    else:
        print("skipping saving process for the current phase[train+test profiles filtering for each epoch]")

    return filtered_mutation_killing_map


def filter_difficult_mutants(mutation_killing_map, difficulty_threshold=0.3):
    """
    Filters mutants with a kill rate ≤ `difficulty_threshold` (default: 30%).

    Args:
        mutation_killing_map: A dictionary where keys are input/test names, and values
                             are lists of 0/1 indicating if each mutant was killed (1)
                             or survived (0) by that input.
        difficulty_threshold: Maximum allowed kill rate (0.0–1.0 scale).

    Returns:
        A dictionary retaining only mutants with kill rate ≤ `difficulty_threshold`.
    """
    # Validate input consistency
    if not mutation_killing_map:
        return {}

    lengths = {len(v) for v in mutation_killing_map.values()}
    if len(lengths) > 1:
        raise ValueError("All mutation profiles must have the same number of mutants.")

    total_inputs = len(mutation_killing_map)
    num_mutants = lengths.pop()

    # Compute kill counts per mutant (across all inputs)
    kill_counts = [0] * num_mutants
    for mutant_status in mutation_killing_map.values():
        for i, killed in enumerate(mutant_status):
            kill_counts[i] += killed

    # Calculate kill rates and identify difficult mutants
    difficult_mutant_indices = [
        i for i, count in enumerate(kill_counts)
        if (count / total_inputs) <= difficulty_threshold
    ]

    # Filter results
    filtered_map = {
        profile: [status[i] for i in difficult_mutant_indices]
        for profile, status in mutation_killing_map.items()
    }

    print(f"Kept {len(difficult_mutant_indices)} mutants with kill rate ≤{difficulty_threshold * 100}%")
    return filtered_map

def split_filtered_profiles(filtered_profiles, test_threshold=0.4):
    """
    Splits the given filtered profiles into two groups:
    - Mutants with kill rate ≤ `test_threshold` (test set).
    - Remaining mutants (train set).

    Args:
        filtered_profiles (dict): Already filtered profiles from `filter_difficult_mutants()`.
        test_threshold (float): Threshold for hardest mutants (default: 40%).

    Returns:
        Two dictionaries: (test_filtered_profiles, train_filtered_profiles)
    """
    if not filtered_profiles:
        return {}, {}

    total_inputs = len(filtered_profiles)
    num_mutants = len(next(iter(filtered_profiles.values())))  # All profiles have the same mutant count

    # Compute kill counts for the already filtered mutants
    kill_counts = [0] * num_mutants
    for mutant_status in filtered_profiles.values():
        for i, killed in enumerate(mutant_status):
            kill_counts[i] += killed

    # Split into test and train mutants
    test_mutant_indices = [i for i, count in enumerate(kill_counts) if (count / total_inputs) <= test_threshold]
    train_mutant_indices = [i for i in range(num_mutants) if i not in test_mutant_indices]

    # Generate separate filtered profiles
    test_filtered_profiles = {
        profile: [status[i] for i in test_mutant_indices]
        for profile, status in filtered_profiles.items()
    }

    train_filtered_profiles = {
        profile: [status[i] for i in train_mutant_indices]
        for profile, status in filtered_profiles.items()
    }

    print(f"Test Set: {len(test_mutant_indices)} mutants (≤ {test_threshold * 100}% kill rate)")
    print(f"Train Set: {len(train_mutant_indices)} mutants (41%-45% kill rate)")

    return test_filtered_profiles, train_filtered_profiles


