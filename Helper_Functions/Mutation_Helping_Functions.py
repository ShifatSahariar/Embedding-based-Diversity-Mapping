import os

import shutil

import random
import pandas as pd

from Helper_Functions.configs.mutation_configs import get_subject_program_mutation_config, sut_class_config_pit
from MUT_KILLING_PROFILE.Mutant_Generation import generate_mutants_PIT
from MUT_KILLING_PROFILE.MutationScore_Compare import evaluate_mutation_scores


def generate_mutants(subject_program='CALC', target_classes_override=None):
    subject_program_config = get_subject_program_mutation_config(subject_program)
    if not subject_program_config:
        raise ValueError(f"Unsupported subject program: {subject_program}")

    raw_class_names = subject_program_config["target_classes"]
    dependencies = subject_program_config.get("dependencies", [])
    target_tests = subject_program_config.get("target_tests")
    pit_config = sut_class_config_pit[subject_program]["pit"]
    project_base = pit_config["class_dir"]

    # --- Determine PIT target class names ---
    if subject_program == "basic":
        pit_target_classes = [f"basic.{cls}" for cls in raw_class_names]

    elif subject_program == "CALC":
        pit_target_classes = raw_class_names  # Calc has no package

    elif subject_program == "rhino":
        # Rhino has nested packages; normalize dynamically
        pit_target_classes = []
        for cls in raw_class_names:
            if cls.startswith("org.mozilla.javascript"):
                # already fully qualified
                pit_target_classes.append(cls)
            elif "." in cls:
                # e.g., "ast.AstNode" → org.mozilla.javascript.ast.AstNode
                pit_target_classes.append(f"org.mozilla.javascript.{cls}")
            else:
                # top-level class
                pit_target_classes.append(f"org.mozilla.javascript.{cls}")

    elif subject_program == "nashorn":
        pit_target_classes = raw_class_names
    elif subject_program == "graaljs":
        pit_target_classes = raw_class_names
    elif subject_program == "karatejs":
        pit_target_classes = raw_class_names


    else:
        raise ValueError(f"No PIT configuration for subject program {subject_program}")

    if target_classes_override:
        pit_target_classes = target_classes_override

    collection_name = "mutants_collection_smoke" if target_classes_override else "mutants_collection"
    pit_mutants_dir = f"MUT_KILLING_PROFILE/pit_mut_tool/{subject_program.upper()}/{collection_name}"
    if os.path.exists(pit_mutants_dir):
        shutil.rmtree(pit_mutants_dir)
    os.makedirs(pit_mutants_dir, exist_ok=True)

    for class_name in pit_target_classes:
        print(f"Generating mutants for {class_name} in {subject_program}...")

        generate_mutants_PIT(
            project_base=project_base,
            mutants_dir=pit_mutants_dir,
            lib_dir="MUT_KILLING_PROFILE/pit_mut_tool/*",
            target_classes=class_name,
            source_dirs=pit_config["source_dir"],
            dependencies=dependencies,
            target_tests=target_tests,
            verbose=False,
        )


    # for class_name in major_target_classes:
    #     # Handle the mutation generation for Major
    #     # MAKE THEY TARGET CLASS NAME AS DYNAMIC AS PATH FOR MAJOR
    #     major_mutants_dir = f"{subject_program.upper()}/{class_name.removesuffix('.java')}"
    #
    #     # FOR MAJOR, WE NEED TO GIVE THE PROJECT_BASE PATH DIFFERENTLY
    #     # SINCE MAJOR NEED JAVA FILES LOCATION
    #     generate_mutants_major(
    #         compile_mml_file=False,  # True if the MML file needs to be recompiled
    #         mml_filename="all.mml",  # MML file for Major mutation tool
    #         source_dir=major_config,  # source directory
    #         target_class=class_name,  # class to target
    #         major_home='MUT_KILLING_PROFILE/major_mut_tool',  # Major mutation tool home
    #         mutants_dir=major_mutants_dir,  # Directory for storing
    #         dependency_jar=dependencies  # Dependency (e.g., ANTLR jar for 'CALC')
    #     )
        print(f"Finished generating mutants for target class in {subject_program}.")



