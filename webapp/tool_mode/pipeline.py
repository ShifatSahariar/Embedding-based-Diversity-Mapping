"""Full SpreadEx tool-mode pipeline after user confirmation."""

import json
import os
import zipfile
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.cluster import KMeans

from .generators import generate_inputs_for_tool_mode
from .runner import run_sut_command
from .config import GENERATOR_MAP, RUNS_ROOT
from .security import ensure_inside_root
from .storage import RunState, safe_mkdir, write_run_json


def execute_run(
    state: RunState,
    openai_api_key: str | None,
    codestral_api_key: str | None,
    set_step: Callable[[str], None],
    log: Callable[[str], None],
) -> None:
    run_id = state.run_id
    run_root = RUNS_ROOT / run_id
    generated_dir = run_root / "generated_inputs"
    output_dir = run_root / "outputs"
    safe_mkdir(generated_dir)
    safe_mkdir(output_dir)

    env_backup = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY"),
    }
    try:
        state.status = "running"
        set_step("step1_manifest_validation")
        log("Run started.")
        log("Step 1/5: Project manifest and command confirmation accepted.")

        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        if codestral_api_key:
            os.environ["MISTRAL_API_KEY"] = codestral_api_key

        _run_smoke_test(state, set_step, log)
        _run_generation(state, generated_dir, set_step, log)
        grouped = read_txt_inputs(generated_dir)
        if not grouped:
            raise RuntimeError("No generated inputs found. Check grammar/setup for selected generators.")
        log(f"Generated inputs for {len(grouped)} generator group(s).")

        gen_mode = state.config.get("generator_selection_mode", "cc")

        if gen_mode == "single":
            winner = state.config["generators"][0]
            cc_scores = {winner: 1.0}
            state.outputs["selected_generator"] = winner
            state.outputs["cc_scores"] = cc_scores
            log(f"Single generator mode — using: {winner}")
            all_names, all_texts, owners = _flatten_grouped_inputs(grouped)
            embeddings = _load_embeddings(all_texts, state.config["provider"], openai_api_key)
        else:
            set_step("step4_model_embeddings_and_cc")
            log("Step 4/5: Creating embeddings and running CC-based generator selection...")
            all_names, all_texts, owners = _flatten_grouped_inputs(grouped)
            embeddings = _load_embeddings(all_texts, state.config["provider"], openai_api_key)
            np.save(output_dir / "all_embeddings.npy", embeddings)
            winner, cc_scores = cluster_coverage_select(embeddings, owners)
            state.outputs["selected_generator"] = winner
            state.outputs["cc_scores"] = cc_scores
            log(f"Selected generator via CC: {winner}")

        set_step("step5_prioritization_and_export")
        log("Step 5/5: Prioritizing inputs and exporting ZIP...")
        _export_prioritized_inputs(state, output_dir, embeddings, all_names, all_texts, owners, winner, cc_scores)
        state.status = "completed"
        set_step("completed")
        log("Run completed successfully.")
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        log(f"Run failed: {type(exc).__name__}: {exc}")
    finally:
        _restore_env(env_backup)


def _run_smoke_test(state: RunState, set_step: Callable[[str], None], log: Callable[[str], None]) -> None:
    """Gate the full pipeline so invalid SUT commands fail early and clearly."""
    run_root = RUNS_ROOT / state.run_id
    smoke_dir = run_root / "smoke_inputs"
    safe_mkdir(smoke_dir)
    set_step("step2_smoke_test")
    log("Step 2/5: Running smoke generation and SUT execution check...")
    smoke_generator = state.config["generators"][0]
    generate_inputs_for_tool_mode(state.run_id, state.config["subject"], smoke_generator, 3, smoke_dir)
    smoke_files = sorted(smoke_dir.glob("*.txt"))[:3]
    if not smoke_files:
        raise RuntimeError("Smoke generation produced no inputs.")

    working_directory = Path(state.config["working_directory"]).resolve(strict=True)
    approved_root = Path(state.config["approved_project_root"]).resolve(strict=True)
    ensure_inside_root(working_directory, approved_root)
    smoke_results = [
        {
            "input": smoke_file.name,
            **run_sut_command(
                state.config["run_command_template"],
                smoke_file,
                working_directory,
                state.config["input_execution_mode"],
            ),
        }
        for smoke_file in smoke_files
    ]
    state.outputs["smoke_test"] = smoke_results
    write_run_json(state.run_id, "smoke_test_report.json", {"results": smoke_results})
    if not any(item["ok"] for item in smoke_results):
        raise RuntimeError("Smoke test failed: SUT command did not produce a successful non-usage output.")
    log("Smoke test passed with at least one valid SUT execution.")


def _run_generation(state: RunState, generated_dir: Path, set_step: Callable[[str], None], log: Callable[[str], None]) -> None:
    set_step("step3_generator_execution")
    log("Step 3/5: Generating candidate inputs from selected generators...")
    for gen in state.config["generators"]:
        log(f"Generating {gen}...")
        generate_inputs_for_tool_mode(
            state.run_id,
            state.config["subject"],
            gen,
            int(state.config["num_inputs_per_generator"]),
            generated_dir,
        )


