"""Run-local generator adapters for SpreadEx tool mode."""

import glob
import json
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

from .config import RUNS_ROOT


def generate_inputs_for_tool_mode(run_id: str, subject: str, gen: str, num_inputs: int, output_dir: Path) -> None:
    """Use run-local grammar files so the research artifact grammar folders are never mutated."""
    grammar_file = _grammar_file_for_run(run_id, gen)
    grammar_text = grammar_file.read_text(encoding="utf-8", errors="ignore") if grammar_file else None
    if gen.startswith("openai"):
        _write_openai_inputs(subject, gen, grammar_text, num_inputs, output_dir)
    elif gen.startswith("fan"):
        if grammar_file is None:
            raise RuntimeError("Fandango generation requires a .fan grammar.")
        _generate_with_fandango(gen, grammar_file, num_inputs, output_dir)
    elif gen.startswith("isla"):
        if grammar_file is None:
            raise RuntimeError("ISLa generation requires a .bnf grammar.")
        _generate_with_isla(gen, grammar_file, num_inputs, output_dir)
    elif gen.startswith("fuzz"):
        if grammar_file is None:
            raise RuntimeError("Fuzzingbook generation requires a Python grammar module.")
        _generate_with_fuzzingbook(gen, grammar_file, num_inputs, output_dir)
    else:
        raise RuntimeError(f"Unsupported generator: {gen}")


def _grammar_file_for_run(run_id: str, gen: str) -> Path | None:
    adapted = _adapted_grammar_for_run(run_id, gen)
    if adapted is not None:
        return adapted
    grammar_dir = RUNS_ROOT / run_id / "grammars"
    if not grammar_dir.exists():
        return None
    for path in sorted(grammar_dir.iterdir()):
        if path.is_file():
            return path
    return None


def _adapted_grammar_for_run(run_id: str, gen: str) -> Path | None:
    report_path = RUNS_ROOT / run_id / "grammar_adapter_report.json"
    if not report_path.exists():
        return None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    family_by_mode = {
        "fuzz_equal": "fuzzingbook",
        "fuzz_prob": "fuzzingbook",
        "fan_no_con": "fandango",
        "fan_con": "fandango",
        "isla_no_con": "isla",
        "isla_con": "isla",
        "openai_gram": "llm",
        "openai_no_gram": "llm",
    }
    family = family_by_mode.get(gen)
    path = (report.get("adapted_grammars") or {}).get(family)
    if not path:
        return None
    candidate = Path(path)
    return candidate if candidate.exists() else None


def _write_openai_inputs(subject: str, gen: str, grammar_text: str | None, num_inputs: int, output_dir: Path) -> None:
    try:
        from GENERATED_INPUTS.input_gen_utils import _init_openai_client
        from GENERATED_INPUTS.llm_based_input_generator import _generate_batch_auto_sized
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenAI/LLM generation helpers are missing. Expected top-level GENERATED_INPUTS/ "
            "with input_gen_utils.py and llm_based_input_generator.py."
        ) from exc

    client = _init_openai_client()
    if client is None:
        raise RuntimeError("OpenAI client unavailable for generation.")
    tests = _generate_batch_auto_sized(
        compiler_name=subject,
        grammar=grammar_text if gen == "openai_gram" else None,
        desired_k=num_inputs,
        model_name="gpt-4.1",
        client=client,
    )
    for i, item in enumerate(tests, start=1):
        program = (item.get("program") or item.get("code") or "").strip()
        if program:
            (output_dir / f"{gen}_{i}.txt").write_text(program.rstrip() + "\n", encoding="utf-8")


def _generate_with_fandango(gen: str, grammar_file: Path, num_inputs: int, output_dir: Path) -> None:
    if shutil.which("fandango") is None:
        raise RuntimeError("Fandango is not installed or not in PATH.")
    command = ["fandango", "fuzz", "-f", str(grammar_file), "-n", str(num_inputs), "-d", str(output_dir), "-N", "1000"]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    generated = sorted(glob.glob(str(output_dir / "fandango-*.txt")))
    for i, src in enumerate(generated, start=1):
        shutil.move(src, output_dir / f"{gen}_{i}.txt")


def _generate_with_isla(gen: str, grammar_file: Path, num_inputs: int, output_dir: Path) -> None:
    if shutil.which("isla") is None:
        raise RuntimeError("ISLa is not installed or not in PATH.")
    command = ["isla", "solve", "-s", "1", "-f", str(num_inputs), "-n", str(num_inputs), str(grammar_file), "-d", str(output_dir)]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    generated = sorted(output_dir.glob("[0-9]*.txt"), key=lambda p: int(p.stem))
    for i, src in enumerate(generated, start=1):
        shutil.move(str(src), output_dir / f"{gen}_{i}.txt")


def _generate_with_fuzzingbook(gen: str, grammar_file: Path, num_inputs: int, output_dir: Path) -> None:
    try:
        from fuzzingbook.Grammars import convert_ebnf_grammar, extend_grammar
        from fuzzingbook.ProbabilisticGrammarFuzzer import ProbabilisticGrammarFuzzer
    except ImportError as exc:
        raise RuntimeError("Fuzzingbook is not installed. Install requirements before using fuzzingbook generators.") from exc
    spec = importlib.util.spec_from_file_location("tool_mode_grammar", grammar_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import Fuzzingbook grammar module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    grammar = getattr(module, "GRAMMAR", None) or getattr(module, "grammar", None)
    if grammar is None:
        raise RuntimeError("Fuzzingbook grammar module must define GRAMMAR or grammar.")
    prepared = extend_grammar(convert_ebnf_grammar(grammar))
    fuzzer = ProbabilisticGrammarFuzzer(prepared)
    for i in range(1, num_inputs + 1):
        (output_dir / f"{gen}_{i}.txt").write_text(fuzzer.fuzz().rstrip() + "\n", encoding="utf-8")