def calculate_file_mutation_scores(mutation_profiles):
    """
    Calculate the mutation score for each file/input.
    """
    file_scores = {}
    for file, profile in mutation_profiles.items():
        score = sum(map(int, profile)) / len(profile) if profile else 0
        file_scores[file] = score
    return file_scores


# def compute_random_mutation_scores(test_profiles, sample_sizes, runs):
#     """
#     Compute random-based mutation scores across multiple runs.
#
#     Args:
#         test_profiles: Dictionary of mutation profiles.
#         sample_sizes: List of sample sizes.
#         runs: Number of runs.
#
#     Returns:
#         A dictionary with random-based mutation scores for each sample size.
#     """
#     all_random_scores = {sample_size: [] for sample_size in sample_sizes}
#
#     for _ in range(runs):
#         all_items = list(test_profiles.keys())  # All mutation profiles
#         for sample_size in sample_sizes:
#             adjusted_sample_size = min(sample_size, len(all_items))
#             random_samples = random.sample(all_items, adjusted_sample_size)
#             random_score = evaluate_mutation_scores(random_samples, test_profiles)
#             all_random_scores[sample_size].append(random_score)
#
#     return all_random_scores



def calculate_random_run(test_profiles, sample_sizes):
    """
    Computes a monotonic random-based mutation score curve for a single run.
    Each larger sample contains all inputs from smaller samples.

    Args:
        test_profiles: Dictionary of mutation profiles for the current run.
        sample_sizes: List of sample sizes to evaluate.

    Returns:
        A dictionary where keys are sample sizes and values are the
        mutation scores for this single random run.
        Example: {1: 0.1, 2: 0.15, 3: 0.22, ...}
    """
    scores_for_this_run = {}

    # Get all possible test cases and shuffle them once to create a random order
    all_items = list(test_profiles.keys())
    random.shuffle(all_items)

    cumulative_sample = []  # Store test cases in an incremental manner

    for sample_size in sample_sizes:
        # Ensure we don't try to select more items than available
        adjusted_sample_size = min(sample_size, len(all_items))

        # Grow the cumulative sample based on the shuffled order
        new_tests_needed = adjusted_sample_size - len(cumulative_sample)
        if new_tests_needed > 0:
            start_index = len(cumulative_sample)
            end_index = start_index + new_tests_needed
            cumulative_sample.extend(all_items[start_index:end_index])

        # Evaluate the score for the current cumulative sample
        random_score = evaluate_mutation_scores(cumulative_sample, test_profiles)
        scores_for_this_run[sample_size] = random_score

    return scores_for_this_run
def compute_random_mutation_scores(test_profiles, sample_sizes, runs):
    """
    Compute monotonic random-based mutation scores across multiple runs.
    Each larger sample contains all inputs from smaller samples.

    Args:
        test_profiles: Dictionary of mutation profiles.
        sample_sizes: List of sample sizes.
        runs: Number of runs.

    Returns:
        A dictionary with monotonic random-based mutation scores for each sample size.
    """
    all_random_scores = {sample_size: [] for sample_size in sample_sizes}

    for _ in range(runs):
        all_items = list(test_profiles.keys())  # Keys of the input(name)
        random.shuffle(all_items)  # Shuffle once per run to ensure randomness

        cumulative_sample = []  # Store test cases in an incremental manner

        for sample_size in sample_sizes:
            adjusted_sample_size = min(sample_size, len(all_items))

            # Grow the cumulative sample without resetting
            new_tests_needed = adjusted_sample_size - len(cumulative_sample)
            if new_tests_needed > 0:
                cumulative_sample.extend(all_items[len(cumulative_sample):len(cumulative_sample) + new_tests_needed])

            random_score = evaluate_mutation_scores(cumulative_sample, test_profiles)
            all_random_scores[sample_size].append(random_score)

    return all_random_scores


