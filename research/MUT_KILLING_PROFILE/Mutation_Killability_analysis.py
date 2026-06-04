import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_mutation_profiles(folder_path):
    input_kill_probs = []
    mutant_matrix = []

    # Step 1: Load all mutation profiles
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r') as f:
                line = f.read().strip()
                if line:
                    profile = [int(x) for x in line.split()]
                    mutant_matrix.append(profile)
                    input_kill_probs.append(sum(profile) / len(profile))

    if not mutant_matrix:
        print("No profiles found.")
        return

    # Convert to numpy
    mutant_matrix = np.array(mutant_matrix)
    mutant_kill_probs = mutant_matrix.sum(axis=0) / mutant_matrix.shape[0]

    # ---- Stats ----
    mean_input, std_input = np.mean(input_kill_probs), np.std(input_kill_probs)
    mean_mutant, std_mutant = np.mean(mutant_kill_probs), np.std(mutant_kill_probs)

    # ---- Plot ----
    sns.set(style="whitegrid", context="talk")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    plt.suptitle(
        "Mutation Testing Dynamics: Test Strength vs. Mutant Hardness\n"
        "(μ = mean, σ = standard deviation)",
        fontsize=17, weight='bold', y=1.05
    )

    # ===== Left: Input Strength =====
    sns.histplot(input_kill_probs, bins=20, kde=True, color="#1f77b4", ax=axes[0])
    axes[0].axvline(mean_input, color='black', linestyle='--', linewidth=2)
    axes[0].set_title("Test Input Strength (Offense)", fontsize=15)
    axes[0].set_xlabel("Fraction of Mutants Killed by Each Input")
    axes[0].set_ylabel("Number of Inputs")

    # Add explanatory box
    text_box_input = (
        f"μ = {mean_input:.2f}, σ = {std_input:.2f}\n"
        f"→ On avg., each test kills {mean_input*100:.0f}% of mutants.\n"
        f"→ σ shows variation in test strength."
    )
    axes[0].text(0.05, 0.9, text_box_input, fontsize=11, transform=axes[0].transAxes,
                 bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))

    axes[0].annotate("Weak tests", xy=(0.1, 0.65), xycoords='axes fraction', fontsize=11)
    axes[0].annotate("Strong tests", xy=(0.8, 0.65), xycoords='axes fraction', fontsize=11)

    # ===== Right: Mutant Killability =====
    sns.histplot(mutant_kill_probs, bins=20, kde=True, color="#d62728", ax=axes[1])
    axes[1].axvline(mean_mutant, color='black', linestyle='--', linewidth=2)
    axes[1].set_title("Mutant Killability (Defense)", fontsize=15)
    axes[1].set_xlabel("Fraction of Inputs That Kill Each Mutant")
    axes[1].set_ylabel("Number of Mutants")

    # Add explanatory box
    text_box_mutant = (
        f"μ = {mean_mutant:.2f}, σ = {std_mutant:.2f}\n"
        f"→ On avg., each mutant is killed by {mean_mutant*100:.0f}% of tests.\n"
        f"→ σ shows diversity in mutant hardness."
    )
    axes[1].text(0.05, 0.9, text_box_mutant, fontsize=11, transform=axes[1].transAxes,
                 bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))

    axes[1].annotate("Hard-to-kill", xy=(0.1, 0.65), xycoords='axes fraction', fontsize=11)
    axes[1].annotate("Easily killed", xy=(0.75, 0.65), xycoords='axes fraction', fontsize=11)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("mutation_killability_explained.png", dpi=300)
    # plt.show()



analyze_mutation_profiles("RHINO/mutants_killing_profiles")

