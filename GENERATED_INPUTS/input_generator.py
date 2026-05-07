"""
input generation for a given subject program using multiple
input generation tools (e.g., Fuzzingbook, Fandango, ISLA, LLM-based).

GENERATED_INPUTS/
└── BASIC/
    ├── input_pool_by_run_1/
    │   ├── fuzz_prob_1.txt
    │   ├── fuzz_equal_1.txt
    │   ├── fan_con_1.txt
    │   ├── fan_no_con_1.txt
    │   ├── isla_con_1.txt
    │   ├── isla_no_con_1.txt
    │   ├── openai_gram_1.txt
    │   └── openai_no_gram_1.txt
    ├── input_pool_by_run_2/
    │   ├── fuzz_prob_1.txt ...

"""

from concurrent.futures import ThreadPoolExecutor as ProcessPoolExecutor, as_completed

import shutil
from GENERATED_INPUTS.fuzzing_tools_config import create_fuzzingbook_fuzzer, _generate_inputs_fuzzingbook, \
    _generate_inputs_fandango, _generate_inputs_isla
from GENERATED_INPUTS.llm_based_input_generator import _generate_inputs_openai
def _run_generator_for_tool(sut_program, tool, config_name, num_inputs, file_gen_config, run_dir):
    """Worker: runs a single generator tool safely in parallel."""
    grammar_available = _check_grammar_availability(
        sut_program=sut_program,
        tool=tool,
        config_name=config_name
    )
    if not grammar_available:
        print(f"[SKIP] {tool.upper()} ({config_name}) – grammar missing.")
        return

    print(f"--- [{tool.upper()} - {config_name}] Generating {num_inputs} inputs in {run_dir} ---")

    if tool == 'fuzzingbook':
        fuzzer = create_fuzzingbook_fuzzer(sut_program, tool, config_name)
        if fuzzer:
            _generate_inputs_fuzzingbook(
                sut_program=sut_program,
                config_name=config_name,
                num_inputs=num_inputs,
                file_gen_config=file_gen_config,
                output_dir=run_dir,
                fuzzer=fuzzer,
                tool_name=tool
            )

    elif tool == 'fandango':
        max_length = str(file_gen_config.get('N', 2000))
        _generate_inputs_fandango(
            sut_program=sut_program,
            config_name=config_name,
            num_inputs=num_inputs,
            output_dir=run_dir,
            max_length=max_length
        )

    elif tool == 'isla':
        _generate_inputs_isla(
            sut_program=sut_program,
            config_name=config_name,
            num_inputs=num_inputs,
            output_dir=run_dir
        )

    elif tool == 'openai':
        _generate_inputs_openai(
            sut_program=sut_program,
            config_name=config_name,
            num_inputs=num_inputs,
            output_dir=run_dir,
            batch_size=int(file_gen_config.get('batch_size', 200))
        )

    else:
        print(f"[WARN] Unsupported tool: {tool}")


def generate_all_inputs(config):
    """
    Generate inputs for each tool across multiple random runs.

    Fixes:
    - Prevents duplicate generator loops per run.
    - Groups all tool generations inside each run folder.
    - Ensures each tool/config combination executes once per run.
    """

    num_inputs_global = config.get('num_inputs_per_tool', None)

    if not config.get('generate_inputs', False):
        print("[INFO] Input generation skipped (flag is False).")
        return

    sut_program = config['subject_program']
    num_random_runs = config.get('num_random_runs', 1)

    # =========================
    # Clean base directory (optional)
    # =========================
    base_dir = f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{sut_program.upper()}"
    if config.get('clean_previous_data', False):
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        print(f"[CLEAN] Removed existing generated inputs for {sut_program}")
    os.makedirs(base_dir, exist_ok=True)

    # =========================
    # Outer loop = per-run organization
    # =========================
    for run_id in range(1, num_random_runs + 1):
        run_dir = os.path.join(base_dir, f"input_pool_by_run_{run_id}")
        os.makedirs(run_dir, exist_ok=True)
        print(f"\n=== Run {run_id}: Generating inputs for all tools (parallel mode) ===")

        generators = config.get('generators', [])

        # --- Parallel execution within each run ---
        max_workers = min(8, os.cpu_count())
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for gen_task in generators:
                tool = gen_task['tool'].lower()
                config_name = gen_task['config_name']
                num_inputs = num_inputs_global or gen_task.get('num_to_generate', 100)
                file_gen_config = gen_task['file_gen_config']

                # submit one generator task
                futures[executor.submit(
                    _run_generator_for_tool,
                    sut_program, tool, config_name, num_inputs, file_gen_config, run_dir
                )] = (tool, config_name)

            # --- Collect results ---
            for future in as_completed(futures):
                tool, config_name = futures[future]
                try:
                    future.result()
                    print(f"[DONE]  {tool.upper()} ({config_name}) completed")
                except Exception as e:
                    print(f"[FAIL] {tool.upper()} ({config_name}) failed: {e}")

    print(f"\n All input generations completed for {sut_program.lower()}.")
    print(f"Outputs saved under: {base_dir}")


