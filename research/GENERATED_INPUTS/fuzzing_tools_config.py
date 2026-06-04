import glob
import os
import re
import subprocess

from fuzzingbook.Grammars import convert_ebnf_grammar, extend_grammar
from fuzzingbook.ProbabilisticGrammarFuzzer import ProbabilisticGrammarFuzzer

from GENERATED_INPUTS.input_gen_utils import _is_fandango_installed, _short_tool_name, _short_config_name, \
    generate_and_save_inputs, rename_isla_outputs, get_fandango_executable
from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.grammar_loader import get_gram
from GRAMMARS.EBNF_TOOLS.FUZZINGBOOK.probabilistic_grammar_sets import get_probabilistic_grammar

import shutil

print(f"Fandango path: {shutil.which('fandango')}")

def _generate_inputs_fandango(sut_program, config_name, num_inputs, output_dir,max_length,tool_name='fandango'):
    """
    Run the Fandango fuzzer for the given subject and configuration.
    """
    if not _is_fandango_installed():
        return

    sut_upper = sut_program.upper()
    base_grammar_dir = "GRAMMARS/EBNF_TOOLS/FANDANGO"
    subject_dir = os.path.join(base_grammar_dir, sut_upper)

    if any(x in config_name.lower() for x in ["no_constraints", "without_constraints", "no_con", "without"]):
        # --- No-constraints grammar ---
        grammar_file = os.path.join(subject_dir, f"{sut_program.lower()}_no_constraints.fan")
    else:
        # --- With constraints grammar ---
        grammar_file = os.path.join(subject_dir, f"{sut_program.lower()}_constraints.fan")

    # --- Check existence and fallback ---
    if not os.path.exists(grammar_file):
        print(f"[WARN] Grammar file not found: {grammar_file}")


    output_dir = os.path.abspath(output_dir)
    FANDANGO_BIN = get_fandango_executable()

    cmd = [
        FANDANGO_BIN, "fuzz",
        "-f", grammar_file,
        "-n", str(num_inputs),
        "-d", output_dir,
        "-N", max_length,
    ]

    print(f"[FANDANGO] Using grammar: {grammar_file}")
    print(f"[FANDANGO] Running command: {' '.join(cmd)}")

    # Create clean environment
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(FANDANGO_BIN) + ":" + env["PATH"]
    env.pop("PYTHONPATH", None)
    try:
        subprocess.run(cmd, env=env, check=True)
        generated = len(glob.glob(os.path.join(output_dir, "*.txt")))
        print(f"[FANDANGO]  Generated {generated} input(s) → {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Fandango failed for {sut_program} ({config_name}). Error: {e}")

    # Rename newly generated Fandango outputs (fandango-*.txt)
    pattern = os.path.join(output_dir, "fandango-*.txt")
    generated_files = sorted(glob.glob(pattern))
    if not generated_files:
        print(f"[WARN] No fandango-*.txt files found in {output_dir}")
        return
    short_tool = _short_tool_name(tool_name)
    short_cfg = _short_config_name(config_name)

    for i, src in enumerate(generated_files, start=1):
        new_name = f"{short_tool}_{short_cfg}_{i}.txt"
        dst = os.path.join(output_dir, new_name)
        shutil.move(src, dst)



def _generate_inputs_isla(sut_program, config_name, num_inputs, output_dir):
    """
    Run ISLA input generation for the given subject program and configuration.
    Automatically detects constraint / non-constraint grammars and renames
    the generated inputs into canonical naming (isla_con_1.txt, etc.).
    """
    # --- Verify ISLA installation ---
    isla_path = shutil.which("isla")
    if isla_path:
        print(f"[OK] ISLA detected at: {isla_path}")
    else:
        print("[ERROR] ISLA not found on PATH. Please install or activate correct environment.")
        print("See: https://rindphi.github.io/isla/")
        return

    sut_upper = sut_program.upper()
    base_grammar_dir = "GRAMMARS/EBNF_TOOLS/ISLA"
    subject_dir = os.path.join(base_grammar_dir, sut_upper)
    os.makedirs(output_dir, exist_ok=True)

    # --- Detecting grammar and constraint files ---
    if "no_constraint" in config_name.lower() or "without" in config_name.lower():
        # --- Without constraints ---
        bnf_file = os.path.join(subject_dir, f"{sut_program.lower()}_no_constraints.bnf")
        isla_file = None
    else:
        # --- With constraints ---
        bnf_file = os.path.join(subject_dir, f"{sut_program.lower()}_constraints.bnf")
        isla_file = os.path.join(subject_dir, "constraints.isla")

    # --- Check existence ---
    if not os.path.exists(bnf_file):
        print(f"[WARN] Missing grammar file: {bnf_file}")
        return
    if isla_file and not os.path.exists(isla_file):
        print(f"[WARN] Missing constraints file: {isla_file}")
        return

    # --- Build command ---
    if isla_file:
        cmd = [
            "isla", "solve",
            "-s", "1",
            "-n", str(num_inputs),
            bnf_file, isla_file,
            "-d", output_dir
        ]
    else:
        cmd = [
            "isla", "solve",
            "-s", "1",
            "-f", str(num_inputs),
            "-n", str(num_inputs),
            bnf_file,
            "-d", output_dir
        ]

    # --- Run info ---
    print(f"[ISLA] Running: {' '.join(cmd)}")
    os.system(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ISLA failed for {sut_program} ({config_name}). Error: {e}")
        return

    # Rename ISLA generated test cases from 0.txt,1.txt --> isla_no_con_1.txt
    rename_isla_outputs(output_dir, config_name)


def _generate_inputs_fuzzingbook(
    sut_program,
    config_name,
    num_inputs,
    file_gen_config,
    output_dir,
    fuzzer,
    tool_name
):
    """
    Generates and saves inputs for Fuzzingbook-based generation.
    The fuzzer is passed in (already configured).
    """
    if not fuzzer:
        print(f"[ERROR] Fuzzer not initialized for {sut_program} ({config_name})")
        return

    generate_and_save_inputs(
        fuzzer=fuzzer,
        num_to_generate=num_inputs,
        output_dir=output_dir,
        sut_program=sut_program,
        gen_config=file_gen_config,
        tool_name=tool_name,
        config_name=config_name
    )

def create_fuzzingbook_fuzzer(sut_program, tool, config_name):
    """
    Factory function to create a Fuzzingbook-based fuzzer for the given subject program.
    Supports multiple configurations such as 'probabilistic' and 'equal_prob'.
    """
    if tool != 'fuzzingbook':
        return None  # Guard early for clarity

    # Step 1: Load and prepare grammar
    ebnf_grammar = get_gram(grammar_type=sut_program)
    bnf_from_ebnf = convert_ebnf_grammar(ebnf_grammar)

    # Step 2: Select configuration
    if config_name == 'probabilistic':
        probabilistic_grammar = get_probabilistic_grammar(sut_program, bnf_from_ebnf)
        print(f"[FUZZINGBOOK] Using probabilistic grammar for {sut_program}")
        return ProbabilisticGrammarFuzzer(probabilistic_grammar)

    elif config_name == 'equal_prob':
        extended_grammar = extend_grammar(bnf_from_ebnf)
        print(f"[FUZZINGBOOK] Using equal-probability grammar for {sut_program}")
        return ProbabilisticGrammarFuzzer(extended_grammar)

    else:
        print(f"[WARN] Unknown Fuzzingbook config: {config_name}")
        return None

