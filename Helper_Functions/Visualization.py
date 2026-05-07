import os
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def analyze_return_codes_and_exceptions(root_dir):
    return_code_0 = 0
    return_code_non_zero = 0
    exceptions_dict = {}

    for subdir, _, files in os.walk(root_dir):
        files_set = set(files)

        # --- return code ---
        if "return_code.txt" in files_set:
            with open(os.path.join(subdir, "return_code.txt"), "r", encoding="utf-8") as f:
                line = f.readline().strip()
            m = re.search(r"Return Code:\s*(-?\d+)", line)
            if m:
                rc = int(m.group(1))
                if rc == 0:
                    return_code_0 += 1
                else:
                    return_code_non_zero += 1

        # --- exception (separate file in the new flow) ---
        if "exception.txt" in files_set:
            with open(os.path.join(subdir, "exception.txt"), "r", encoding="utf-8") as f:
                ex_line = f.readline().strip()

            if ex_line and ex_line != "<no_exception>":
                # try to extract the exception type (fully-qualified or simple)
                # e.g., java.lang.NullPointerException: ...  -> NullPointerException
                #       org.foo.BarException                 -> BarException
                m = re.search(r"([A-Za-z_]\w*(?:Exception|Error))", ex_line.split()[-1])
                if not m:
                    # fallback: last token with "Exception"/"Error" anywhere
                    m = re.search(r"([A-Za-z_]\w*(?:Exception|Error))", ex_line)
                if m:
                    exc_short = m.group(1)
                else:
                    # as a last resort, bucket by the full first line
                    exc_short = ex_line[:120]
                exceptions_dict[exc_short] = exceptions_dict.get(exc_short, 0) + 1

    # --- plots ---
    plt.figure()
    plt.bar(['0', 'Non-zero'], [return_code_0, return_code_non_zero], color=['green', 'red'])
    plt.title('Return Code Distribution')
    plt.ylabel('Count')
    plt.xlabel('Return Codes')
    plt.savefig(os.path.join(root_dir, 'return_code_distribution.png'))
    plt.close()

    plt.figure()
    exceptions, counts = zip(*exceptions_dict.items()) if exceptions_dict else ([], [])
    plt.bar(exceptions, counts, color='blue')
    plt.title('Exception Distribution')
    plt.ylabel('Count')
    plt.xlabel('Exceptions')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(root_dir, 'exception_distribution.png'))
    plt.close()



# Save mutation score to visualize representation
def plot_mutation_scores(summary_results, save_results_path=None):
    """
    Plot and optionally save the comparison of cluster-based and random-based mutation scores.

    Args:
        summary_results: A list of dictionaries containing sample sizes, cluster-based scores, and random-based scores.
        save_results_path: Optional path to save the plot image. If not provided, the plot will just be displayed.
    """
    # Extract sample sizes and scores from summary_results
    sample_sizes = []
    cluster_based_scores = []
    random_based_scores = []

    for result in summary_results:
        sample_size = result['Sample Size']
        cluster_score = result['Cluster-Based Score[Mean]']
        random_score = result['Random-Based Score[Mean]']

        sample_sizes.append(sample_size)
        cluster_based_scores.append(cluster_score)
        random_based_scores.append(random_score)
        # # Stop adding points to the curve if cluster-based score reaches the plateau (e.g., 1.0)
        # if cluster_score >= 1.0:
        #     break  # Stop further plotting as we reached the plateau

    plt.figure(figsize=(10, 6))

    # Plotting the Cluster-Based and Random-Based Mean Scores
    plt.plot(sample_sizes, cluster_based_scores, marker='o', label='Cluster-Based Mean Score', color='blue')
    plt.plot(sample_sizes, random_based_scores, marker='o', label='Random-Based Mean Score', color='orange')

    # Extract our_trained_models name, algorithm, and score type from the save_results_path
    if save_results_path:
        try:
            filename = os.path.basename(save_results_path)
            parts = filename.split('__')
            model_name = parts[0] if len(parts) > 0 else "Model"
            algorithm_name = parts[1] if len(parts) > 1 else "Algorithm"
            score_type = parts[2] if len(parts) > 2 else "Score"
        except IndexError:
            model_name = "Model"
            algorithm_name = "Algorithm"
            score_type = "Score"

        title = f"{model_name} - {algorithm_name}: {score_type}"
    else:
        title = 'Comparison of Cluster-Based and Random-Based Mutation Scores'

    # Adding titles and labels
    plt.title(title)
    plt.xlabel('Sample Size')
    plt.ylabel('Mean Mutation Score')

    # # Set x-axis ticks to intervals of 50
    plt.xticks(range(min(sample_sizes), max(sample_sizes) + 1, 5))

    # Adding a legend
    plt.legend()

    # Adding grid for better readability
    plt.grid(True)

    # Save the plot if save_results_path is provided
    if save_results_path:
        os.makedirs(os.path.dirname(save_results_path), exist_ok=True)
        plt.savefig(save_results_path)
        # print(f"Plot saved to {save_results_path}")

    # Display the plot
    # plt.show()


