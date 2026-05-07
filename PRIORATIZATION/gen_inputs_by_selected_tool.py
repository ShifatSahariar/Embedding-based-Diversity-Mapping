import os
import shutil
from pathlib import Path

from GENERATED_INPUTS.input_generator import _run_generator_for_tool


def simple_generate_inputs(
    subject_program: str,
    tool: str,
    config_name: str,
    num_inputs: int = 1000,
    base_dir: str = "CALC"
):
    """

    Parameters:
        subject_program: str  - e.g. 'calc', 'basic', 'rhino'
        tool: str              - e.g. 'fuzzingbook', 'fandango', 'isla', 'openai'
        config_name: str       - e.g. 'equal_prob', 'no_constraints'
        num_inputs: int        - number of inputs to generate
        base_dir: str          - directory to store generated inputs
    """

    # === Create final output directory (flat structure) ===
    output_dir = Path(base_dir)
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] Generating {num_inputs} inputs for {subject_program.upper()} "
          f"using {tool.upper()} ({config_name})")
    print(f"[INFO] Saving directly to: {output_dir.resolve()}")

    # --- define file generation config per tool ---
    if tool == "fuzzingbook":
        file_gen_config = {"sentences_per_file": 1, "add_eof_marker": True}
    elif tool == "fandango":
        file_gen_config = {"sentences_per_file": 1, "add_eof_marker": False, "N": 2000}
    elif tool == "isla":
        file_gen_config = {"sentences_per_file": 1, "add_eof_marker": False}
    elif tool == "openai":
        file_gen_config = {"sentences_per_file": 1, "add_eof_marker": False, "batch_size": 200}
    else:
        raise ValueError(f"Unknown tool: {tool}")

    # --- Run the generation task directly ---
    _run_generator_for_tool(
        sut_program=subject_program,
        tool=tool,
        config_name=config_name,
        num_inputs=num_inputs,
        file_gen_config=file_gen_config,
        run_dir=str(output_dir)   # reused param name but points directly to base dir
    )

    print(f"[DONE] Generated {num_inputs} inputs in: {output_dir.resolve()}")


# ----------------------------------------------------------------------
# Example Usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    subject_program ='calc'

    simple_generate_inputs(
        subject_program=subject_program,
        tool="fuzzingbook",
        config_name="equal_prob",
        num_inputs=1000,
        base_dir=f"../GENERATED_INPUTS/INPUT_PRIORITIZATION/{subject_program.upper()}"
    )