def save_greedy_mutation_score(selected_inputs, mutation_score, save_mutation_cluster_results):
    """
    Save the selected inputs and mutation score to a CSV file in the given directory.

    Args:
        selected_inputs: List of selected input IDs.
        mutation_score: Mutation score based on how many mutants were killed out of the total.
        save_mutation_cluster_results: Base directory where the CSV file will be saved.
    """
    # Define the file name and path
    file_name = "Greedy-Mutation-Score.csv"
    save_path = os.path.join(save_mutation_cluster_results, file_name)

    # Create a DataFrame with the results
    data = {
        'Selected Profiles': [', '.join(map(str, selected_inputs))],
        'Total Profiles': [len(selected_inputs)],
        'Mutation score': [mutation_score]
    }

    df = pd.DataFrame(data)

    # Add a note as the last row (corrected to match the number of columns)
    df.loc[1] = ['Greedy approach does not depend on any vector models or cluster algorithm', '', '']

    # Create the directory if it does not exist
    os.makedirs(save_mutation_cluster_results, exist_ok=True)

    # Save the DataFrame to a CSV file
    df.to_csv(save_path, index=False)




def aggregate_mutants(subject_program='CALC', aggregated_mutants_path=None, shuffle_mutants=True):
    """
    Aggregates mutants from PIT (and optionally Major) for multiple classes.
    Supports mixed-depth packages (e.g., org.mozilla.javascript.* and org.mozilla.javascript.ast.*).
    """

    subject_program_config = get_subject_program_mutation_config(subject_program)
    if not subject_program_config:
        raise ValueError(f"Unsupported subject program: {subject_program}")

    target_classes = subject_program_config["target_classes"]
    package_prefix = subject_program_config.get("package_prefix")

    # Clear existing folder if present
    if os.path.exists(aggregated_mutants_path):
        print(f"Removing existing folder {aggregated_mutants_path}...")
        shutil.rmtree(aggregated_mutants_path)
    os.makedirs(aggregated_mutants_path, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helper: Collect mutants from one tool path
    # ------------------------------------------------------------------
    def collect_mutants_from_tool(tool_path, starting_index):
        collected_mutants = []
        if not os.path.exists(tool_path):
            print(f"[WARN] Path {tool_path} does not exist. Skipping...")
            return collected_mutants, starting_index

        for folder_name in os.listdir(tool_path):
            folder_path = os.path.join(tool_path, folder_name)
            if not (os.path.isdir(folder_path) and folder_name.isdigit()):
                continue

            # Copy valid mutant folders
            if any(f.endswith(".class") for f in os.listdir(folder_path)):
                new_folder_name = str(starting_index)
                destination_folder = os.path.join(aggregated_mutants_path, new_folder_name)
                shutil.copytree(folder_path, destination_folder)

                # Keep full class names (do not strip "org.mozilla.javascript.*")
                # Just ensure file names end correctly
                for filename in os.listdir(destination_folder):
                    if filename.endswith(".class") and filename.count(".") >= 1:
                        # Example: org.mozilla.javascript.ast.AstNode.class → keep as-is
                        # We only fix cases like "AstNode..class"
                        new_name = filename.replace("..", ".")
                        if new_name != filename:
                            os.rename(os.path.join(destination_folder, filename),
                                      os.path.join(destination_folder, new_name))

                collected_mutants.append(new_folder_name)
                starting_index += 1
        return collected_mutants, starting_index

    # ------------------------------------------------------------------
    # Aggregation logic
    # ------------------------------------------------------------------
    current_index = 1
    all_collected_mutants = []

    for class_name in target_classes:
        print(f"[INFO] Aggregating mutants for: {class_name}")

        # --- CALC (no package) ---
        if subject_program == "CALC":
            export_folder = class_name

        # --- BASIC (single package) ---
        elif subject_program == "basic":
            export_folder = f"{package_prefix}/{class_name}"

        # --- RHINO (mixed depth) ---
        elif subject_program == "rhino":
            # If user wrote "ast.AstNode" or "optimizer.Optimizer" etc.
            if "." in class_name:
                # append to org.mozilla.javascript → org.mozilla.javascript.ast.AstNode
                export_folder = f"{package_prefix}.{class_name}".replace(".", "/")
            elif class_name.startswith("org.mozilla.javascript"):
                # already fully qualified
                export_folder = class_name.replace(".", "/")
            else:
                # top-level class under org.mozilla.javascript
                export_folder = f"{package_prefix.replace('.', '/')}/{class_name}"
        elif subject_program == "nashorn":
            # Example: org.openjdk.nashorn.internal.parser.Parser
            export_folder = class_name.replace(".", "/")
        elif subject_program == "graaljs":
            # Example: org.openjdk.nashorn.internal.parser.Parser
            export_folder = class_name.replace(".", "/")
        elif subject_program == "karatejs":
            # Example: org.openjdk.nashorn.internal.parser.Parser
            export_folder = class_name.replace(".", "/")
        else:
            export_folder = class_name

        pit_mutants_path = (
            f"MUT_KILLING_PROFILE/pit_mut_tool/{subject_program.upper()}/"
            f"mutants_collection/export/{export_folder}/mutants"
        )

        # Collect PIT mutants
        pit_collected, current_index = collect_mutants_from_tool(pit_mutants_path, current_index)
        all_collected_mutants.extend(pit_collected)

    if not all_collected_mutants:
        print("[WARN] No mutants found in any tool paths.")
    else:
        print(f"[INFO] Aggregated {len(all_collected_mutants)} mutants into {aggregated_mutants_path}")

    # Optional shuffle
    # if shuffle_mutants:
    #     random.shuffle(all_collected_mutants)

    return sorted(all_collected_mutants, key=lambda x: int(os.path.basename(x)))

    # [
    # '/path/to/aggregated_mutants/1',
    # '/path/to/aggregated_mutants/2',
    # '/path/to/aggregated_mutants/3',
    # '/path/to/aggregated_mutants/5',
    # '/path/to/aggregated_mutants/10'
    # ]


# the previous implementation was just splitting the mutants into two folders
# if we use this approach, we have to generate the profiles multiple times incase we want to generate N times.
def split_mutants_to_training_and_testing(subject_program, aggregated_mutants_path):
    """
    Splits the aggregated mutants into training and testing sets by randomly selecting 80% for training
    and 20% for testing.

    :param aggregated_mutants_path:
    :param subject_program: The subject program for which to split mutants (e.g., 'CALC', 'basic').
    """
    # Define the paths
    # aggregated_mutants_path = f"MUT_KILLING_PROFILE/{subject_program.upper()}/aggregated_mutants"
    training_mutants_path = f"MUT_KILLING_PROFILE/{subject_program.upper()}/Training_mutants"
    testing_mutants_path = f"MUT_KILLING_PROFILE/{subject_program.upper()}/Testing_mutants"

    # Ensure the aggregated mutants folder exists
    if not os.path.exists(aggregated_mutants_path):
        raise ValueError(f"Aggregated mutants folder does not exist: {aggregated_mutants_path}")

    # If the training or testing folders exist, remove them to start fresh
    if os.path.exists(training_mutants_path):
        shutil.rmtree(training_mutants_path)
    if os.path.exists(testing_mutants_path):
        shutil.rmtree(testing_mutants_path)

    # Recreate training and testing folders
    os.makedirs(training_mutants_path, exist_ok=True)
    os.makedirs(testing_mutants_path, exist_ok=True)

    # Get the list of all mutant folders in the aggregated folder
    all_mutant_folders = [f for f in os.listdir(aggregated_mutants_path) if
                          os.path.isdir(os.path.join(aggregated_mutants_path, f))]

    # Shuffle the list to ensure randomness
    random.shuffle(all_mutant_folders)

    # Split the mutant folders (80% training, 20% testing)
    total_mutants = len(all_mutant_folders)
    split_index = int(0.8 * total_mutants)

    training_mutants = all_mutant_folders[:split_index]
    testing_mutants = all_mutant_folders[split_index:]

    # Copy the selected mutants to their respective folders
    for mutant_folder in training_mutants:
        # search the mutant folder in the source dir
        source_folder = os.path.join(aggregated_mutants_path, mutant_folder)
        # copy the mutant folder to training dir
        destination_folder = os.path.join(training_mutants_path, mutant_folder)
        shutil.copytree(source_folder, destination_folder)

    for mutant_folder in testing_mutants:
        # search the mutant folder in the source dir
        source_folder = os.path.join(aggregated_mutants_path, mutant_folder)
        # copy the mutant folder to testing dir
        destination_folder = os.path.join(testing_mutants_path, mutant_folder)
        shutil.copytree(source_folder, destination_folder)

    print(f"Mutants split into training and testing sets.")
    print(f"Training mutants: {len(training_mutants)}")
    print(f"Testing mutants: {len(testing_mutants)}")


"""
Lets assume we have list of mutants in the aggregated dir _> ['3', '1', '2', '10', '5']
->> we will sort them like ['1', '2', '3', '5', '10']
->> and store the path of each mutants to return like following
    [
    '/path/to/aggregated_mutants/1',
    '/path/to/aggregated_mutants/2',
    '/path/to/aggregated_mutants/3',
    '/path/to/aggregated_mutants/5',
    '/path/to/aggregated_mutants/10'
    ]

"""


def sort_mutants(aggregated_mutants_path):
    """
    Sort mutants in the given directory by their numeric order.

    Args:
        aggregated_mutants_path: The directory where all mutants are stored.

    Returns:
        A list of sorted mutant paths.
    """
    # Only include entries that are purely digits, ignoring .DS_Store or any other non-numeric folders
    mutants = [m for m in os.listdir(aggregated_mutants_path) if m.isdigit()]

    # Sort them numerically
    sorted_mutants = sorted(mutants, key=lambda x: int(x))

    # Create full paths
    sorted_mutant_paths = [os.path.join(aggregated_mutants_path, mutant) for mutant in sorted_mutants]

    return sorted_mutant_paths

def split_train_test(num_mutants, train_ratio=0.8):
    """Splits mutants into a single train-test split based on the given ratio."""
    num_train = int(train_ratio * num_mutants)
    indices = list(range(num_mutants))
    random.shuffle(indices)  # Shuffle once

    train_indices = indices[:num_train]
    test_indices = indices[num_train:]

    return train_indices, test_indices

def create_train_test_splits(num_mutants, N=1, train_ratio=0.8):

    num_train = int(train_ratio * num_mutants)  # size of the training set
    splits = []
    for epoch in range(N):
        indices = list(range(num_mutants))
        random.shuffle(indices)

        train_indices = indices[:num_train]
        test_indices = indices[num_train:]

        splits.append((train_indices, test_indices))

    return splits


def generate_train_test_killing_profiles(subject_program, main_killing_profiles, train_indices, test_indices):
    """
    Generates killing profiles for training and testing sets and stores them in separate directories.

    Args:
        subject_program (str): Name of the subject program.
        main_killing_profiles (dict): Dictionary of main killing profiles for each input file.
        train_indices (list): List of mutant indices for training.
        test_indices (list): List of mutant indices for testing.

    Returns:
        None
    """

    base_output_dir = os.path.join("MUT_KILLING_PROFILE",subject_program.upper())

    # Define separate directories for train and test profiles
    train_dir = os.path.join(base_output_dir, "train_mut_kill_profiles")
    test_dir = os.path.join(base_output_dir, "test_mut_kill_profiles")

    # Remove existing directories if they exist, then recreate them
    for dir_path in [train_dir, test_dir]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path)

    # Generate killing profiles for train and test sets
    for input_file, main_profile in main_killing_profiles.items():
        # Extract train profiles
        train_profile = [main_profile[i] for i in train_indices]
        with open(os.path.join(train_dir, input_file), 'w') as f:
            f.write(' '.join(map(str, train_profile)))

        # Extract test profiles
        test_profile = [main_profile[i] for i in test_indices]
        with open(os.path.join(test_dir, input_file), 'w') as f:
            f.write(' '.join(map(str, test_profile)))

    print(f"Killing profiles have been generated and stored in:\n  - {train_dir}\n  - {test_dir}")



