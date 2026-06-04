"""Grammar analysis and run-local adapter generation for tool mode."""

import ast
import re
from pathlib import Path
from typing import Any

from .config import GENERATOR_FAMILIES, RUNS_ROOT
from .storage import safe_mkdir


SUPPORTED_FAMILIES = set(GENERATOR_FAMILIES.keys())


def analyze_and_adapt_grammar(
    run_id: str,
    grammar_text: str | None,
    grammar_meta: dict[str, Any],
    selected_generators: list[str],
    llm_constraints: str | None = None,
) -> dict[str, Any]:
    """Prepare family-specific grammar files without modifying the original grammar."""
    selected = _normalize_families(selected_generators, bool(grammar_text and grammar_text.strip()))
    run_root = RUNS_ROOT / run_id
    adapted_dir = run_root / "adapted_grammars"
    safe_mkdir(adapted_dir)

    original_format = _detect_format(grammar_text, grammar_meta)
    rules, warnings = _extract_rules(grammar_text or "", original_format)
    start_symbol = _detect_start_symbol(rules, grammar_text or "")
    unsupported: list[str] = []
    adapted: dict[str, str] = {}

    if "fuzzingbook" in selected:
        path = adapted_dir / "fuzzingbook_grammar.py"
        path.write_text(_to_fuzzingbook(rules, start_symbol), encoding="utf-8")
        adapted["fuzzingbook"] = str(path)

    if "fandango" in selected:
        path = adapted_dir / "fandango_grammar.fan"
        path.write_text(_to_angle_bnf(rules, start_symbol, original_text=grammar_text or ""), encoding="utf-8")
        adapted["fandango"] = str(path)

    if "isla" in selected:
        path = adapted_dir / "isla_grammar.bnf"
        path.write_text(_to_angle_bnf(rules, start_symbol, original_text=grammar_text or ""), encoding="utf-8")
        adapted["isla"] = str(path)

    if "llm" in selected:
        path = adapted_dir / "llm_generation_prompt.txt"
        path.write_text(_to_llm_prompt(rules, start_symbol, grammar_text or "", llm_constraints), encoding="utf-8")
        adapted["llm"] = str(path)

    if not grammar_text and any(gen != "llm" for gen in selected):
        warnings.append("No grammar was supplied; only the LLM no-grammar path can run reliably.")
    if original_format == "plain_text":
        warnings.append("Plain text grammar was treated as an informal specification for adapter generation.")
    if "constraint" in (grammar_text or "").lower():
        warnings.append("Constraint translation is best-effort in v1; review generated files before running.")

    confidence = _confidence(original_format, rules, warnings)
    return {
        "original_format": original_format,
        "start_symbol": start_symbol,
        "selected_generators": selected,
        "adapted_grammars": adapted,
        "warnings": warnings,
        "unsupported_features": unsupported,
        "confidence": confidence,
        "generator_status": _generator_status(selected, adapted),
    }


def map_families_to_internal_modes(selected_families: list[str], has_grammar: bool) -> list[str]:
    modes: list[str] = []
    for family in _normalize_families(selected_families, has_grammar):
        if family == "llm":
            modes.append("openai_gram" if has_grammar else "openai_no_gram")
        else:
            mode = GENERATOR_FAMILIES[family]["internal_mode"]
            modes.append(str(mode))
    return modes


def _normalize_families(selected: list[str], has_grammar: bool) -> list[str]:
    families = [item for item in selected if item in SUPPORTED_FAMILIES]
    if not families:
        families = ["llm"]
    if not has_grammar:
        return ["llm"] if "llm" not in families else families
    return families


def _detect_format(grammar_text: str | None, grammar_meta: dict[str, Any]) -> str:
    fmt = (grammar_meta.get("format") or "").lower()
    if fmt == "py":
        return "FuzzingBook"
    if fmt == "fan":
        return "Fandango"
    if fmt in {"bnf", "ebnf"}:
        return fmt.upper()
    if fmt == "isla":
        return "ISLa"
    text = grammar_text or ""
    if re.search(r"<[^>]+>\s*::=", text):
        return "BNF"
    if "::=" in text or "->" in text:
        return "EBNF"
    if text.strip():
        return "plain_text"
    return "unknown"


