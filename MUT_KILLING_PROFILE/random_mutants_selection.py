# mutant_selector.py
from __future__ import annotations
import os
import random
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# ---------------------------- Data structures ----------------------------

@dataclass(frozen=True)
class SelectedMutant:
    class_key: str
    src_path: Path
    dst_path: Optional[Path]  # None if copy=False


# ---------------------------- Key extraction ----------------------------

def default_class_key_extractor(name: str) -> str:
    """
    Heuristics to infer a class key from a mutant folder name.
    Order:
      1) Split by '__' and take the first token (e.g., Foo__COND__42 -> 'Foo')
      2) If dotted path exists, return dotted token (org.example.Foo...)
      3) Fallback: full name
    """
    if "__" in name:
        return name.split("__", 1)[0]
    if "." in name:
        # keep package.Class form if present
        tokens = re.split(r"[^A-Za-z0-9_.]+", name)
        return tokens[0] if tokens and tokens[0] else name
    return name


def make_regex_key_extractor(pattern: str) -> Callable[[str], str]:
    """
    Create an extractor from a regex with a named group 'class'.
    Example: r'(?P<class>[^_]+)__.+'  -> captures 'Foo' from 'Foo__COND__42'
    """
    rx = re.compile(pattern)
    def extract(name: str) -> str:
        m = rx.search(name)
        if not m or "class" not in m.groupdict():
            raise ValueError(
                f"Pattern didn't match or has no named group 'class'. "
                f"pattern={pattern!r}, name={name!r}"
            )
        return m.group("class")
    return extract


# ---------------------------- Allocation strategies ----------------------------

def _equal_allocation(sizes: Dict[str, int], budget: int) -> Dict[str, int]:
    """
    Equal per-class allocation with caps, remainder distribution, and top-up correction.
    Ensures total == budget if possible.
    """
    C = len(sizes)
    if C == 0 or budget <= 0:
        return {k: 0 for k in sizes}

    base = budget // C
    rem = budget % C
    alloc = {k: min(base, sizes[k]) for k in sizes}

    # Step 1: distribute remainder to classes with most remaining capacity
    for k in sorted(sizes.keys(), key=lambda kk: sizes[kk] - alloc[kk], reverse=True):
        if rem == 0:
            break
        if alloc[k] < sizes[k]:
            alloc[k] += 1
            rem -= 1

    # Step 2: final top-up if total < budget and capacity remains
    total = sum(alloc.values())
    if total < budget:
        remaining = budget - total
        # Assign leftover slots to classes with remaining mutants (descending by capacity)
        for k in sorted(sizes.keys(), key=lambda kk: sizes[kk] - alloc[kk], reverse=True):
            if remaining == 0:
                break
            extra = min(sizes[k] - alloc[k], remaining)
            alloc[k] += extra
            remaining -= extra

    # Final sanity: clamp totals
    total = sum(alloc.values())
    if total > budget:
        # reduce proportionally from largest allocations if overshoot occurs
        over = total - budget
        for k in sorted(alloc.keys(), key=lambda kk: alloc[kk], reverse=True):
            if over == 0:
                break
            reduce_by = min(over, alloc[k] - 1)
            alloc[k] -= reduce_by
            over -= reduce_by

    return alloc


def _proportional_allocation(sizes: Dict[str, int], total_budget: int, min_per_class: int = 1) -> Dict[str, int]:
    """
    Allocate proportional to mutant availability (sizes), but ensure:
      - At least `min_per_class` mutants per class
      - Never exceed total_budget
      - Redistribute leftover slots to reach total_budget if possible
    """
    total_size = sum(sizes.values())
    if total_size == 0 or total_budget <= 0:
        return {k: 0 for k in sizes}

    # Step 1: initial proportional allocation (respect class caps)
    alloc = {}
    for k, v in sizes.items():
        prop = int(round(total_budget * (v / total_size)))
        alloc[k] = min(max(prop, min_per_class), v)

    # Step 2: fix total underflow (sum < total_budget)
    total = sum(alloc.values())
    if total < total_budget:
        remaining = total_budget - total
        for k in sorted(sizes.keys(), key=lambda kk: sizes[kk] - alloc[kk], reverse=True):
            if remaining == 0:
                break
            extra = min(sizes[k] - alloc[k], remaining)
            alloc[k] += extra
            remaining -= extra

    # Step 3: fix overflow (sum > total_budget)
    total = sum(alloc.values())
    if total > total_budget:
        over = total - total_budget
        for k in sorted(alloc.keys(), key=lambda kk: alloc[kk], reverse=True):
            if over == 0:
                break
            reduce_by = min(over, alloc[k] - min_per_class)
            alloc[k] -= reduce_by
            over -= reduce_by

    return alloc



