import re
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set, Optional

# -----------------------------
# Config & constants
# -----------------------------

RANDOM_STR_POOL = ["HELLO", "WORLD", "BASIC", "TEST", "DUMMY", "OK", "VAL", "TXT"]
NUM_POOL = list(range(1, 100))


VAR_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]?\$?)$")
# Regex to strip numbers (int, float, scientific notation)
NUMBER_RE = re.compile(r'\b\d+(?:\.\d+)?(?:E[+-]?\d+)?\b', re.IGNORECASE)

# Regex to strip quoted strings
STRING_RE = re.compile(r'"[^"]*"')

# Arrays like A(10) or Ab(3,4) – still only two chars before optional $
ARRAY_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9]?)\(\s*([0-9]+(?:\s*,\s*[0-9]+)*)\s*\)")


# Recognize a BASIC line: "<number> <rest>"
LINE_RE = re.compile(r"^\s*(\d+)\s+(.*\S)\s*$", re.IGNORECASE)

# Keywords & functions (case-insensitive)
RESERVED = {
  "IF","THEN","AND","OR","NOT","FOR","NEXT","TO","STEP","GOTO","GOSUB","RETURN",
  "END","STOP","PRINT","INPUT","DIM","DATA","READ","RESTORE","RANDOMIZE",
  "TRON","TROFF","RESUME","LIST","LET","ON"
}

BUILTINS = {
    "RND","INT","SIN","COS","TAN","ATN","SQR","ABS","LOG","SGN","LEN","VAL","STR$","SPC$","MAX","MIN",
    "CHR$","LEFT$","RIGHT$","TAB$","MID$","FRE","AND","OR","NOT"
}

def is_var_token(tok: str) -> bool:
    """
    Decide whether a token is a valid BASIC variable.
    - Variables are already restricted by grammar to max two characters (+ optional $).
    - Here we only need to reject reserved keywords and built-in functions.
    """
    if not tok:
        return False
    t = tok.strip()
    if t.upper() in RESERVED or t.upper() in BUILTINS:
        return False
    return bool(VAR_RE.fullmatch(t))


def var_is_string(tok: str) -> bool:
    return tok.endswith("$")

@dataclass
class ProgramIndex:
    lines: List[Tuple[int, str]] = field(default_factory=list)
    line_set: set[int] = field(default_factory=set)
    line_to_code: Dict[int, str] = field(default_factory=dict)

    used: set[str] = field(default_factory=set)
    defined: set[str] = field(default_factory=set)
    loop_vars: set[str] = field(default_factory=set)
    var_usage_lines: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    var_def_lines: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))

    read_vars: List[List[str]] = field(default_factory=list)

    has_any_data: bool = False


    goto_targets: Dict[int, List[int]] = field(default_factory=dict)
    gosub_targets: Dict[int, List[int]] = field(default_factory=dict)
    explicit_targets: set[int] = field(default_factory=set)

    actions: List[str] = field(default_factory=list)


