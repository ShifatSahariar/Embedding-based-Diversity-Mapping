"""Grammar loading and generator compatibility checks."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .config import GENERATOR_MAP, MAX_TEXT_BYTES
from .errors import ToolModeError
from .security import ensure_inside_allowed_scope, safe_resolve_local_path


def read_text_source(
    location: str | None,
    text: str | None,
    project_root: Path,
    machine_read_approved: bool = False,
) -> tuple[str | None, dict[str, Any]]:
    if text and text.strip():
        return text, {"source": "inline_text", "format": "text"}
    if not location:
        return None, {"source": "missing", "format": None}
    if location.startswith("http://") or location.startswith("https://"):
        with urlopen(location, timeout=20) as response:
            data = response.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES:
            raise ToolModeError("Grammar URL is too large.")
        suffix = Path(urlparse(location).path).suffix.lower().lstrip(".") or "text"
        return data.decode("utf-8", errors="ignore"), {"source": location, "format": suffix}

    candidate = safe_resolve_local_path(location)
    ensure_inside_allowed_scope(candidate, project_root, machine_read_approved)
    if not candidate.is_file():
        raise ToolModeError("Grammar location must point to a file, not a directory.")
    if candidate.stat().st_size > MAX_TEXT_BYTES:
        raise ToolModeError("Grammar file is too large.")
    suffix = candidate.suffix.lower().lstrip(".") or "text"
    return candidate.read_text(encoding="utf-8", errors="ignore"), {"source": str(candidate), "format": suffix}


def validate_grammar(grammar_text: str | None, grammar_meta: dict[str, Any]) -> dict[str, Any]:
    fmt = (grammar_meta.get("format") or "").lower()
    has_grammar = bool(grammar_text and grammar_text.strip())
    generator_status: dict[str, dict[str, Any]] = {}
    if not has_grammar:
        for gen in GENERATOR_MAP:
            generator_status[gen] = {
                "compatible": gen == "openai_no_gram",
                "reason": "No grammar supplied; OpenAI no-grammar mode is recommended.",
            }
        return {
            "has_grammar": False,
            "format": None,
            "issues": ["No grammar supplied."],
            "recommended_generators": ["openai_no_gram"],
            "generator_status": generator_status,
        }

    issues: list[str] = []
    if fmt not in {"bnf", "ebnf", "txt", "text", "fan", "isla", "py"}:
        issues.append(f"Unknown grammar extension '{fmt}'. OpenAI can still use it as text.")

    for gen in GENERATOR_MAP:
        compatible = False
        reason = ""
        if gen.startswith("openai"):
            compatible = True
            reason = "OpenAI accepts grammar text or freeform descriptions."
        elif gen.startswith("fan"):
            compatible = fmt == "fan"
            reason = "Fandango requires .fan grammar files."
        elif gen.startswith("isla"):
            compatible = fmt in {"bnf", "isla"}
            reason = "ISLa requires .bnf and optionally .isla constraints."
        elif gen.startswith("fuzz"):
            compatible = fmt == "py"
            reason = "Fuzzingbook currently requires a Python grammar module."
        generator_status[gen] = {"compatible": compatible, "reason": reason}

    recommended = [gen for gen, info in generator_status.items() if info["compatible"]] or ["openai_gram"]
    return {
        "has_grammar": True,
        "format": fmt or "text",
        "issues": issues,
        "recommended_generators": recommended,
        "generator_status": generator_status,
    }
