import logging
import os, json, math
import shutil
from typing import List, Dict, Any, Optional, Union
import openai

from GRAMMARS.LLM.PROMTS.prompt_builder import build_messages
from GENERATED_INPUTS.normalize_llm_inputs import split_and_cleanup

# ----------------------------
# Logging Setup
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("input_generation.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
MODEL_NAME = "gpt-4.1"

openai.api_key = ""

def generate_batch_auto_sized(
    compiler_name: str,
    grammar: Optional[Union[str, List[str]]] = None,
    desired_k: int = 1,
    avg_lines_per_program: int = 6,
    avg_chars_per_line: int = 22,
    context_window_tokens: int = 120_000,
    response_buffer_tokens: int = 40_000,
    max_k_per_call: int = 200,
    include_assistTemplate: bool = True,
    temperature: float = 0.4,
) -> List[Dict[str, Any]]:
    """
        Build prompt -> estimate feasible k -> call OpenAI -> return parsed tests.
        """
    # Rough token estimate (4 chars ≈ 1 token)
    avg_prog_tokens = math.ceil((avg_lines_per_program * avg_chars_per_line) / 4)
    per_test_cost = avg_prog_tokens + 40
    base_prompt_cost = 1000  # rough system+grammar overhead

    usable = context_window_tokens - response_buffer_tokens - base_prompt_cost
    k_feasible = max(1, min(max_k_per_call, usable // per_test_cost))
    k_final = min(desired_k, k_feasible)

    # Build the messages
    messages = build_messages(k_final, compiler_name, grammar, include_assistTemplate)

    resp = openai.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
    )

    raw = resp.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"[ERROR] Could not parse JSON: {e}\nRaw output:\n{raw}")

    tests = data.get("tests", [])
    if len(tests) != k_final:
        print(f"[WARN] Expected {k_final}, got {len(tests)} — using what we have.")

    return tests

# ----------------------------------------------------------
# 🚀 Main entry point
# ----------------------------------------------------------

def main():
    inputs_root_path = "generated_inputs"
    compiler_name = "karatejs"  # "basic", "CALC", or "rhino"

    # Clean up old results
    if os.path.exists(inputs_root_path):
        logging.info(f"Clearing old test cases from {inputs_root_path}...")
        shutil.rmtree(inputs_root_path)
    os.makedirs(inputs_root_path)

    # Load grammar (optional)
    with_grammar = False
    grammar_path = f"grammars/{compiler_name.lower()}_grammar.txt"
    SUT_grammar = None
    if with_grammar:
        SUT_grammar = open(grammar_path).read()
        logging.info(f"Loaded grammar for {compiler_name}.")

    else:
        logging.warning(f"No grammar provided for {compiler_name}; using freeform mode.")

    k_total = 1000
    hard_cap_per_call = 200
    all_tests = []
    batch_index = 0

    while len(all_tests) < k_total:
        remaining = k_total - len(all_tests)
        k_this_call = min(remaining, hard_cap_per_call)

        logging.info(f"[Batch {batch_index + 1}] Requesting {k_this_call} programs (remaining: {remaining})")

        try:
            batch_tests = generate_batch_auto_sized(
                compiler_name=compiler_name,
                grammar=SUT_grammar,
                desired_k=k_this_call,
                avg_lines_per_program=6,
                avg_chars_per_line=25,
                max_k_per_call=k_this_call,
                temperature=0.9,  # tuned for diversity + stability
            )
        except Exception as e:
            logging.error(f"Batch {batch_index + 1} failed: {e}", exc_info=True)
            break

        # Assign unique IDs
        offset = len(all_tests)
        for idx, tc in enumerate(batch_tests, start=1):
            tc["id"] = offset + idx
        all_tests.extend(batch_tests)

        logging.info(f"[Batch {batch_index + 1}] +{len(batch_tests)} (total {len(all_tests)}/{k_total})")
        batch_index += 1

        if not batch_tests:
            logging.warning("No tests returned; stopping early.")
            break

    # Save everything
    out_json = {"compiler": compiler_name, "tests": all_tests}
    out_path = f"{inputs_root_path}/all_{compiler_name}_inputs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(out_json, ensure_ascii=False, indent=2))

    logging.info(f"Saved {len(all_tests)} programs to {out_path}.")

if __name__ == "__main__":
    main()


    compiler_name = "karatejs"
    OUTPUT_DIR = "generated_inputs"
    JSON_PATH = os.path.join(OUTPUT_DIR, f"all_{compiler_name}_inputs.json")
    split_and_cleanup(json_path=JSON_PATH, output_dir=OUTPUT_DIR)
