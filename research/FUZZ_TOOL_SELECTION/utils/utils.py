import os
import re
import numpy as np
import pandas as pd

from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

try:
    from scipy.stats import spearmanr as _scipy_spearmanr, ConstantInputWarning
except Exception:
    _scipy_spearmanr = None
    ConstantInputWarning = None
import warnings


def _cluster_quality(X, labels):
    """Return Silhouette (higher=better), DB (lower=better), CH (higher=better).
       If labels are degenerate (all same), return Nones."""
    labs = np.asarray(labels)
    if np.unique(labs).size < 2 or np.unique(labs).size >= len(labs):
        return None, None, None
    try:
        sil = float(silhouette_score(X, labs, metric="euclidean"))
    except Exception:
        sil = None
    try:
        db  = float(davies_bouldin_score(X, labs))
    except Exception:
        db = None
    try:
        ch  = float(calinski_harabasz_score(X, labs))
    except Exception:
        ch = None
    return sil, db, ch

def _natural_key(s: str):
    """Natural sort key: splits digits and text so '10' > '2'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def _read_profile_file(path: str):
    """
    Read a single kill profile: whitespace-separated 0/1 tokens.
    Returns a boolean numpy array (shape (M,)) or None if unparsable.
    """
    try:
        tokens = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                tokens.extend(line.strip().split())
        bits = []
        for t in tokens:
            if t in ("0", "1"):
                bits.append(1 if t == "1" else 0)
        if not bits:
            return None
        return np.array(bits, dtype=bool)
    except Exception:
        return None


def _union_bool(vecs):
    """Elementwise OR over a list of boolean vectors."""
    u = vecs[0].copy()
    for v in vecs[1:]:
        np.logical_or(u, v, out=u)
    return u


def _l2_normalize(X):
    X = np.asarray(X, dtype=float)
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    return X / norms


# --- add these small helpers near the top ---

def _read_generator_order(path: str) -> list[str]:
    """Read one generator name per line; ignore blanks/comments."""
    order = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if not name or name.startswith("#"):
                continue
            order.append(name)
    return order

def _write_generator_order(path: str, tools: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in tools:
            f.write(t + "\n")

def _row_for(mutation_metrics, g):
    """Return a plain dict for generator g from a dict-of-dicts or a DataFrame."""
    if isinstance(mutation_metrics, pd.DataFrame):
        if "Tools" in mutation_metrics.columns:
            mdf = mutation_metrics.set_index("Tools")
        else:
            mdf = mutation_metrics
        return mdf.loc[g].to_dict()
    else:
        return dict(mutation_metrics[g])

def _get_metric(mutation_metrics, g, primary, *fallbacks):
    row = _row_for(mutation_metrics, g)
    if primary in row:
        return row[primary]
    for k in fallbacks:
        if k in row:
            return row[k]
    raise KeyError(f"{primary} not found for {g}. Available: {list(row.keys())}")

def quality_vs_correlation_summary(results, corr_df, quality_key="Silhouette",
                                   corr_cols=("Coverage–MS","Coverage–KI","Coverage–SKI"),
                                   decimals=4):
    # collect quality values aligned with rows (exclude the 'Average over configs' row)
    mask = corr_df["Configuration"] != "Average over configs"
    qvals = []
    for cfg in corr_df.loc[mask, "Configuration"]:
        # find matching result row
        emb, algo, k = [p.strip() for p in cfg.split("+")]
        k = int(k)
        r = next((x for x in results
                  if x["Embedding Model"]==emb and x["Cluster Algo"]==algo and int(x["K"])==k), None)
        qvals.append(None if r is None else r.get(quality_key, None))

    q = pd.Series(qvals, index=corr_df.index[mask]).astype("float64")
    out = []
    for col in corr_cols:
        y = pd.to_numeric(corr_df.loc[mask, col], errors="coerce")
        # Spearman between q and y:
        rho = _spearman_safe(q.to_numpy(), y.to_numpy())
        out.append({"Quality": quality_key, "Metric": col, "Spearman": round(float(rho), decimals)})
    return pd.DataFrame(out)

def _spearman_basic(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    if x.size != y.size or x.size == 0:
        return float("nan")
    rx = pd.Series(x).rank(method="average").to_numpy()
    ry = pd.Series(y).rank(method="average").to_numpy()
    if np.all(rx == rx[0]) or np.all(ry == ry[0]):
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])

def _spearman_safe(x, y) -> float:
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    if x.size != y.size or x.size == 0:
        return float("nan")
    # constant vectors -> undefined correlation
    if np.nanstd(x) == 0.0 or np.nanstd(y) == 0.0:
        return float("nan")

    if _scipy_spearmanr is not None:
        # (Optional) also silence any edge-case warnings just in case
        if ConstantInputWarning is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=ConstantInputWarning)
                r, _ = _scipy_spearmanr(x, y)
        else:
            r, _ = _scipy_spearmanr(x, y)
        return float(r)

    # fallback
    return _spearman_basic(x, y)



def infer_generator_order_from_inputs(base_input_dir: str) -> list:
    """
    Automatically infer generator order based on renamed test input files
    inside the first run folder.

    Example file names:
        fandango_con_1.txt
        isla_no_con_2.txt
        openai_gram_3.txt
    Returns:
        A unique, ordered list of generator identifiers.
    """

    print(f"[INFO] Inferring generator order from: {base_input_dir}")

    #  Locate the first run folder (e.g., input_pool_by_run_1)
    run_folders = sorted(
        [f for f in os.listdir(base_input_dir) if f.startswith("input_pool_by_run_")]
    )
    if not run_folders:
        print("[WARN] No run folders found in base input directory.")
        return []

    first_run_dir = os.path.join(base_input_dir, run_folders[0])
    print(f"[DEBUG] Using run folder: {first_run_dir}")

    # Collect all .txt input files
    all_files = [
        f for f in os.listdir(first_run_dir)
        if f.endswith(".txt") and os.path.isfile(os.path.join(first_run_dir, f))
    ]

    if not all_files:
        print(f"[WARN] No .txt files found inside {first_run_dir}.")
        return []

    # Extract generator prefixes before the final underscore-number pattern
    prefix_pattern = re.compile(r"^(.*)_[0-9]+\.txt$")
    prefixes = []
    for fname in all_files:
        m = prefix_pattern.match(fname)
        if m:
            prefixes.append(m.group(1))

    #  Preserve original appearance order
    seen = set()
    ordered_prefixes = [p for p in prefixes if not (p in seen or seen.add(p))]
    # Sorted alphabetically (case-insensitive) — stable across machines
    ordered_prefixes = sorted(ordered_prefixes, key=lambda x: x.lower())

    print(f"[INFO] Inferred (sorted) generator order: {ordered_prefixes}")
    return ordered_prefixes


