import os

import numpy as np

from FUZZ_TOOL_SELECTION.utils.ms_score_utils import select_mutants_global


def filter_mutation_profiles(mut_profiles_dict,
                             min_rate=0.0,
                             max_rate=0.5,
                             drop_never=True,
                             drop_always=True,
                             dedup=True,
                             subsumption=True,
                             save_csv_path=None):
    """
    Apply global mutant filtering once for all tools/approaches.
    Optionally save the filtered mutation profiles as CSV.
    """

    # ----------------------------------------------------------
    # Convert dict → matrix for filtering
    input_names = list(mut_profiles_dict.keys())
    mat = np.array([mut_profiles_dict[name] for name in input_names])

    # Ensure matrix is boolean or integer (required for np.packbits)
    mat = (mat > 0).astype(bool)

    # ----------------------------------------------------------
    # Apply global mutant filtering
    keep_mask, kept_count = select_mutants_global(
        mat,
        min_rate=min_rate,
        max_rate=max_rate,
        drop_never=drop_never,
        drop_always=drop_always,
        dedup=dedup,
        subsumption=subsumption
    )
    print(f"[INFO] Mutant filtering complete: kept {kept_count}/{mat.shape[1]} mutants.")

    # ----------------------------------------------------------
    # Apply mask column-wise to every profile
    filtered_profiles = {
        name: mat[i, keep_mask]
        for i, name in enumerate(input_names)
    }

    # OPTIONAL SAVE
    # ----------------------------------------------------------
    if save_csv_path is not None:
        import pandas as pd
        df = pd.DataFrame(
            [mat[i, keep_mask] for i in range(len(input_names))],
            index=input_names
        )
        df.to_csv(save_csv_path)
        print(f"[INFO] Saved filtered mutation profiles to: {save_csv_path}")

    return filtered_profiles, keep_mask



def compute_mutation_score_for_selected_inputs(selected_inputs, filtered_profiles_dict):

    if not selected_inputs:
        return 0.0

    # Collect mutation profiles of the selected inputs
    profiles = [filtered_profiles_dict[name] for name in selected_inputs if name in filtered_profiles_dict]

    if not profiles:
        return 0.0  # No valid profiles found

    # Stack into matrix: shape = (#selected_inputs × #mutants_kept)
    mat = np.vstack(profiles)

    # ----------------------------------------------------------
    # Compute which mutants were killed by any selected input
    mutants_killed = np.any(mat == 1, axis=0)  # OR across rows

    # Compute mutation score
    total_mutants = mat.shape[1]
    ms_score = mutants_killed.sum() / max(1, total_mutants)

    return float(round(ms_score, 6))

# Loading Mutation Profiles with Prefix
# ============================================================
def load_mutation_profiles(run_dir, prefix, allowed_names=None):
    """
    Load mutation profiles filtered by prefix and optionally restricted
    to a given set of allowed input names (from embeddings).
    """
    profiles = {}
    for file in sorted(os.listdir(run_dir)):
        if not file.startswith(prefix) or not file.endswith(".txt"):
            continue

        name = file.replace(".txt", "")
        if allowed_names and name not in allowed_names:
            continue

        path = os.path.join(run_dir, file)
        try:
            prof = np.loadtxt(path)
            profiles[name] = prof.astype(bool)
        except Exception as e:
            print(f"[Warning] Skipped {file}: {e}")

    print(f"[INFO] Loaded {len(profiles)} mutation profiles from {run_dir}")
    return profiles