def generate_killing_profiles_for_splits(subject_program, main_killing_profiles, splits):
    """
    main_killing_profiles = {
    "Input_1.txt": [1, 0, 1, 1, 0, 1],
    "Input_2.txt": [0, 1, 0, 0, 1, 0],
    "Input_3.txt": [1, 1, 1, 0, 1, 1],
    }
    lets say we have 6 mutants in order [1,2,3,4,5,6]

    splits = [
    ([0, 1, 2, 3], [4, 5]),
    ([1, 2, 3, 4], [0, 5]),
]
    Generate killing profiles for each train-test split and store them in the output directory.

    Args:
        main_killing_profiles: Dictionary of main killing profiles for each input.
        mutant_paths: List of sorted mutant paths.
        splits: List of tuples containing train and test indices for each split.
        output_dir: The base directory where train-test profiles will be stored.

    Returns:
        None
        :param splits:

        :param main_killing_profiles:
        :param subject_program:
    """
    output_dir = f"MUT_KILLING_PROFILE/{subject_program.upper()}/all_train_test_profiles"

    # Check if the output directory exists, if so, remove it
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    # Recreate the output directory
    os.makedirs(output_dir)

    # Loop over each epoch (split)
    for epoch, (train_indices, test_indices) in enumerate(splits):
        # Create directories for train and test profiles for this epoch
        train_dir = os.path.join(output_dir, f"epoch_{epoch + 1}_train_mut_kill_profiles")
        test_dir = os.path.join(output_dir, f"epoch_{epoch + 1}_test_mut_kill_profiles")

        os.makedirs(train_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)

        # For each input file, extract killing profiles based on the indices
        for input_file, main_profile in main_killing_profiles.items():
            # Extract train profiles
            train_profile = [main_profile[i] for i in train_indices]
            with open(os.path.join(train_dir, f"{input_file}"), 'w') as f:
                f.write(' '.join(map(str, train_profile)))

            # Extract test profiles
            test_profile = [main_profile[i] for i in test_indices]
            with open(os.path.join(test_dir, f"{input_file}"), 'w') as f:
                f.write(' '.join(map(str, test_profile)))

    print(f"Killing profiles for {len(splits)} epochs have been generated and stored in {output_dir}.")