def read_txt_inputs(folder: Path) -> dict[str, list[tuple[str, str]]]:
    by_generator: dict[str, list[tuple[str, str]]] = {}
    for file_path in sorted(folder.glob("*.txt")):
        gen = next((candidate for candidate in GENERATOR_MAP if file_path.stem.startswith(f"{candidate}_")), None)
        if gen is None:
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        by_generator.setdefault(gen, []).append((file_path.name, content))
    return by_generator


def cluster_coverage_select(embeddings: np.ndarray, owners: list[str]) -> tuple[str, dict[str, float]]:
    n = len(embeddings)
    if n == 0:
        raise RuntimeError("No embeddings available for CC selection.")
    k = max(2, min(10, int(np.sqrt(n))))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)
    total_clusters = len(set(labels))
    coverage_map: dict[str, set[int]] = {}
    for label, owner in zip(labels, owners):
        coverage_map.setdefault(owner, set()).add(int(label))
    score_map = {gen: len(cset) / total_clusters for gen, cset in coverage_map.items()}
    winner = max(score_map.items(), key=lambda kv: kv[1])[0]
    return winner, score_map


def prioritize_inputs(
    selected_embeddings: np.ndarray,
    selected_names: list[str],
    selected_texts: list[str],
    budget: int,
) -> list[tuple[str, str]]:
    if budget >= len(selected_names):
        return list(zip(selected_names, selected_texts))
    k = max(2, min(10, int(np.sqrt(len(selected_names)))))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(selected_embeddings)
    centers = km.cluster_centers_
    per_cluster: dict[int, list[tuple[int, float]]] = {}
    for idx, label in enumerate(labels):
        dist = np.linalg.norm(selected_embeddings[idx] - centers[label])
        per_cluster.setdefault(int(label), []).append((idx, float(dist)))
    for label in per_cluster:
        per_cluster[label].sort(key=lambda x: x[1], reverse=True)

    cluster_ids = sorted(per_cluster.keys(), key=lambda c: len(per_cluster[c]))
    chosen_idx: list[int] = []
    while len(chosen_idx) < budget:
        progressed = False
        for cid in cluster_ids:
            if per_cluster[cid]:
                idx, _ = per_cluster[cid].pop(0)
                chosen_idx.append(idx)
                progressed = True
                if len(chosen_idx) >= budget:
                    break
        if not progressed:
            break
    return [(selected_names[i], selected_texts[i]) for i in chosen_idx]


def _flatten_grouped_inputs(grouped: dict[str, list[tuple[str, str]]]) -> tuple[list[str], list[str], list[str]]:
    all_names: list[str] = []
    all_texts: list[str] = []
    owners: list[str] = []
    for gen, items in grouped.items():
        for name, text in items:
            owners.append(gen)
            all_names.append(name)
            all_texts.append(text)
    return all_names, all_texts, owners


def _load_embeddings(texts: list[str], provider: str, openai_api_key: str | None) -> np.ndarray:
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key or "")
        vectors = []
        for text in texts:
            emb = client.embeddings.create(model="text-embedding-3-small", input=text)
            vectors.append(emb.data[0].embedding)
        return np.asarray(vectors, dtype=np.float64)

    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(max_features=1024, ngram_range=(1, 2))
    return vec.fit_transform(texts).toarray().astype(np.float64)


def _export_prioritized_inputs(
    state: RunState,
    output_dir: Path,
    embeddings: np.ndarray,
    all_names: list[str],
    all_texts: list[str],
    owners: list[str],
    winner: str,
    cc_scores: dict[str, float],
) -> None:
    winner_idx = [i for i, owner in enumerate(owners) if owner == winner]
    prioritized = prioritize_inputs(
        embeddings[winner_idx, :],
        [all_names[i] for i in winner_idx],
        [all_texts[i] for i in winner_idx],
        int(state.config["prioritization_budget"]),
    )
    prioritized_dir = output_dir / "prioritized_inputs"
    safe_mkdir(prioritized_dir)
    for idx, (_, text) in enumerate(prioritized, start=1):
        (prioritized_dir / f"input_{idx}.txt").write_text(text, encoding="utf-8")

    zip_path = output_dir / "prioritized_inputs.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for txt in sorted(prioritized_dir.glob("*.txt")):
            zf.write(txt, arcname=txt.name)

    report = {
        "run_id": state.run_id,
        "subject": state.config["subject"],
        "embedding_model": state.config["embedding_model"],
        "selected_generator": winner,
        "candidate_generators": state.config["generators"],
        "requested_budget": int(state.config["prioritization_budget"]),
        "exported_inputs": len(prioritized),
        "cc_scores": cc_scores,
        "project_manifest": str(RUNS_ROOT / state.run_id / "project_manifest.json"),
        "inspection_report": str(RUNS_ROOT / state.run_id / "inspection_report.json"),
        "sut_analysis_report": str(RUNS_ROOT / state.run_id / "sut_analysis_report.json"),
        "grammar_adapter_report": str(RUNS_ROOT / state.run_id / "grammar_adapter_report.json"),
    }
    (output_dir / "run_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    state.outputs["run_report"] = report
    state.outputs["download"] = f"/api/runs/{state.run_id}/download"


def _restore_env(env_backup: dict[str, str | None]) -> None:
    for key, value in env_backup.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