# -------------------------------------------------------------------------
# 📘 Grammar Availability Checker (Updated for your structure)
# -------------------------------------------------------------------------

import os
import glob

def _check_grammar_availability(sut_program, tool, config_name=None):
    """
    Dynamically checks if grammar files are available for a given tool and subject program.
    Handles different tool structures and extensions.
    """
    base_dir = "GRAMMARS/EBNF_TOOLS"
    sut_upper = sut_program.upper()
    tool_upper = tool.upper()

    # ----------------------------
    # FUZZINGBOOK
    # ----------------------------
    if tool == "fuzzingbook":
        grammar_dir = os.path.join(base_dir, "FUZZINGBOOK", sut_upper)
        patterns = ["*.py"]
        found = any(
            glob.glob(os.path.join(grammar_dir, pattern))
            for pattern in patterns
        )
        if found:
            print(f"[OK] Grammar found for {tool_upper} → {grammar_dir}")
            return True
        print(f"[WARN] Grammar folder missing for {tool_upper} → {grammar_dir}")
        return False

    # ----------------------------
    # FANDANGO
    # ----------------------------
    elif tool == "fandango":
        grammar_dir = os.path.join(base_dir, "FANDANGO", sut_upper)
        patterns = ["*.fan"]
        found = any(
            glob.glob(os.path.join(grammar_dir, pattern))
            for pattern in patterns
        )
        if found:
            print(f"[OK] Grammar found for {tool_upper} → {grammar_dir}")
            return True
        print(f"[WARN] Grammar folder missing for {tool_upper} → {grammar_dir}")
        return False

    # ----------------------------
    # ISLA
    # ----------------------------
    elif tool == "isla":
        grammar_dir = os.path.join(base_dir, "ISLA", sut_upper)
        patterns = ["*.isla", "*.bnf"]
        found = any(
            glob.glob(os.path.join(grammar_dir, "**", pattern), recursive=True)
            for pattern in patterns
        )
        if found:
            print(f"[OK] Grammar found for {tool_upper} → {grammar_dir}")
            return True
        print(f"[WARN] Grammar folder missing for {tool_upper} → {grammar_dir}")
        return False

    # ----------------------------
    # OPENAI / LLM FAMILY
    # ----------------------------
    elif tool in ["openai", "llm"]:
        grammar_dir = os.path.join("GRAMMARS/LLM/grammars")
        patterns = [f"{sut_program.lower()}_grammar.txt"]
        found = any(
            os.path.exists(os.path.join(grammar_dir, pattern))
            for pattern in patterns
        )
        if found:
            print(f"[OK] Grammar prompt found for {tool_upper} → {grammar_dir}")
            return True
        print(f"[WARN] Grammar prompt missing for {tool_upper} → {grammar_dir}")
        return False

    # ----------------------------
    # UNKNOWN TOOL
    # ----------------------------
    else:
        print(f"[WARN] Unknown tool: {tool}")
        return False