def load_main_killing_profiles_from_dir(profiles_directory):
    """
    Loads killing profiles from files in a specified directory and formats them in a dictionary.
    """
    killing_profiles = {}

    for file_name in os.listdir(profiles_directory):
        file_path = os.path.join(profiles_directory, file_name)

        if os.path.isfile(file_path):
            # Open the file and print raw content for debugging
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_content = f.read().strip()
                # print(f"Debug: File {file_name} Raw Content ->", repr(raw_content))  # Print raw content

            # Convert only if content is numeric
            try:
                killing_statuses = list(map(int, raw_content.split()))
                killing_profiles[file_name] = killing_statuses
            except ValueError as e:
                print(f"Skipping {file_name} due to non-integer values. Error: {e}")

    return killing_profiles

def load_main_killing_profiles_from_dir_2(profiles_directory):
    """
    Loads killing profiles from files in a specified directory and formats them in a dictionary.

    Args:
        profiles_directory: Path to the directory where profiles are stored.

    Returns:
        A dictionary with file names (e.g., 'Input_1.txt') as keys and lists of killing statuses as values.
        Example:
        {
            "Input_1.txt": [1, 0, 1],
            "Input_2.txt": [0, 1, 0],
            ...
        }
    """
    killing_profiles = {}

    # Iterate over each file in the profiles directory
    for file_name in os.listdir(profiles_directory):
        file_path = os.path.join(profiles_directory, file_name)

        # Check if the file path is actually a file (not a directory)
        if os.path.isfile(file_path):
            # Read the contents of the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                killing_statuses = list(map(int, f.read().strip().split()))

            # Store in the dictionary using the file name as the key
            killing_profiles[file_name] = killing_statuses

    return killing_profiles

