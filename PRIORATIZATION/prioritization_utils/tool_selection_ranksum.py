import os
import pandas as pd


# --------------------------------------------------------------
# Function 1: Compute RankSum for ALL models and save results
# --------------------------------------------------------------
def compute_ranksum_all_models(
        base_dir,
        candidate_tools,
        n_runs=None,
        filename_prefix="cluster_coverage_summary_run_",
        save_dir=None
    ):
    """
    Computes per-model RankSum across all runs.
    Saves:
        ranksum_all_models.csv
        winning_tool_per_model.csv
    """

    if save_dir is None:
        save_dir = base_dir
    os.makedirs(save_dir, exist_ok=True)

    # Detect run folders
    run_folders = sorted([d for d in os.listdir(base_dir) if d.startswith("run_")])

    if n_runs is None:
        n_runs = len(run_folders)

    print(f"[INFO] Found runs: {run_folders[:n_runs]}")

    # Dictionary: model -> list of per-run ranking series
    model_rankings = {}

    # --------------------------------------------------
    # Process each run folder
    # --------------------------------------------------
    for run_name in run_folders[:n_runs]:

        run_path = os.path.join(base_dir, run_name)

        # Extract actual run number (e.g., "run_10" → "10")
        run_number = run_name.split("_")[1]

        # Now map correctly to the file name inside the folder
        csv_path = os.path.join(run_path, f"{filename_prefix}{run_number}.csv")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing CSV: {csv_path}")

        df = pd.read_csv(csv_path)

        # available models
        models_in_run = df["Model"].unique()

        # --------------------------------------------------
        # For each model, extract row, extract tool values, rank
        # --------------------------------------------------
        for model in models_in_run:
            row = df[df["Model"] == model].iloc[0]

            tool_values = row[candidate_tools]

            # descending ranking (higher coverage = better)
            ranked = tool_values.sort_values(ascending=False)

            # store ranking for model
            model_rankings.setdefault(model, []).append(ranked)

    # -------------------------------------------------------
    # Convert per-run rankings → RankSum per model
    # -------------------------------------------------------
    ranksum_dict = {}

    for model, per_run_list in model_rankings.items():

        # Build DataFrame: columns = run_i, rows = tools
        rank_df = pd.DataFrame({
            f"run_{i+1}": per_run_list[i].rank(ascending=False, method="min")
            for i in range(len(per_run_list))
        })

        # RankSum = sum of ranks across runs
        ranksum = rank_df.sum(axis=1)

        ranksum_dict[model] = ranksum

    # -------------------------------------------------------
    # Save RankSum for ALL MODELS
    # -------------------------------------------------------
    ranksum_all = pd.DataFrame(ranksum_dict)
    ranksum_all.to_csv(os.path.join(save_dir, "ranksum_all_models.csv"), index=True)

    # -------------------------------------------------------
    # Save winning tool for each model
    # -------------------------------------------------------
    winners = {
        model: ranksum.idxmin()
        for model, ranksum in ranksum_dict.items()
    }

    winners_df = pd.DataFrame(list(winners.items()), columns=["Model", "BestTool"])
    winners_df.to_csv(os.path.join(save_dir, "winning_tool_per_model.csv"), index=False)

    print(f"[OK] Saved RankSum summary → {save_dir}")
    return ranksum_all, winners_df



# --------------------------------------------------------------
# Function 2: Given a model name, return best tool
# --------------------------------------------------------------
def get_best_tool(model_name, ranksum_csv_path):
    """
    Returns the best tool (lowest RankSum) for the given model.
    """
    df = pd.read_csv(ranksum_csv_path, index_col=0)

    if model_name not in df.columns:
        raise ValueError(f"Model '{model_name}' not found in RankSum CSV.")

    col = df[model_name]
    best_tool = col.idxmin()
    best_value = col.min()

    return best_tool, best_value