def plot_combined_mutation_scores(combined_results, save_results_path=None,sample_sizes=None, process_type="mutation", runs=5):
    """
    Plot and optionally save the combined mutation score comparison for random and multiple clustering approaches.


        :param sample_sizes:
        :param runs:
        :param combined_results: Dictionary where each key is a our_trained_models-algorithm combination, and each value is a dictionary
                          containing mutation scores and AUC (e.g., {"scores": [...], "AUC": ...}).
        :param save_results_path: Optional path to save the plot image.
        If not provided, the plot will just be displayed.
        :param process_type: Mutation or coverage
    """

    plt.figure(figsize=(14, 10))
    # Extract AUC values and apply min-max normalization
    auc_values = {key: value['AUC'] for key, value in combined_results.items()}
    auc_array = np.array(list(auc_values.values()))

    # min_auc, max_auc = np.min(auc_array), np.max(auc_array)
    #normalized_auc = (auc_array - min_auc) / (max_auc - min_auc)  # Min-Max normalization
    max_auc = np.max(auc_array)

    if max_auc == 0:
        normalized_auc = np.zeros_like(auc_array)  # Avoid division by zero, set all to 0
    else:
        normalized_auc = auc_array / max_auc

    # Store normalized AUC in dictionary
    normalized_auc_values = {key: norm_val for key, norm_val in zip(auc_values.keys(), normalized_auc)}

    # Sorting by normalized AUC (highest to lowest)
    sorted_combined_results = sorted(combined_results.items(), key=lambda x: normalized_auc_values[x[0]], reverse=True)
    # Plot Random mutation score as baseline
    random_scores = combined_results["Random"]["scores"] # Extract scores only
    # random_scores = next(iter(combined_results.values()))["Random"]["scores"]


    plt.plot(sample_sizes, random_scores, marker='o',
             label=f"Random (AUC: {auc_values['Random']:.2f}, Norm: {normalized_auc_values['Random']:.2f})",
             color='black', linestyle='--', linewidth=2, alpha=0.8)

    # Plot Greedy mutation score
    if "Greedy" in combined_results:
        greedy_scores = combined_results["Greedy"]["scores"]
        plt.plot(sample_sizes, greedy_scores, marker='o',
                 label=f"Greedy (AUC: {auc_values['Greedy']:.2f}, Norm: {normalized_auc_values['Greedy']:.2f})",
                 color='red', linestyle=':', linewidth=2, alpha=0.8)
    # Plot the mutation scores for each combination of vector our_trained_models and clustering algorithm
    for model_algo, data in sorted_combined_results:
        if model_algo not in ["Random", "Greedy"]:  # Skip plotting Random and Greedy again
            scores = data["scores"]
            plt.plot(sample_sizes, scores, marker='o',
                     label=f"{model_algo} (AUC: {auc_values[model_algo]:.2f}, Norm: {normalized_auc_values[model_algo]:.2f})",
                     linestyle='-', linewidth=1.5, alpha=0.8)

    # Adding titles and labels
    plt.title(f'Comparison of Random, Greedy, and Cluster-Based {process_type.capitalize()} Scores', fontsize=16)
    plt.xlabel(f'Sample Size [Run {runs} times]', fontsize=14)
    plt.ylabel(f'{process_type.capitalize()} Score', fontsize=14)

    # Adding a legend with increased font size
    plt.legend(loc='lower right', fontsize=12)

    # Adding grid for better readability
    plt.grid(True)

    # Save the plot if save_results_path is provided
    if save_results_path:
        plt.savefig(save_results_path)
        print(f"Plot saved to {save_results_path}")
    else:
        plt.show()
    # Save AUC values as CSV
    save_auc_table_to_csv(auc_values, normalized_auc_values, save_results_path)


def flatten_groups_to_pairs_from_fold(groups):
    """
    Flatten a list of groups to extract all pairs.

    Args:
        groups (list): List of groups, where each group contains pairs.

    Returns:
        list: Flattened list of all pairs.
    """
    return [pair for group in groups for pair in group]
def flatten_groups_to_pairs_from_json(groups):
    """
     Flatten a list of groups to extract all pairs.

     Args:
         groups (list): List of groups, where each group contains pairs.

     Returns:
         list: Flattened list of all pairs.
     """
    flattened = []
    for group in groups:
        if isinstance(group, list) and len(group) == 3:  # Ensure it's a triplet
            flattened.append(group)
        elif isinstance(group, list):  # Handle incorrectly flattened lists
            for i in range(0, len(group), 3):
                flattened.append(group[i:i + 3])
    return flattened


def save_auc_table_to_csv(auc_values, normalized_auc_values, save_results_path):
    """
    Saves the AUC values (raw and normalized) to a CSV file.

    Args:
        auc_values (dict): Dictionary with raw AUC values.
        normalized_auc_values (dict): Dictionary with normalized AUC values.
        save_results_path (str): Base path for saving.
    """
    csv_path = os.path.join(os.path.dirname(save_results_path), "Normalized_AUC_Values.csv")

    # Convert to DataFrame
    df = pd.DataFrame({
        "Model_Algorithm": list(auc_values.keys()),
        "AUC (Raw)": list(auc_values.values()),
        "AUC (Normalized)": list(normalized_auc_values.values())
    })

    # Save to CSV
    df.to_csv(csv_path, index=False)
    print(f"Normalized AUC values saved to {csv_path}")