# ---------------------------- Core API ----------------------------

def select_mutants(
    src: str | Path,
    dst: str | Path,
    *,
    budget: int = 300,
    allocation: str = "proportional",   # "proportional" | "equal"
    seed: int = 42,
    copy: bool = True,
    overwrite: bool = False,
    class_key_extractor: Optional[Callable[[str], str]] = None,
    class_pattern: Optional[str] = None,
    min_per_class: int = 1,
) -> Tuple[Dict[str, int], List[SelectedMutant]]:
    """
    Select mutant folders stratified by class and (optionally) copy them.
    Works for nested Java packages (e.g., org.mozilla.javascript.ast.AstNode).
    """

    src_root = Path(src)
    if not src_root.exists():
        raise FileNotFoundError(f"Source root not found: {src_root}")

    # --- helper: extract class name from .class file ---
    def infer_class_key_from_folder(folder: Path) -> str:
        class_files = list(folder.glob("*.class"))
        if class_files:
            name = class_files[0].stem  # e.g., org.mozilla.javascript.ast.AstNode
            return name.split(".")[-1]  # or return full path if you prefer
        return "UnknownClass"

    # decide extractor
    if class_key_extractor is None:
        if class_pattern:
            class_key_extractor = make_regex_key_extractor(class_pattern)
        else:
            class_key_extractor = infer_class_key_from_folder  # our improved version

    # gather mutant folders
    mutant_folders = [p for p in src_root.iterdir() if p.is_dir()]
    if not mutant_folders:
        return {}, []

    # group by inferred class key
    groups: Dict[str, List[Path]] = defaultdict(list)
    for mf in mutant_folders:
        key = class_key_extractor(mf)
        groups[key].append(mf)

    sizes = {k: len(v) for k, v in groups.items()}

    # compute allocation
    if allocation == "proportional":
        alloc = _proportional_allocation(sizes, budget, min_per_class=min_per_class)
    elif allocation == "equal":
        alloc = _equal_allocation(sizes, budget)
    else:
        raise ValueError("allocation must be 'proportional' or 'equal'")

    # random sampling
    rng = random.Random(seed)
    selected: List[SelectedMutant] = []
    per_class_counts: Dict[str, int] = {}

    for cls, folders in groups.items():
        k = min(alloc.get(cls, 0), len(folders))
        picks = rng.sample(folders, k) if k > 0 else []
        per_class_counts[cls] = len(picks)
        for mf in picks:
            selected.append(SelectedMutant(class_key=cls, src_path=mf, dst_path=None))

    # copy if requested
    dst_root = Path(dst)
    if copy:
        if dst_root.exists():
            if overwrite:
                shutil.rmtree(dst_root)
            else:
                if any(dst_root.iterdir()):
                    raise FileExistsError(
                        f"Destination '{dst_root}' exists and is not empty. "
                        f"Pass overwrite=True to replace it."
                    )
        dst_root.mkdir(parents=True, exist_ok=True)

        used_names = set()
        updated: List[SelectedMutant] = []
        for item in selected:
            name = item.src_path.name
            target = dst_root / name
            if target.name in used_names or target.exists():
                i = 2
                while (dst_root / f"{name}__{i}").exists() or f"{name}__{i}" in used_names:
                    i += 1
                target = dst_root / f"{name}__{i}"
            shutil.copytree(item.src_path, target)
            used_names.add(target.name)
            updated.append(SelectedMutant(item.class_key, item.src_path, target))
        selected = updated

    return per_class_counts, selected



def preview_selection(
    src: str | Path,
    *,
    budget: int = 300,
    allocation: str = "proportional",
    seed: int = 42,
    class_key_extractor: Optional[Callable[[str], str]] = None,
    class_pattern: Optional[str] = None,
    min_per_class: int = 1,
) -> Dict[str, int]:
    """
    Dry-run: compute the per-class counts that *would* be selected (no copying).
    """
    counts, _ = select_mutants(
        src=src,
        dst=Path("/dev/null"),  # ignored when copy=False
        budget=budget,
        allocation=allocation,
        seed=seed,
        copy=False,
        overwrite=False,
        class_key_extractor=class_key_extractor,
        class_pattern=class_pattern,
        min_per_class=min_per_class,
    )
    return counts





