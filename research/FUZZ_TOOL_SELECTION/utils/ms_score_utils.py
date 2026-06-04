
import numpy as np
import pandas as pd
def export_input_mutant_matrix(profiles_by_tool, tool_order, keep_mask, out_dir, selected_indices=None):
    """
    Export, for each tool, an Excel file of inputs × mutants (after filtering).
    Columns = actual mutant IDs (not just sequential).
    Cells are highlighted green if True.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Use actual mutant indices if provided
    if selected_indices is not None:
        mutant_ids = [f"mutant_{idx}" for idx in selected_indices]
    else:
        # Use actual selected indices instead of renumbering
        if selected_indices is not None:
            mutant_ids = [f"mutant_{idx}" for idx in selected_indices]
        else:
            mutant_ids = [f"mutant_{j + 1}" for j in range(np.sum(keep_mask))]

    for tool in tool_order:
        profiles = profiles_by_tool.get(tool, [])
        if not profiles:
            continue

        # Stack into matrix (#inputs × #mutants)
        mat = np.vstack(profiles)

        # Apply mask
        mat = mat[:, keep_mask]

        # DataFrame with real mutant IDs
        df = pd.DataFrame(
            mat,
            index=[f"input_{i+1}" for i in range(len(profiles))],
            columns=mutant_ids
        )

        # Export as Excel with formatting
        out_path = os.path.join(out_dir, f"{tool}_mutant_kills.xlsx")

        with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="MutantKills")

            # Apply formatting
            workbook  = writer.book
            worksheet = writer.sheets["MutantKills"]

            green_fmt = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
            white_fmt = workbook.add_format({"bg_color": "#FFFFFF"})

            # Apply formatting cell by cell
            for row in range(1, df.shape[0] + 1):  # +1 offset for header
                for col in range(1, df.shape[1] + 1):  # +1 offset for index col
                    val = df.iloc[row-1, col-1]
                    fmt = green_fmt if val else white_fmt
                    worksheet.write(row, col, str(val), fmt)

        print(f"[INFO] Exported Excel with formatting for {tool}: {out_path}")

# ---------------------------
# Loading all tools' profiles from each run folder
# ---------------------------
import os
import re


def _load_profiles_from_run(run_dir: str):
    """
    Load all mutation profiles from a single run folder.
    Example structure:
        mutants_profile_run_1/
            fan_con_1.txt
            isla_con_1.txt
            fan_no_con_1.txt

    Returns:
        profiles_by_tool: dict[str, list[np.ndarray]]
        tool_order: list[str]
        M: int (#mutants per profile)
    """
    files = sorted([f for f in os.listdir(run_dir) if f.endswith(".txt")])
    if not files:
        raise RuntimeError(f"No .txt files found in {run_dir}")

    profiles_by_tool = {}
    M_expected = None

    for fname in files:
        # Extract tool name from filename, e.g., fan_con_1.txt → fan_con
        tool = re.split(r'[_\-][0-9]+\.txt$', fname)[0]  # remove trailing _<num>.txt
        path = os.path.join(run_dir, fname)

        try:
            arr = np.loadtxt(path)
        except Exception:
            print(f"[WARN] Could not parse {fname}")
            continue

        if arr.ndim > 1:
            arr = arr.flatten()
        if M_expected is None:
            M_expected = arr.size
        if arr.size != M_expected:
            print(f"[WARN] {fname} has inconsistent size ({arr.size} vs {M_expected})")
            continue

        profiles_by_tool.setdefault(tool, []).append(arr.astype(bool))

    # Sorted alphabetically (case-insensitive)
    tool_order = sorted(profiles_by_tool.keys())
    if not profiles_by_tool:
        raise RuntimeError(f"No valid profiles found in {run_dir}")

    return profiles_by_tool, tool_order, M_expected


# -----------------------------------
# 2) Global selection (fair for all)
#    - drop never/always
#    - keep band [min_rate, max_rate]
#    - dedup identical columns
#    - subsumption (optional)
# -----------------------------------

def _build_global_matrix(profiles_by_tool: dict[str, list[np.ndarray]]):
    """Stack ALL tests from ALL tools -> (T x M) boolean matrix."""
    mats = [np.vstack(vecs).astype(bool) for vecs in profiles_by_tool.values()]
    return np.vstack(mats)  # (T x M)

def _dedup_columns_global(global_mat: np.ndarray, keep_mask: np.ndarray) -> np.ndarray:
    """Remove equivalent mutants globally (identical columns across all tests)."""
    idx = np.flatnonzero(keep_mask)
    if idx.size <= 1:
        return keep_mask.copy()
    X = global_mat[:, idx]
    packed = np.packbits(X, axis=0)
    keys = [packed[:, j].tobytes() for j in range(packed.shape[1])]
    _, unique_idx = np.unique(keys, return_index=True)
    keep_local = np.zeros(X.shape[1], dtype=bool)
    keep_local[unique_idx] = True
    out = np.zeros_like(keep_mask, dtype=bool)
    out[idx[keep_local]] = True
    return out

def _subsumption_reduce_global(global_mat: np.ndarray, keep_mask: np.ndarray) -> np.ndarray:
    """
    Remove subsumed mutants globally: drop column j if kills(j) ⊆ kills(i) for some i≠j.
    O(M^2 * T), fine for M~300.
    """
    idx = np.flatnonzero(keep_mask)
    if idx.size <= 1:
        return keep_mask.copy()
    X = global_mat[:, idx]
    keep = np.ones(X.shape[1], dtype=bool)
    for i in range(X.shape[1]):
        if not keep[i]:
            continue
        vi = X[:, i]
        for j in range(X.shape[1]):
            if i == j or not keep[j]:
                continue
            vj = X[:, j]
            if np.all((~vj) | vi):  # if vj ⊆ vi
                keep[j] = False
    out = np.zeros_like(keep_mask, dtype=bool)
    out[idx[keep]] = True
    return out

def select_mutants_global(global_mat: np.ndarray,
                          min_rate: float,
                          max_rate: float,
                          drop_never: bool,
                          drop_always: bool,
                          dedup: bool,
                          subsumption: bool):
    """
    Build the global KEEP mask shared by all tools.

    Parameters
    ----------
    global_mat : np.ndarray (T x M)
        Binary matrix (T = #test inputs, M = #mutants)
        Each cell = 1 if test kills mutant, else 0.

    min_rate, max_rate : float
        Define acceptable range for kill-rate-based filtering.
        Mutants outside this range are dropped.

    drop_never : bool
        If True → drop mutants never killed (equivalent mutants).

    drop_always : bool
        If True → drop mutants always killed (trivial mutants).

    dedup : bool
        If True → remove mutants with identical kill patterns (redundant).

    subsumption : bool
        If True → remove mutants that are weaker (subsumed) by others.

    Returns
    -------
    keep : np.ndarray(bool, M)
        Boolean mask indicating which mutants to keep.

    after_band : int
        Number of mutants remaining after kill-rate filtering.

    ---------------------------------------------------------------------
     Example
    ----------
    Suppose we have:
        global_mat =
            [[1, 0, 1, 1, 0],
             [1, 0, 1, 1, 0],
             [0, 0, 1, 1, 0]]

        → 3 tests × 5 mutants

        Kill rates (mean across rows):
            M1 = 0.67
            M2 = 0.00   ← equivalent (never killed)
            M3 = 1.00   ← trivial (always killed)
            M4 = 1.00   ← trivial (always killed)
            M5 = 0.00   ← equivalent (never killed)

        If:
            min_rate = 0.0
            max_rate = 0.5
            drop_never = True
            drop_always = True
        → Only mutants with kill rate 0.0 < rate < 1.0 will remain.

        After this step, mutants M2, M3, M4, M5 are dropped
        because they are either always or never killed.
    ---------------------------------------------------------------------
    """

    #  Compute the kill rate of each mutant (column-wise)
    #    e.g., [0.67, 0.0, 1.0, 1.0, 0.0]
    rates = global_mat.mean(axis=0)

    #  Basic band filter: keep mutants whose kill rates fall between thresholds
    #    This removes mutants that are "too easy" or "too hard" by default range.
    keep = (rates >= min_rate) & (rates <= max_rate)

    #  Explicitly remove "never killed" mutants (kill rate == 0)
    #    These are equivalent mutants — tests never differentiate them.
    if drop_never:
        keep &= (rates > 0.0)

    #  Explicitly remove "always killed" mutants (kill rate == 1)
    #    These are trivial mutants — any test can kill them, so they add no value.
    if drop_always:
        keep &= (rates < 1.0)

    #  Count how many mutants survive after the above filters


    #  Optionally remove redundant mutants
    #     (compares column patterns — keeps one per group)
    if dedup:
        keep = _dedup_columns_global(global_mat, keep)

    #  Optionally remove subsumed mutants
    #     (A subsumes B if every test that kills A also kills B)
    if subsumption:
        keep = _subsumption_reduce_global(global_mat, keep)

    after_band = int(keep.sum())
    #  Return boolean mask + count for diagnostics
    return keep, after_band



# -----------------------------------------------------
# Per-tool metrics on the selected global set S
#    - KI: count of inputs with >= ki_threshold kills
#    - SKI: mean kills among those inputs (average)
#    - optional KI_at_τ / SKI_mean_at_τ for τ in extra_taus
# -----------------------------------------------------
# We skip  test profiles ( all-1) during metric computation.
# These inputs can create MS score 1 for all generator so we can not compare
# We keep them in data but exclude them from MS/KI/SKI calculations for fairness across tools.

def _metrics_for_tool(X_tool: np.ndarray,
                      selected_mask: np.ndarray,
                      ki_threshold: int = 1,
                      skip_all_ones: bool = True) -> dict:
    """
    Compute mutation metrics (MS, KI, SKI) for one tool on globally filtered mutants.

    Parameters
    ----------
    X_tool : np.ndarray
        Binary (N x M) kill matrix for this tool.
    selected_mask : np.ndarray(bool, M)
        Global keep mask for mutants.
    ki_threshold : int
        Minimum kills per test for KI calculation.
    skip_all_ones : bool
        If True, remove tests that kill all mutants (trivial cases).
    """
    # # --- 🔹 First let us remove tests that kill ALL mutants (super-tests) ---
    # # if we dont remove these test , we would be not able to comapre the generators
    # if X_tool.shape[1] > 0:
    #     before = X_tool.shape[0]
    #     X_tool = X_tool[~(X_tool.sum(axis=1) == X_tool.shape[1])]
    #     removed = before - X_tool.shape[0]
    #     if removed > 0:
    #         print(f"[INFO] Removed {removed}/{before} trivial tests (kill-all mutants).")

    Xs = X_tool[:, selected_mask].astype(bool)
    N, Msel = Xs.shape

    # Optional filtering of trivial "all-1" profiles ---
    """
    Xs =
        [[1, 0, 1, 0],
         [1, 1, 1, 1],
         [0, 0, 0, 0],
         [1, 1, 0, 1]]
         
         here we remove  [1, 1, 1, 1], cause for this the MS would be 1.0 and we can not comapre the tools
    
    """
    if skip_all_ones:
        Xs = Xs[~(Xs.sum(axis=1) == Msel)]
        N = Xs.shape[0]

    if N == 0:
        return {
            "MS": 0.0, "KI": 0, "KI_rate": 0.0,
            "SKI": 0.0, "SKI_mean": 0.0, "SKI_rate": 0.0,
            "tests": 0, "mutants_selected": int(Msel),
            "ki_threshold": int(ki_threshold)
        }

    # --- MS: fraction of selected mutants killed by any test ---
    MS = float(Xs.any(axis=0).sum()) / max(1, Msel)

    # --- Kills per test ---
    kills_per_test = Xs.sum(axis=1)

    # --- KI: number of tests that kill ≥ threshold mutants ---
    mask_ki = (kills_per_test >= ki_threshold)
    KI = int(mask_ki.sum())
    KI_rate = KI / max(1, N)

    # --- SKI: average kills among those KI tests ---
    SKI_mean = float(kills_per_test[mask_ki].mean()) if KI > 0 else 0.0
    SKI_rate = SKI_mean / max(1, Msel)

    return {
        "MS": round(MS, 6),
        "KI": KI,
        "KI_rate": round(KI_rate, 6),
        "SKI": round(SKI_mean, 6),
        "SKI_mean": round(SKI_mean, 6),
        "SKI_rate": round(SKI_rate, 6),
        "tests": int(N),
        "mutants_selected": int(Msel),
        "ki_threshold": int(ki_threshold)
    }

