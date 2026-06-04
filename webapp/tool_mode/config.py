"""Dependency-light constants for SpreadEx tool mode."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "webapp_runs"
STATIC_ROOT = REPO_ROOT / "webapp" / "static"

MAX_SCAN_FILES = 400
MAX_TEXT_BYTES = 2 * 1024 * 1024

GENERATOR_MAP = {
    "fuzz_prob": ("fuzzingbook", "probabilistic"),
    "fuzz_equal": ("fuzzingbook", "equal_prob"),
    "fan_con": ("fandango", "constraints"),
    "fan_no_con": ("fandango", "no_constraints"),
    "isla_con": ("isla", "constraints"),
    "isla_no_con": ("isla", "no_constraints"),
    "openai_gram": ("openai", "with_grammar"),
    "openai_no_gram": ("openai", "without_grammar"),
}

GENERATOR_FAMILIES = {
    "fuzzingbook": {
        "label": "FuzzingBook",
        "internal_mode": "fuzz_equal",
    },
    "fandango": {
        "label": "Fandango",
        "internal_mode": "fan_no_con",
    },
    "isla": {
        "label": "ISLa",
        "internal_mode": "isla_no_con",
    },
    "llm": {
        "label": "LLM Generator",
        "internal_mode_with_grammar": "openai_gram",
        "internal_mode_without_grammar": "openai_no_gram",
    },
}

MODEL_OPTIONS = ["openai", "unixcoder", "graph_codebert", "codestral", "qwen3"]
PROVIDER_BY_MODEL = {
    "openai": "openai",
    "unixcoder": "local",
    "graph_codebert": "local",
    "codestral": "codestral",
    "qwen3": "local",
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Disable in hosted/public deployments.
TOOL_MODE_NATIVE_BROWSE_ENABLED = _env_bool("TOOL_MODE_NATIVE_BROWSE_ENABLED", True)
