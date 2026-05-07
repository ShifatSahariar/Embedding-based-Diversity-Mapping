
import os, json, math
import re
from typing import Optional, Union, List, Dict, Any
from GENERATED_INPUTS.input_gen_utils import _init_openai_client
from GRAMMARS.LLM.PROMTS.prompt_builder import build_messages
from GENERATED_INPUTS.normalize_llm_inputs import split_and_cleanup



def _generate_inputs_openai(sut_program: str, config_name: str, num_inputs: int, output_dir: str,batch_size):
    """
    Generate test inputs using OpenAI GPT-based input generation.
    """
    MODEL_NAME = "gpt-4.1"
    client = _init_openai_client()
    if client is None:
        print("[OPENAI] Skipping input generation — API key missing or invalid.")
        return
    os.makedirs(output_dir, exist_ok=True)
    compiler_name = sut_program.lower()
    use_grammar = "with" in config_name.lower() and "without" not in config_name.lower()

    # -------------------------------
    # Load grammar if required
    # -------------------------------
    grammar_path = f"GRAMMARS/LLM/grammars/{compiler_name}_grammar.txt"
    grammar_text = None
    if use_grammar and os.path.exists(grammar_path):
        with open(grammar_path, "r", encoding="utf-8") as f:
            grammar_text = f.read()
        print(f"[OPENAI] Loaded grammar for {compiler_name}.")
    else:
        print(f"[OPENAI] No grammar provided for {compiler_name} ({config_name}). Using freeform generation.")

    # -------------------------------
    # Parameters
    # -------------------------------
    total_k = num_inputs
    batch_size = batch_size
    all_tests = []
    batch_idx = 0

    while len(all_tests) < total_k:
        remaining = total_k - len(all_tests)
        k_this_call = min(remaining, batch_size)

        print(f"[OPENAI] Batch {batch_idx+1}: Requesting {k_this_call} programs...")

        try:
            tests = _generate_batch_auto_sized(
                compiler_name=compiler_name,
                grammar=grammar_text,
                desired_k=k_this_call,
                model_name =MODEL_NAME,
                client=client
            )
        except Exception as e:
            print(f"[ERROR] OpenAI generation failed in batch {batch_idx+1}: {e}")
            break

        # Assign unique IDs
        offset = len(all_tests)
        for i, t in enumerate(tests, start=1):
            t["id"] = offset + i
        all_tests.extend(tests)
        batch_idx += 1

    # -------------------------------
    # Save as JSON
    # -------------------------------
    json_path = os.path.join(output_dir, f"all_{compiler_name}_{config_name}_inputs.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"compiler": compiler_name, "tests": all_tests}, f, indent=2, ensure_ascii=False)

    print(f"[OPENAI] Saved {len(all_tests)} programs → {json_path}")

    # -------------------------------
    # Split into .txt files
    # -------------------------------
    if config_name.lower() == "with_grammar":
        prefix = "openai_gram"
    elif config_name.lower() == "without_grammar":
        prefix = "openai_no_gram"
    else:
        prefix = f"openai_{config_name.lower()}"

    split_and_cleanup(json_path=json_path, output_dir=output_dir, prefix=prefix)

    print(f"[OPENAI] Split JSON into .txt inputs under {output_dir}")


def _generate_batch_auto_sized(
    compiler_name: str,
    grammar: Optional[Union[str, List[str]]] = None,
    desired_k: int = 1,
    model_name: Optional[str] = None,
    client: Optional[Any] = None,
    avg_lines_per_program: int = 6,
    avg_chars_per_line: int = 25,
    context_window_tokens: int = 120_000,
    response_buffer_tokens: int = 40_000,
    max_k_per_call: int = 200,
    temperature: float = 0.8,
) -> List[Dict[str, Any]]:

    if client is None or model_name is None:
        raise ValueError("[OPENAI] Missing client or model name for generation.")

    avg_prog_tokens = math.ceil((avg_lines_per_program * avg_chars_per_line) / 4)
    per_test_cost = avg_prog_tokens + 40
    base_prompt_cost = 1000
    usable = context_window_tokens - response_buffer_tokens - base_prompt_cost
    k_feasible = max(1, min(max_k_per_call, usable // per_test_cost))
    k_final = min(desired_k, k_feasible)

    messages = build_messages(k_final, compiler_name, grammar, include_assistTemplate=True)

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)

    return data.get("tests", [])

