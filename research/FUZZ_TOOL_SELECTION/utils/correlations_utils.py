
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from FUZZ_TOOL_SELECTION.utils.utils import _get_metric

try:
    from scipy.stats import spearmanr as _scipy_spearmanr, ConstantInputWarning
except Exception:
    _scipy_spearmanr = None
    ConstantInputWarning = None


# ----------------------------- Spearman helpers -----------------------------

def _spearman_manual(x: np.ndarray, y: np.ndarray) -> float:
    """
    Manual Spearman: rank both vectors then Pearson on the ranks.
    Returns NaN for empty or mismatched lengths or constant ranks.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or x.size != y.size:
        return float("nan")

    rx = pd.Series(x).rank(method="average").to_numpy()
    ry = pd.Series(y).rank(method="average").to_numpy()

    if np.all(rx == rx[0]) or np.all(ry == ry[0]):
        return float("nan")

    return float(np.corrcoef(rx, ry)[0, 1])


def spearman_safe(x, y) -> float:
    """
    Safe Spearman wrapper:
    - returns NaN on empty/mismatched lengths or constant vectors
    - uses SciPy if available (warnings silenced), else falls back to manual.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if x.size == 0 or x.size != y.size:
        return float("nan")

    # Treat constant (incl. all-equal with NaN-tolerant std) as undefined
    if np.nanstd(x) == 0.0 or np.nanstd(y) == 0.0:
        return float("nan")

    if _scipy_spearmanr is not None:
        if ConstantInputWarning is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=ConstantInputWarning)
                r, _ = _scipy_spearmanr(x, y)
        else:
            r, _ = _scipy_spearmanr(x, y)
        return float(r)

    return _spearman_manual(x, y)


def format_correlation(val, nan_fallback=0.0):
    """
    Replace None/NaN with the chosen fallback (number or string).
    """
    if val is None:
        return nan_fallback
    try:
        if np.isnan(val):
            return nan_fallback
    except Exception:
        pass
    return val


# ----------------------------- Table builders ------------------------------

def build_cluster_coverage_table(
    cluster_runs: List[dict],
    tools: List[str]
) -> pd.DataFrame:
    """
    Flatten clustering results into a table with fixed tool (generator) order.

    cluster_runs item schema:
      {
        "Embedding Model": str,
        "Cluster Algo"  : str,
        "K"             : Optional[int],   # None for non-K algos
        "K_eff"         : int,             # effective number of clusters
        "Scores"        : {tool: coverage_value, ...},
        "Winner"        : str              # unused here
      }

    Returns DataFrame with columns:
      ["Configuration", "K_eff", <tool1>, <tool2>, ...]
    where Configuration := "<Embedding Model> + <Cluster Algo> + <K>"
    """
    rows = []
    for run in cluster_runs:
        cfg = f"{run['Embedding Model']} + {run['Cluster Algo']} + {run['K']}"
        row = {
            "Configuration": cfg,
            "K_eff": int(run.get("K_eff", run.get("K", 0))),
        }
        for tool in tools:
            row[tool] = float(run["Scores"].get(tool, 0.0))
        rows.append(row)
    return pd.DataFrame(rows)


def build_mutation_metrics_table(
    mutation_metrics: Dict[str, dict],
    tools: List[str],
    use_rates: bool = True
) -> pd.DataFrame:
    """
    Normalize mutation metrics to a fixed tool order.

    mutation_metrics: dict[tool] -> {
        "MS": float,
        "KI": int, "KI_rate": float, (alt spellings tolerated)
        "SKI": float, "SKI_rate": float, ...
    }

    Returns DataFrame with columns: ["Tools", "MS", "KI", "SKI"].
    If use_rates=True, KI/SKI are taken from rate fields when available.
    """
    rows = []
    for tool in tools:
        if tool not in mutation_metrics:
            raise KeyError(
                f"Tool {tool!r} missing from mutation_metrics keys: "
                f"{sorted(mutation_metrics.keys())}"
            )
        mm = mutation_metrics[tool]
        if use_rates:
            rows.append({
                "Tools": tool,
                "MS": float(mm["MS"]),
                # tolerant keys for KI-rate (supports historical variants)
                "KI": float(mm.get("KI_rate", mm.get("KI", 0.0))),
                "SKI": float(mm.get("SKI_rate", mm.get("SKI", 0.0))),
            })
        else:
            rows.append({
                "Tools": tool,
                "MS": float(mm["MS"]),
                "KI": float(mm["KI"]),
                "SKI": float(mm["SKI"]),
            })
    return pd.DataFrame(rows)


def build_correlations_table(
    cluster_runs: List[dict],
    mutation_metrics: Dict[str, dict],
    tools: List[str],
    *,
    nan_fallback: float = 0.0,
    decimals: int = 4
) -> pd.DataFrame:
    """
    Compute Spearman correlation between cluster coverage scores and mutation scores (MS)
    across all generator tools, for each clustering configuration.

    Parameters:
        cluster_runs: List of dicts, each representing a clustering configuration and its coverage scores.
        mutation_metrics: Dict of per-tool metrics (must include MS).
        tools: Ordered list of tool/generator names.
        nan_fallback: Value to use when correlation cannot be computed (default = 0.0).
        decimals: Number of decimal places to round correlation values.

    Returns:
        pd.DataFrame with columns:
            ["Configuration", "Coverage–MS"]
    """

    # === Step 1: Prepare MS vector in fixed tool order ===
    MS_vec = np.array(
        [_get_metric(mutation_metrics, t, "MS") for t in tools],
        dtype=float
    )

    rows = []

    # === Step 2: Compute correlation per configuration ===
    for run in cluster_runs:
        # e.g., "OpenAI + K-Means + 20" or "Qwen3 + Affinity"
        cfg_parts = [run.get('Embedding Model'), run.get('Cluster Algo')]
        if 'K' in run and run['K'] is not None:
            cfg_parts.append(str(run['K']))
        cfg = " + ".join(filter(None, cfg_parts))

        # Coverage scores for each generator tool
        cov_vec = np.array([run["Scores"].get(t, 0.0) for t in tools], dtype=float)

        # Compute Spearman correlation
        r_ms = format_correlation(spearman_safe(cov_vec, MS_vec), nan_fallback)

        rows.append({
            "Configuration": cfg,
            "Coverage–MS": round(float(r_ms), decimals)
        })

    # === Step 3: Build DataFrame and return ===
    df = pd.DataFrame(rows)
    return df




# ----------------------------- Optional helper -----------------------------

def results_from_coverage_df(df: pd.DataFrame, tools: List[str]) -> List[dict]:
    """
    Rebuild `cluster_runs` from a saved coverage table.

    Expected columns: ["Configuration", "K_eff", <tool1>, <tool2>, ...]
    Accepts Configuration formatted as "Model + Algo + K" (spaces optional).
    """
    rebuilt: List[dict] = []
    for _, row in df.iterrows():
        cfg = str(row["Configuration"]).strip()
        # tolerate varying spaces around '+'
        parts = [p.strip() for p in cfg.split("+")]
        if len(parts) == 3:
            emb_model, algo, k_str = parts
            try:
                k_val: Optional[int] = int(k_str)
            except Exception:
                k_val = None
        else:
            emb_model, algo, k_val = cfg, "", None

        scores = {t: float(row[t]) for t in tools if t in row.index}
        rebuilt.append({
            "Embedding Model": emb_model,
            "Cluster Algo": algo,
            "K": k_val,
            "K_eff": int(row.get("K_eff", k_val or 0)),
            "Scores": scores,
            "Winner": ""
        })
    return rebuilt