# -----------------------------
# Parsing helpers
# -----------------------------
def ensure_valid_prints(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """
    Ensure the program has exactly ONE unnumbered PRINT placed immediately before BYE:
      - Convert numbered PRINTs (e.g., '120 PRINT A') to unnumbered 'PRINT A'.
      - Deduplicate multiple unnumbered PRINTs (keep first, drop others).
      - If missing, synthesize one using a defined variable (prefer LET-defined), else 0.
      - Missing printed vars get defined later by PHASE 2.
    """
    new: List[Tuple[int, str]] = []

    # 1) Convert numbered PRINTs -> unnumbered
    converted: List[Tuple[int, str]] = []
    for ln, code in idx.lines:
        u = code.strip().upper()
        if u.startswith("PRINT") and ln >= 0:
            converted.append((-1, code.strip()))
            idx.actions.append(f"convert numbered PRINT at {ln} -> unnumbered")
        else:
            converted.append((ln, code))
    idx.lines = converted


    # Build candidates for printing.
    # 1) Prefer any variable that appears on a LET LHS (definitely scalar).
    let_defined = [v for v, defs in idx.var_def_lines.items() if defs]

    # 2) Also allow any variables that the program "uses" (they will be defined by Phase 2 if missing).
    used_vars = sorted(idx.used) if idx.used else []

    # 3) Heuristically detect array base names used with parentheses to exclude them from printing.
    arrays_used = set()
    for _, c in idx.lines:
        for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9]?)\s*\(", c):
            arrays_used.add(m.group(1).upper())

    # Merge & filter (LET first), exclude anything that looks like an array base.
    merged = []
    seen = set()
    for v in let_defined + used_vars:
        vu = v.upper()
        if vu in seen or vu in arrays_used:
            continue
        if is_var_token(v):
            merged.append(v)
            seen.add(vu)

    def choose_print_item() -> str:
        # If we have any variable candidates, use one of them; else use a random numeric literal.
        if merged:
            return random.choice(merged)
        return str(random.choice(NUM_POOL))



    # 2) Ensure exactly one unnumbered PRINT
    unnum_positions = [i for i, (ln, c) in enumerate(idx.lines) if ln < 0 and c.strip().upper().startswith("PRINT")]
    if not unnum_positions:
        # Insert a PRINT <var> immediately before BYE (or at end if BYE missing)
        v = choose_print_item()

        bye_index = next((i for i, (_, c) in enumerate(idx.lines) if c.strip().upper() == "BYE"), None)
        insert_at = bye_index if bye_index is not None else len(idx.lines)
        idx.lines.insert(insert_at, (-1, f"PRINT {v}"))
        idx.actions.append(f"insert PRINT {v} " + ("before BYE" if bye_index is not None else "at end (no BYE found)"))
    else:
        # Deduplicate: keep first, drop the rest
        first_seen = False
        deduped: List[Tuple[int, str]] = []
        for ln, c in idx.lines:
            if ln < 0 and c.strip().upper().startswith("PRINT"):
                if not first_seen:
                    deduped.append((ln, c))
                    first_seen = True
                else:
                    idx.actions.append("remove duplicate unnumbered PRINT")
            else:
                deduped.append((ln, c))
        idx.lines = deduped

        # Ensure the kept PRINT is before BYE
        bye_index = next((i for i, (_, c) in enumerate(idx.lines) if c.strip().upper() == "BYE"), None)
        first_print_index = next((i for i, (ln, c) in enumerate(idx.lines) if ln < 0 and c.strip().upper().startswith("PRINT")), None)
        if first_print_index is not None and bye_index is not None and first_print_index > bye_index:
            ln, c = idx.lines.pop(first_print_index)
            idx.lines.insert(bye_index, (ln, c))
            idx.actions.append("move PRINT before BYE")

    return new



def ensure_missing_vars_at_header(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """
    Insert UNNUMBERED LET definitions for all missing variables
    at the VERY BEGINNING of the program, so they appear before any usage
    and never after BYE.
    """
    new: List[Tuple[int, str]] = []

    # Which variables are missing?
    missing = (idx.used - idx.defined) - getattr(idx, "loop_vars", set())
    # Keep only valid variable tokens, stable order
    to_define = [v for v in sorted(missing) if is_var_token(v)]
    if not to_define:
        return new

    # Build unnumbered header LETs
    header_defs: List[Tuple[int, str]] = []
    for var in to_define:
        if var_is_string(var):
            val = f"\"{random.choice(RANDOM_STR_POOL)}\""
        else:
            val = str(random.choice(NUM_POOL))
        header_defs.append((-1, f"LET {var} = {val}"))
        idx.actions.append(f"define header var (UNNUMBERED): {var}")
        idx.defined.add(var)

    # PREPEND header definitions at the very start of the program
    # (this guarantees they are before any usage and before BYE)
    idx.lines = header_defs + idx.lines

    return new




def next_header_lines(existing: Set[int], count: int, start=1, step=1) -> List[int]:
    """Produce 'count' header line numbers (before smallest existing) that are free."""
    used = set(existing)
    out = []
    ln = start
    while len(out) < count:
        if ln not in used:
            out.append(ln)
            used.add(ln)
        ln += step
    return out
def parse_program(text: str) -> ProgramIndex:
    idx = ProgramIndex()
    for raw in text.splitlines():
        raw = raw.rstrip()
        if not raw.strip():
            continue
        m = LINE_RE.match(raw)
        if m:
            ln = int(m.group(1))
            code = m.group(2)
            idx.lines.append((ln, code))
            idx.line_set.add(ln)
            idx.line_to_code[ln] = code
        else:
            # Non-numbered line: keep as-is by assigning a virtual negative line to preserve order
            # (we’ll float these to the end unchanged)
            idx.lines.append((-1, raw))
    # stable sort by line number (non-numbered last)
    idx.lines.sort(key=lambda p: (p[0] < 0, p[0]))
    return idx

def tokenize_expr_vars(expr: str) -> list[str]:
    # 1) Remove string literals
    s = STRING_RE.sub(' ', expr)
    # 2) Remove numbers (so 6484.27E3 disappears entirely)
    s = NUMBER_RE.sub(' ', s)
    # 3) Split into tokens on non-alphanumeric
    raw_tokens = re.split(r'[^A-Za-z0-9\$]', s)
    # 4) Keep only real variable tokens
    return [t for t in raw_tokens if VAR_RE.match(t) and is_var_token(t)]

def extract_targets(action: str) -> List[int]:
    # Fetch integers in action part (line numbers)
    return [int(x) for x in re.findall(r"\b\d+\b", action)]

# -----------------------------
# First pass: collect facts
# -----------------------------

def scan_program(idx: ProgramIndex) -> None:
    for ln, code in idx.lines:
        up = code.strip().upper()

        # DATA?
        if up.startswith("DATA"):
            idx.has_any_data = True

        elif code.strip().upper().startswith("DIM"):
            for m in ARRAY_RE.finditer(code):
                arr_name = m.group(1)  # e.g., "Y"
                idx.defined.add(arr_name)
                idx.actions.append(f"array defined: {arr_name}")

        # INPUT "prompt"; A, B$
        elif code.strip().upper().startswith("INPUT"):
            tail = re.split(r"\bINPUT\b", code, flags=re.IGNORECASE)[1].strip()

            # If there's a quoted prompt followed by a semicolon, remove it
            if tail.startswith('"'):
                m = re.match(r'"[^"]*"\s*;\s*(.*)', tail)
                if m:
                    tail = m.group(1)

            # Now split remaining by commas
            vars_ = [v.strip() for v in tail.split(",") if v.strip()]
            for v in vars_:
                if is_var_token(v):
                    idx.defined.add(v)
                    idx.actions.append(f"input defines: {v}")

        # READ A, B$
        if up.startswith("READ"):
            tail = re.split(r"\bREAD\b", code, flags=re.IGNORECASE)[1]
            vars_ = [v.strip() for v in tail.split(",") if v.strip()]
            keep = [v for v in vars_ if is_var_token(v)]
            if keep:
                idx.read_vars.append(keep)
                # Treat READ LHS as "defined by I/O"
                for v in keep:
                    idx.defined.add(v)

        # LET X = <expr>
        if up.startswith("LET "):
            # SAFE parse: split once on =
            if "=" in code:
                lhs, rhs = code.split("=", 1)
                var = lhs.split(None, 1)[1].strip() if " " in lhs else lhs.strip()[3:].strip()
                if is_var_token(var):
                    idx.defined.add(var)
                # RHS used variables
                for v in tokenize_expr_vars(rhs):
                    idx.used.add(v)

        # FOR I = start TO end [STEP s]
        elif up.startswith("FOR "):
            # LHS var before '='
            if "=" in code:
                left, right = code.split("=", 1)
                var = left.split(None, 1)[1].strip()  # after 'FOR'
                if is_var_token(var):
                    idx.defined.add(var)
                    idx.loop_vars.add(var)
                # Collect RHS vars (start, end, step)
                for v in tokenize_expr_vars(right):
                    # filter out TO/STEP captured as vars
                    if v.upper() not in {"TO", "STEP"}:
                        idx.used.add(v)

        # NEXT I
        elif up.startswith("NEXT"):
            pass  # loop var already treated as defined by FOR

        # IF <cond> THEN <stmt | line>
        elif code.strip().upper().startswith("IF "):
            parts = re.split(r'\bTHEN\b', code, flags=re.IGNORECASE, maxsplit=1)

            # --- Condition part ---
            cond = re.sub(r'^\s*IF\b', '', parts[0], flags=re.IGNORECASE).strip()
            for v in tokenize_expr_vars(cond):
                if is_var_token(v):
                    idx.used.add(v)

            # --- THEN part ---
            if len(parts) > 1:
                action = parts[1].strip()

                # Case 1: THEN GOTO or GOSUB
                if action.upper().startswith("GOTO") or action.upper().startswith("GOSUB"):
                    idx.explicit_targets.update(extract_targets(action))
                    if action.upper().startswith("GOSUB"):
                        idx.gosub_targets.setdefault(ln, []).extend(extract_targets(action))
                    else:
                        idx.goto_targets.setdefault(ln, []).extend(extract_targets(action))

                # Case 2: THEN LET
                elif action.upper().startswith("LET "):
                    assign = action[4:].strip()  # after 'LET'
                    lhs_rhs = assign.split("=", 1)
                    if len(lhs_rhs) == 2:
                        lhs = lhs_rhs[0].strip()
                        rhs = lhs_rhs[1].strip()

                        # mark lhs as defined
                        if is_var_token(lhs):
                            idx.defined.add(lhs)

                        # mark rhs vars as used
                        for v in tokenize_expr_vars(rhs):
                            if is_var_token(v):
                                idx.used.add(v)

                # Case 3: THEN <number>   (implicit GOTO)
                m_num = re.match(r"^\s*(\d+)\s*$", action)
                if m_num:
                    t = int(m_num.group(1))
                    idx.explicit_targets.add(t)
                    idx.goto_targets.setdefault(ln, []).append(t)
                else:
                    # Case 4: Other THEN actions (PRINT, STOP, END, etc.)
                    for v in tokenize_expr_vars(action):
                        if is_var_token(v):
                            idx.used.add(v)

        # PRINT <expr list>
        if up.startswith("PRINT"):
            tail = code.split(None, 1)[1] if " " in code else ""
            for v in tokenize_expr_vars(tail):
                idx.used.add(v)

        # ON R GOTO 10,20 or ON R GOSUB 40
        if up.startswith("ON "):
            # control var is used
            ctrl = code.split()[1]
            if is_var_token(ctrl):
                idx.used.add(ctrl)
            idx.explicit_targets.update(extract_targets(code))
            if "GOSUB" in up:
                idx.gosub_targets.setdefault(ln, []).extend(extract_targets(code))
            elif "GOTO" in up:
                idx.goto_targets.setdefault(ln, []).extend(extract_targets(code))

        # GOTO/GOSUB n
        if up.startswith("GOTO "):
            t = extract_targets(code)
            if t:
                idx.explicit_targets.update(t)
                idx.goto_targets.setdefault(ln, []).extend(t)
        if up.startswith("GOSUB "):
            t = extract_targets(code)
            if t:
                idx.explicit_targets.update(t)
                idx.gosub_targets.setdefault(ln, []).extend(t)

        # Generic usage elsewhere (don’t mark keywords/functions)
        # (Skip REM lines)
        if up.startswith("REM"):
            continue
        for v in tokenize_expr_vars(code):
            # exclude LHS already handled and DIM labels; filter keywords/functions
            if v.upper() not in RESERVED and v.upper() not in BUILTINS:
                # Already handled most definitions; this only adds stray uses
                idx.used.add(v)

# -----------------------------
# Fixers
# -----------------------------


def ensure_missing_vars(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """Insert LETs for missing vars before their first usage line,
       not just at the header."""
    new = []
    missing = (idx.used - idx.defined) - idx.loop_vars
    truly_missing = [v for v in sorted(missing) if is_var_token(v)]

    for v in truly_missing:
        # Find first usage
        first_use = min(idx.var_usage_lines.get(v, [max(idx.line_set) + 10]))
        # Find first definition (if any)
        first_def = min(idx.var_def_lines.get(v, [99999]))

        # If never defined, or defined only after first usage → insert before usage
        if first_def > first_use:
            ln = smallest_gap_before(idx, first_use)
            val = (f"\"{random.choice(RANDOM_STR_POOL)}\""
                   if var_is_string(v) else str(random.choice(NUM_POOL)))
            new.append((ln, f"LET {v} = {val}"))
            idx.actions.append(f"define: {v} before {first_use} at {ln}")
            idx.line_set.add(ln)
            idx.defined.add(v)

    return new


def ensure_data_before_read(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """If there are READ statements but no DATA earlier, insert DATA lines matching variable types."""
    new = []
    if not idx.read_vars:
        return new
    # Strategy: For each READ occurrence, if there was no DATA before it, insert a DATA line
    # immediately BEFORE that READ line, matching type & arity.
    # First, map line -> code for quick lookup
    line_to_idx = {ln: i for i, (ln, _) in enumerate(idx.lines)}
    # Collect READ line numbers in order
    read_line_positions = []
    for ln, code in idx.lines:
        if code.strip().upper().startswith("READ"):
            read_line_positions.append((ln, line_to_idx.get(ln, None)))

    # If there is at least one DATA anywhere, we’re ok globally,
    # but your requirement says: ensure DATA appears BEFORE each READ if missing.
    # So we check per READ anchor if there’s a DATA above it; if not, inject one right above.
    for (ln, pos) in read_line_positions:
        if pos is None or pos == 0:
            # If can’t find position, conservatively inject a header DATA
            vals = synth_data_values_for_read_line(idx, ln)
            new_ln = smallest_gap_before(idx, ln)
            new.append((new_ln, f"DATA {vals}"))
            idx.actions.append(f"insert DATA at {new_ln} for READ at {ln}")
            idx.line_set.add(new_ln)
            continue

        # Check if any DATA exists above this index
        has_data_above = any(idx.lines[i][1].strip().upper().startswith("DATA") for i in range(0, pos))
        if not has_data_above:
            vals = synth_data_values_for_read_line(idx, ln)
            new_ln = smallest_gap_before(idx, ln)
            new.append((new_ln, f"DATA {vals}"))
            idx.actions.append(f"insert DATA at {new_ln} for READ at {ln}")
            idx.line_set.add(new_ln)

    return new

def synth_data_values_for_read_line(idx: ProgramIndex, read_ln: int) -> str:
    """Find the READ vars at read_ln and synthesize DATA values matching type & order."""
    # Find the specific READ at read_ln
    code = idx.line_to_code.get(read_ln, "")
    tail = re.split(r"\bREAD\b", code, flags=re.IGNORECASE)
    if len(tail) < 2:
        # fallback: use first READ group recorded
        vars_seq = idx.read_vars[0] if idx.read_vars else []
    else:
        vars_seq = [v.strip() for v in tail[1].split(",") if is_var_token(v.strip())]
    values = []
    for v in vars_seq:
        if var_is_string(v):
            values.append(f"\"{random.choice(RANDOM_STR_POOL)}\"")
        else:
            values.append(str(random.choice(NUM_POOL)))
    return ", ".join(values) if values else "\"DUMMY\""

def smallest_gap_before(idx: ProgramIndex, anchor_ln: int) -> int:
    """Pick a free line number < anchor_ln (tries anchor_ln-1, then anchor_ln-2, etc.)."""
    cand = anchor_ln - 1
    while cand in idx.line_set or cand <= 0:
        cand -= 1
        if cand <= 0:
            # fallback header
            cand = min(set(range(1, 10000)) - idx.line_set)  # very defensive
            break
    return cand
def ensure_loops_balanced(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """
    Ensure every FOR has a matching NEXT, and every NEXT has a matching FOR.
    - Inserts NEXT after unmatched FORs.
    - Inserts dummy FOR before unmatched NEXTs.
    - Fixes mismatched NEXT vars to match their FOR.
    """
    new: List[Tuple[int, str]] = []
    open_stack = []   # [(line, var)] for open FOR loops
    seen_for_vars = set(idx.loop_vars)  # already tracked vars

    # Step 1: Traverse program lines in order
    for ln, code in sorted(idx.lines, key=lambda p: p[0]):
        ucode = code.strip().upper()

        # Detect FOR statements
        if ucode.startswith("FOR "):
            m = re.match(r"FOR\s+([A-Z][A-Z0-9\$]?)\s*=", ucode, re.I)
            if m:
                var = m.group(1)
            else:
                var = "I"  # fallback variable
            open_stack.append((ln, var))

        # Detect NEXT statements
        elif ucode.startswith("NEXT"):
            m = re.match(r"NEXT\s+([A-Z][A-Z0-9\$]?)", ucode, re.I)
            var = m.group(1) if m else None

            if open_stack:
                # Match with last FOR
                for_ln, for_var = open_stack.pop()

                if var is None:
                    # Bare NEXT → fix to match FOR
                    fixed = f"NEXT {for_var}"
                    if code.strip() != fixed:
                        new.append((ln, fixed))
                        idx.actions.append(f"fix bare NEXT at {ln} → NEXT {for_var}")
                        idx.line_to_code[ln] = fixed
                elif var != for_var:
                    # Mismatched NEXT var → fix
                    fixed = f"NEXT {for_var}"
                    new.append((ln, fixed))
                    idx.actions.append(f"fix NEXT {var} at {ln} → NEXT {for_var}")
                    idx.line_to_code[ln] = fixed
            else:
                # NEXT without FOR → insert dummy FOR before it
                insert_ln = ln - 1
                while insert_ln in idx.line_set:
                    insert_ln -= 1
                dummy_var = var or "I"
                new.append((insert_ln, f"FOR {dummy_var} = 0 TO 0"))
                idx.actions.append(f"insert dummy FOR {dummy_var} before NEXT at {ln}")
                idx.line_set.add(insert_ln)
                idx.line_to_code[insert_ln] = f"FOR {dummy_var} = 0 TO 0"

    # Step 2: Close any remaining FOR loops
    # Insert an UNNUMBERED "NEXT <var>" immediately after the FOR line.
    # (We don’t add a line number for the inserted NEXT.)
    if open_stack:
        # To keep minimal changes to the rest of the pipeline, we directly insert
        # into idx.lines here. (We still return 'new' for earlier fixes.)
        # Note: Later sorts place unnumbered lines after numbered ones, so NEXT
        # will still be *after* its FOR in program order, not at the beginning.
        for for_ln, var in open_stack:
            # Find the position of the FOR in the current ordered list
            for_pos = next(i for i, (ln, _) in enumerate(idx.lines) if ln == for_ln)
            idx.lines.insert(for_pos + 1, (-1, f"NEXT {var}"))
            idx.actions.append(f"insert missing NEXT {var} after FOR {for_ln} (unnumbered)")


    return new
def sparsify_line_numbers(idx: ProgramIndex) -> None:
    """
    Keep a line number only if it is an explicit jump target.
    All other lines are made unnumbered (ln = -1).
    """
    keep: Set[int] = set(idx.explicit_targets)
    new_lines: List[Tuple[int, str]] = []
    for ln, code in idx.lines:
        if ln >= 0 and ln not in keep:
            new_lines.append((-1, code))      # drop numbering on non-targets
        else:
            new_lines.append((ln, code))      # preserve explicit targets (and unnumbered lines)
    idx.lines = new_lines


def ensure_targets_exist_and_return(idx: ProgramIndex) -> List[Tuple[int, str]]:
    """
    For all GOTO/GOSUB (and IF/ON forms) targets:
      - If the target line doesn't exist, create it at the exact target number as a harmless label:
            N REM TARGET N
      - If the target is a GOSUB, ensure there's a RETURN immediately after it.
    """
    new: List[Tuple[int, str]] = []

    # Build target -> callers map so we know which targets exist
    target_callers: Dict[int, List[int]] = {}
    for caller, targets in {**idx.goto_targets, **idx.gosub_targets}.items():
        for t in targets:
            target_callers.setdefault(t, []).append(caller)

    # Create exact-number targets if missing (use REM label, not LET)
    for target in sorted(idx.explicit_targets):
        if target not in idx.line_set:
            new.append((target, f"REM TARGET {target}"))
            idx.actions.append(f"insert exact target {target}")
            idx.line_set.add(target)
            idx.line_to_code[target] = f"REM TARGET {target}"

    # Ensure RETURN after each GOSUB target
    for _, targets in idx.gosub_targets.items():
        for t in targets:
            if t in idx.line_set:
                code = idx.line_to_code.get(t, "").strip().upper()
                # We don't force the target line content; we only ensure a RETURN *after* it.
                insert_ln = t + 1
                while insert_ln in idx.line_set:
                    insert_ln += 1
                new.append((insert_ln, "RETURN"))
                idx.actions.append(f"insert RETURN at {insert_ln} for GOSUB target {t}")
                idx.line_set.add(insert_ln)
                idx.line_to_code[insert_ln] = "RETURN"

    return new



def rewrite_target_number(idx: ProgramIndex, old: int, new: int) -> None:
    """Rewrite all occurrences of line number 'old' (as a target) to 'new' in GOTO/GOSUB/ON/IF THEN."""
    # Update explicit_targets set
    if old in idx.explicit_targets:
        idx.explicit_targets.remove(old)
        idx.explicit_targets.add(new)
    updated_lines = []
    for ln, code in idx.lines:
        # Replace whole-number tokens only
        def repl(m):
            num = int(m.group(0))
            return str(new) if num == old else m.group(0)
        new_code = re.sub(r"\b\d+\b", repl, code)
        if new_code != code:
            idx.actions.append(f"rewrite target in line {ln}: {code!r} -> {new_code!r}")
            code = new_code
            idx.line_to_code[ln] = code
        updated_lines.append((ln, code))
    idx.lines = updated_lines


def scan_program_enhanced(idx: ProgramIndex) -> None:
    """Enhanced scanning with better variable usage tracking"""

    # Track variable usage by line number
    idx.var_usage_by_line = defaultdict(list)  # line_num -> list of variables used
    idx.var_def_by_line = defaultdict(list)  # line_num -> list of variables defined

    for ln, code in idx.lines:
        if ln < 0:  # Skip non-numbered lines
            continue

        up = code.strip().upper()
        current_line_vars_used = set()
        current_line_vars_defined = set()

        # ... [existing scanning logic] ...

        # Enhanced: Track exactly where variables are used/defined
        for v in tokenize_expr_vars(code):
            if v.upper() not in RESERVED and v.upper() not in BUILTINS:
                current_line_vars_used.add(v)
                idx.var_usage_lines[v].append(ln)

        # Track definitions more precisely
        if up.startswith("LET ") and "=" in code:
            lhs, rhs = code.split("=", 1)
            var = lhs.split(None, 1)[1].strip() if " " in lhs else lhs.strip()[3:].strip()
            if is_var_token(var):
                current_line_vars_defined.add(var)
                idx.var_def_lines[var].append(ln)

        # Store per-line usage
        idx.var_usage_by_line[ln].extend(current_line_vars_used)
        idx.var_def_by_line[ln].extend(current_line_vars_defined)


def validate_variable_placement(idx: ProgramIndex) -> List[str]:
    """Validate that no variable is used before being defined"""
    errors = []

    for var in idx.used:
        if var not in idx.defined:
            continue  # Will be handled by header definition

        first_def = min(idx.var_def_lines.get(var, [99999]))
        first_use = min(idx.var_usage_lines.get(var, [99999]))

        if first_use < first_def:
            errors.append(f"Variable {var} used at line {first_use} but defined at line {first_def}")

    return errors
# -----------------------------
# Main entry
# -----------------------------

def postprocess_and_verify_basic_file(file_path: str) -> Dict:
    with open(file_path, "r") as f:
        src = f.read()

    idx = parse_program(src)
    scan_program(idx)

    added: List[Tuple[int, str]] = []

    # -----------------------------
    # PHASE 1: Structural fixes
    # -----------------------------
    # 1) Fix GOTO/GOSUB targets first (this may create new lines)
    added += ensure_targets_exist_and_return(idx)

    # 2) DATA before each READ (if none above that READ)
    added += ensure_data_before_read(idx)
    # 3) Balance FOR/NEXT loops
    added += ensure_loops_balanced(idx)
    # 4) Ensure valid PRINTs
    added += ensure_valid_prints(idx)

    # Apply structural changes now
    if added:
        idx.lines.extend(added)
        idx.lines = sorted(idx.lines, key=lambda p: (p[0] < 0, p[0]))
        # Re-scan to catch any new variables from added lines
        idx = parse_program('\n'.join(
            f"{ln} {code}" if ln >= 0 else code
            for ln, code in idx.lines
        ))
        scan_program(idx)

    # -----------------------------
    # PHASE 2: Variable definitions
    # -----------------------------
    # Define all missing variables at the beginning (header)
    header_defs = ensure_missing_vars_at_header(idx)

    if header_defs:
        idx.lines.extend(header_defs)
        idx.lines = sorted(idx.lines, key=lambda p: (p[0] < 0, p[0]))

    # -----------------------------
    # Dedupe safeguard
    # -----------------------------
    seen = {}
    others = []
    for ln, code in idx.lines:
        if ln >= 0:
            seen[ln] = code  # last definition wins
        else:
            others.append((ln, code))
    idx.lines = sorted(seen.items(), key=lambda p: p[0]) + others

    # -----------------------------
    # Rebuild text file
    # -----------------------------
    out_lines = []
    for ln, code in idx.lines:
        if ln >= 0:
            out_lines.append(f"{ln} {code}\n")
        else:
            out_lines.append(code + "\n")

    with open(file_path, "w") as f:
        f.writelines(out_lines)

    # -----------------------------
    # Build verification report
    # -----------------------------
    report = {
        "file": file_path,
        "defined_count": len(idx.defined),
        "used_count": len(idx.used),
        "missing_defined_now": sorted((idx.used - idx.defined) - idx.loop_vars),
        "had_read": bool(idx.read_vars),
        "had_data": idx.has_any_data or any(l for l in (added + header_defs) if l[1].startswith("DATA")),
        "targets_ok": True,
        "actions": idx.actions,
        "added_lines_count": len(added) + len(header_defs),
        "header_definitions_added": len(header_defs),
        "tick_passed": (len(added) + len(header_defs)) == 0,
    }
    return report

