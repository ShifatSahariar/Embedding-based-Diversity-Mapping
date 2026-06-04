import os
import re
import json

# -------------------------------------------------------------
# --- Helper regex and text normalization utilities ------------
# -------------------------------------------------------------
MARKDOWN_FENCE = re.compile(r'^\s*```(?:basic|CALC|rhino)?\s*$', re.IGNORECASE)
HAS_LINENUM = re.compile(r'^\s*\d+\s+\S')
GOTO_GOSUB_NUM = re.compile(r'\b(?:GOTO|GOSUB)\s+(\d+)\b', re.IGNORECASE)


def coerce_newlines(s: str) -> str:
    """If string has literal \\n but no real newlines, convert once."""
    if "\\n" in s and "\n" not in s:
        return s.replace("\\n", "\n")
    return s


def needs_numbering(program: str) -> bool:
    """Decide whether to auto-number lines based on GOTO/GOSUB usage."""
    lines = [ln for ln in program.splitlines() if ln.strip()]
    has_any_numbers = any(HAS_LINENUM.match(ln) for ln in lines)
    has_jump_targets = bool(GOTO_GOSUB_NUM.search(program))
    return has_any_numbers or has_jump_targets


def clean_generated_text(program: str, end_token: str = "bye") -> str:
    """
    Cleans generated LLM text and enforces correct termination.
    1) Remove markdown fences
    2) Drop trailing RETURN if last non-empty line
    3) Enforce the given end_token ('bye', 'exit', etc.) as the final line (lowercase)
    4) Ensure trailing newline
    """
    lines = [ln for ln in program.splitlines()]
    lines = [ln for ln in lines if not MARKDOWN_FENCE.match(ln.strip())]

    # 2) Remove trailing RETURN (case-insensitive)
    non_empty = [i for i, ln in enumerate(lines) if ln.strip()]
    if non_empty:
        last_idx = non_empty[-1]
        last = lines[last_idx].strip()
        if last.lower().startswith("return"):
            del lines[last_idx]

    # 3) Find the first appearance of the termination keyword (case-insensitive)
    end_idx = None
    for i, ln in enumerate(lines):
        if end_token.lower() in ln.lower():
            end_idx = i
            break

    if end_idx is not None:
        lines = lines[:end_idx] + [end_token.lower()]
    else:
        lines.append(end_token.lower())

    out = "\n".join(lines).rstrip() + "\n"
    return out


# -------------------------------------------------------------
# --- Split JSON into text files with dynamic compiler support -
# -------------------------------------------------------------
def split_and_cleanup(json_path: str, output_dir: str, prefix: str = None):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    testcases = data.get("tests", [])
    compiler_name = data.get("compiler", "basic").lower()

    # Define termination keywords per compiler
    terminators = {
        "basic": "BYE",
        "CALC": "EXIT",
        "rhino": "",  # JS/Rhino programs don’t require a terminator
    }
    end_token = terminators.get(compiler_name, "BYE")

    count_written = 0
    skipped = 0
    os.makedirs(output_dir, exist_ok=True)

    for i, tc in enumerate(testcases, start=1):
        program = (tc.get("program") or tc.get("code") or "").strip()
        if not program:
            skipped += 1
            continue

        program = coerce_newlines(program)

        # Skip end-token normalization for JS-like languages (Rhino)
        if compiler_name != "rhino":
            program = clean_generated_text(program, end_token=end_token)
        else:
            program = re.sub(r'\s*;\s*', '; ', program)
            if not program.endswith("\n"):
                program += "\n"

        # NAMING
        if prefix:
            filename = f"{prefix}_{i}.txt"
        else:
            filename = f"{i}.txt"

        fp = os.path.join(output_dir, filename)
        with open(fp, "w", encoding="utf-8") as out:
            out.write(program)
        count_written += 1
        print(f"Wrote: {os.path.basename(fp)}")

    print(f"\nSplit complete — {count_written} files written in '{output_dir}'. Skipped: {skipped}.")

    # --- Cleanup JSON file after splitting ---
    try:
        os.remove(json_path)
        print(f"[CLEANUP] Removed temporary JSON file: {json_path}")
    except Exception as e:
        print(f"[WARN] Could not remove JSON file: {json_path}. Error: {e}")
