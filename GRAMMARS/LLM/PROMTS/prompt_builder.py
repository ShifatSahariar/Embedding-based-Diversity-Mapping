from typing import Optional

from GRAMMARS.LLM.PROMTS.few_shot import build_assistant_fewshot

# ============================================================
# 🔧 Constraint Templates for Each Compiler / Language
# ============================================================
ASSIGNMENT_VALUE_DIVERSITY = """
Assignment/value diversity:
- When declaring variables with LET, diversify the right-hand side (RHS) while keeping types consistent with the grammar.
  • Numeric vars (e.g., LET A = ...): use numeric literals, arithmetic expressions, and numeric-returning functions:
    RND(x), INT(x), SIN(x), COS(x), TAN(x), ATN(x), SQR(x), ABS(x), LOG(x), SGN(x), MAX(x,y), MIN(x,y), VAL("123"), FRE
  • String vars (e.g., LET S$ = ...): use quoted strings and string-returning functions:
    STR$(n), CHR$(code), SPC$(k), TAB$(k), LEFT$(str,k), RIGHT$(str,k), MID$(str,i,k)
- Enforce type correctness: numeric vars receive numeric values; string vars receive string values.
- Mix literals, variable references, and function calls across the batch to maximize variety.
""".strip()
BASIC_RULES = f"""
Hard rules (must all pass):
1) ≤ 7 lines of executable code per program.
2) Define variables before use (LET statements).
3) PRINT only previously defined variables (no string literals/labels).
4) If GOSUB or GOTO appears: the target line number must exist. For GOSUB, a matching RETURN must exist.
5) FOR must have a matching NEXT.
6) If READ is present: DATA appears earlier; types/count/order strictly match variables in READ (numeric vars read numeric constants; string vars read quoted strings).
7) The program ends with BYE on its own final line.
8) Avoid infinite loops and undefined labels.

Diversity objectives:
- Cover constructs broadly: arithmetic, IF (with valid jump targets), FOR/NEXT, READ/DATA (numeric and string), GOTO, GOSUB/RETURN, simple nesting (e.g., IF inside a loop), and varied line numbering.
- Vary identifiers, line-number strides, and loop ranges; avoid near-duplicate programs.

{ASSIGNMENT_VALUE_DIVERSITY}
""".strip()

CALC_RULES = (
    "- Follow valid arithmetic expression syntax.\n"
    "- Each expression must be evaluable by the CALC interpreter.\n"
    "- Ensure balanced parentheses and valid operators.\n"
    "- Use numeric constants and variables (x, y, z, etc.).\n"
    "- Avoid division by zero.\n"
    "- Generate concise expressions (3–10 tokens).\n"
    "Diversity objectives:\n"
    "- Include addition, subtraction, multiplication, division, and nested parentheses.\n"
)

RHINO_RULES = (
    "- Follow valid ECMAScript / Rhino syntax.\n"
    "- Each program must compile and run under the Rhino JavaScript engine.\n"
    "- Always declare and initialize every identifier (numeric, string, array, object, function) before use.\n"
    "- Ensure numeric and string variables are used consistently with their types (no undefined references).\n"
    "- Maintain balanced parentheses, braces, and quotation marks.\n"
    "- print() statements may appear occasionally, but not in every program.\n"
    "- Prefer concise, self-contained programs (3–7 lines total).\n"
    "- Include a mix of statement types: arithmetic, conditionals (if/else), loops (for/while), print statements, and function calls.\n"
    "- Use arrays or objects only after proper initialization (e.g., var arr=[1,2]; arr[0]; var obj={x:1}; print(obj.x);).\n"
    "- return statements are valid only inside function bodies.\n"
    "- Throw statements (throw new Error(...)) should appear only inside try/catch blocks or functions — not standalone.\n"
    "- Avoid undefined variables in any expression, condition, or print statement.\n"
    "- Prefer expressions that involve declared identifiers rather than only literals.\n"
    "- Ensure catch parameters and function parameters are locally scoped and used meaningfully.\n"
    "- Avoid overly deep nesting or infinite loops.\n"
    "Diversity objectives:\n"
    "- Encourage combinations of variable declarations, arithmetic operations, control flow (if/for/while), try/catch, arrays, objects, and short functions.\n"
)


# ============================================================
# Core Function: Dynamic Constraint Selector
# ============================================================

def get_compiler_constraints(compiler_name: str) -> str:
    """
    Return a natural-language description of semantic and syntactic constraints
    for the given compiler, including a dynamic introductory line.
    """

    intro_line = {
        "basic": "You are a BASIC input generator."
                 " Dont include line numbers for the Statements unless RETURN statement should begin with its line number (e.g., '40 RETURN').\n"
,
        "CALC": "You are a CALC input generator.",
        "rhino": "You are a JavaScript input generator."
    }.get(compiler_name.lower(), f"You are an input generator for {compiler_name}.")

    core_rules = {
        "basic": BASIC_RULES,
        "CALC": CALC_RULES,
        "rhino": RHINO_RULES
    }.get(compiler_name.lower(), "- Follow valid syntax.\n")

    return f"{intro_line}\n{core_rules}"

# ============================================================
# 🧩 Message Construction for OpenAI Calls
# ============================================================

def build_messages(k: int, compiler_name: str, grammar: Optional[str], include_assistTemplate: bool) -> list:
    """
        Build chat messages for OpenAI input generation with grammar or without grammar.
        Injects compiler-specific constraints (via get_compiler_constraints) into the system message.
        Ensures the system message explicitly mentions JSON for response_format="json_object".
        """
    # --- Compiler-specific constraints ---
    compiler_constraints = get_compiler_constraints(compiler_name)

    # --- SYSTEM MESSAGE (with constraints added) ---
    system_message = {
        "role": "system",
        "content": (
            f"You are an expert program input generator for the '{compiler_name.upper()}' interpreter/compiler.\n"
            f"Generate {k} unique, syntactically valid programs using the provided grammar if given.\n"
            "Each program must follow the semantics of the target language (e.g., logical expressions, "
            "valid variable usage, matching brackets, and consistent return statements).\n"
            "\n"
            "Language-specific constraints:\n"
            f"{compiler_constraints}\n"
            "\n"
            "Output format requirement:\n"
            "Respond strictly in **valid JSON** format with the following structure:\n"
            "{\n"
            '  \"compiler\": \"<compiler_name>\",\n'
            '  \"tests\": [\n'
            '     {\"id\": 1, \"program\": \"<single program as string>\"},\n'
            '     {\"id\": 2, \"program\": \"<next program>\"}\n'
            "  ]\n"
            "}\n"
            "Do not include comments or explanations outside the JSON.\n"
        )
    }

    # --- USER MESSAGE ---
    user_content = f"Generate exactly {k} valid {compiler_name.upper()} programs.\n"
    if grammar:
        user_content += "\nFollow this grammar strictly:\n" + grammar
    else:
        user_content += "\nNo grammar provided — use your own knowledge to generate realistic programs."

    user_message = {"role": "user", "content": user_content}

    # --- 3️⃣ FEWSHOT ASSISTANT TEMPLATE (OPTIONAL EXAMPLES) ---
    messages = [system_message, user_message]
    if include_assistTemplate:
        fewshot = build_assistant_fewshot(compiler_name)
        messages.append({"role": "assistant", "content": fewshot})

    return messages