# Example usage:
# profiles_directory = "path_to_your_saved_profiles_folder"
# killing_profiles = load_killing_profiles_from_directory(profiles_directory)
# print(killing_profiles)
def gather_sorted_mutant_paths(base_path):
    """
    Looks in `base_path` (e.g., MUT_KILLING_PROFILE/CALC/aggregated_mutants),
    finds subfolders named '1', '2', '3', etc., sorts them numerically,
    and returns a list of full directory paths.
    """
    # List only subfolders with digit names
    subfolders = [
        d for d in os.listdir(base_path)
        if d.isdigit() and os.path.isdir(os.path.join(base_path, d))
    ]
    # Sort them in ascending numeric order
    subfolders.sort(key=lambda x: int(x))

    # Build absolute paths
    full_paths = [os.path.join(base_path, d) for d in subfolders]
    return full_paths

def restore_original_classes(original_class_directory):
    """Restores all .class.backup files recursively."""
    restored = 0
    for root, _, files in os.walk(original_class_directory):
        for file in files:
            if file.endswith(".class.backup"):
                backup_path = os.path.join(root, file)
                target_path = backup_path[:-7]  # remove ".backup"
                try:
                    os.replace(backup_path, target_path)
                    restored += 1
                    print(f"[RESTORED] {target_path}")
                except Exception as e:
                    print(f"[ERROR] Failed to restore {backup_path}: {e}")
    if restored:
        print(f"[RESTORE] {restored} class file(s) restored.")



