import random


def select_random_lower_baseline(embeddings_dict, previously_selected, budget):
    """
    Random selection approach (Lower Baseline).

    Randomly selects test inputs from the embedding pool while ensuring
    monotonic accumulation — meaning once an input is selected for a smaller
    budget, it remains included for larger budgets.

    Parameters
    ----------
    embeddings_dict : dict
        Mapping {input_name: embedding_vector}.
    previously_selected : set
        Inputs already chosen in smaller budgets for the same run.
    budget : int
        Total number of inputs to select for the current budget.

    Returns
    -------
    selected_inputs : set
        Updated set of selected input names for the current budget.
    """

    # Collecting Inputs Name
    all_inputs = list(embeddings_dict.keys())

    # How many new inputs we need to add (monotonic increase)
    remaining_to_add = max(0, budget - len(previously_selected))

    if remaining_to_add <= 0:
        # Nothing to add — already have enough for this budget
        return previously_selected

    # Select randomly from un-chosen inputs
    unselected = list(set(all_inputs) - previously_selected)
    newly_selected = random.sample(unselected, remaining_to_add)

    # Return cumulative (monotonic) set
    updated_selection = set(previously_selected).union(newly_selected)
    return updated_selection