def _extract_rules(grammar_text: str, original_format: str) -> tuple[dict[str, list[str]], list[str]]:
    if original_format == "FuzzingBook":
        rules = _extract_fuzzingbook_rules(grammar_text)
        if rules:
            return rules, []
    rules = _extract_bnf_rules(grammar_text)
    if rules:
        return rules, []
    if grammar_text.strip():
        return {"<start>": [grammar_text.strip()]}, ["Could not parse production rules; using the grammar text as an informal start rule."]
    return {"<start>": [""]}, ["No grammar text was available."]


def _extract_fuzzingbook_rules(grammar_text: str) -> dict[str, list[str]]:
    try:
        tree = ast.parse(grammar_text)
    except SyntaxError:
        return {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id in {"GRAMMAR", "grammar"} for target in node.targets):
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    return {}
                if isinstance(value, dict):
                    return {str(k): [str(item) for item in v] for k, v in value.items() if isinstance(v, list)}
    return {}


def _extract_bnf_rules(grammar_text: str) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = {}
    for raw_line in grammar_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if "::=" in line:
            left, right = line.split("::=", 1)
        elif "->" in line:
            left, right = line.split("->", 1)
        elif ":" in line and not line.lower().startswith(("http:", "https:")):
            left, right = line.split(":", 1)
        else:
            continue
        symbol = _angle(left.strip())
        alternatives = [part.strip() for part in right.split("|") if part.strip()]
        rules.setdefault(symbol, []).extend(alternatives or [""])
    return rules


def _detect_start_symbol(rules: dict[str, list[str]], grammar_text: str) -> str:
    for candidate in ("<start>", "<START>", "<program>", "<input>"):
        if candidate in rules:
            return candidate
    match = re.search(r"start\s*[:=]\s*(<[^>]+>|\w+)", grammar_text, re.IGNORECASE)
    if match:
        return _angle(match.group(1))
    return next(iter(rules.keys()), "<start>")


def _angle(symbol: str) -> str:
    cleaned = symbol.strip().strip("'\"")
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return cleaned
    return f"<{cleaned}>"


def _to_fuzzingbook(rules: dict[str, list[str]], start_symbol: str) -> str:
    items = []
    normalized = dict(rules)
    if "<start>" not in normalized and start_symbol in normalized:
        normalized = {"<start>": [start_symbol], **normalized}
    for symbol, alternatives in normalized.items():
        alts = ", ".join(repr(alt) for alt in alternatives)
        items.append(f"    {symbol!r}: [{alts}],")
    return "# Auto-generated by SpreadEx Grammar Adapter Agent.\nGRAMMAR = {\n" + "\n".join(items) + "\n}\n"


def _to_angle_bnf(rules: dict[str, list[str]], start_symbol: str, original_text: str) -> str:
    if not rules and original_text.strip():
        return original_text.strip() + "\n"
    lines = []
    if start_symbol != "<start>" and "<start>" not in rules:
        lines.append(f"<start> ::= {start_symbol}")
    for symbol, alternatives in rules.items():
        lines.append(f"{_angle(symbol)} ::= {' | '.join(alternatives)}")
    return "\n".join(lines) + "\n"


def _to_llm_prompt(
    rules: dict[str, list[str]],
    start_symbol: str,
    original_text: str,
    llm_constraints: str | None,
) -> str:
    lines = [
        "Generate valid test inputs for the target program.",
        f"Start symbol: {start_symbol}",
        "",
        "Generation rules:",
    ]
    if rules:
        for symbol, alternatives in rules.items():
            lines.append(f"- {symbol} ::= {' | '.join(alternatives)}")
    elif original_text.strip():
        lines.append(original_text.strip())
    else:
        lines.append("- No strict grammar was supplied. Infer compact valid inputs from the subject context.")
    if llm_constraints and llm_constraints.strip():
        lines.extend(["", "Additional user constraints or hints:", llm_constraints.strip()])
    lines.append("")
    lines.append("Return only generated inputs, without explanations.")
    return "\n".join(lines) + "\n"


def _confidence(original_format: str, rules: dict[str, list[str]], warnings: list[str]) -> float:
    if original_format == "unknown":
        return 0.2
    score = 0.45 + min(len(rules), 5) * 0.08 - min(len(warnings), 4) * 0.07
    return round(max(0.1, min(0.95, score)), 2)


def _generator_status(selected: list[str], adapted: dict[str, str]) -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for family in GENERATOR_FAMILIES:
        prepared = family in adapted
        status[family] = {
            "compatible": family in selected and prepared,
            "prepared": prepared,
            "reason": "Prepared by Grammar Adapter Agent." if prepared else "Not selected or no compatible grammar prepared.",
        }
    return status