def replace_class_with_mutant(mutant_dir, original_class_directory):
    """
    Replaces the correct .class file(s) in the original directory with the corresponding mutant versions.
    Handles nested packages (e.g., org.mozilla.javascript.ast.*).
    """
    mutant_class_files = [f for f in os.listdir(mutant_dir) if f.endswith(".class")]
    if not mutant_class_files:
        print(f"[SKIP] No .class file in {mutant_dir}")
        return None

    replaced_files = []

    for mutant_class_file in mutant_class_files:
        # Example: org.mozilla.javascript.ast.AstNode.class
        class_name = mutant_class_file[:-6]  # remove '.class'
        class_path = class_name.replace('.', os.sep) + '.class'  # nested path form

        target_class_path = os.path.join(original_class_directory, class_path)
        mutant_class_path = os.path.join(mutant_dir, mutant_class_file)

        if not os.path.exists(target_class_path):
            print(f"[WARN] Target class not found for mutant: {class_name}")
            continue

        backup_path = target_class_path + ".backup"

        # Create backup only once
        if not os.path.exists(backup_path):
            shutil.copyfile(target_class_path, backup_path)
            print(f"[BACKUP] {backup_path}")
        else:
            print(f"[INFO] Backup already exists: {backup_path}")

        # Replace with mutant
        shutil.copyfile(mutant_class_path, target_class_path)
        print(f"[REPLACED] {target_class_path} ← {mutant_class_path}")

        replaced_files.append(class_name)

    return replaced_files
