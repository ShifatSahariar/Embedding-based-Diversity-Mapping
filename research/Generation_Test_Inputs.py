"""
Standalone script to generate test inputs using grammar-based tools
(e.g., Fuzzingbook, Fandango, ISLA) for compiler/interpreter subjects.
Supports:
- IDE execution (via pipeline_config below)
- CLI execution with arguments: subject, tools, and number of runs
"""

import argparse
import multiprocessing
import platform

from GENERATED_INPUTS.input_generator import generate_all_inputs
from Helper_Functions.HelperFunctions import setup_logger, clean_directories


# -------------------------------------------------------------------------
# DEFAULT CONFIGURATION (used when running from IDE)
# -------------------------------------------------------------------------
pipeline_config = {
    'subject_program': 'karatejs',       # Options: CALC | rhino | basic | karatejs
    'generate_inputs': True,
    'clean_previous_data': False,
    'num_inputs_per_tool': 3,  # how many input per tool we want to generate
    'num_random_runs': 10,

    # --- Input Generators Family ---
    'generators': [

        # -------------------------
        # FUZZINGBOOK Family
        # -------------------------
        {
            'tool': 'fuzzingbook',
            'config_name': 'probabilistic',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False
            }
        },
        {
            'tool': 'fuzzingbook',
            'config_name': 'equal_prob',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False
            }
        },
        #
        # # -------------------------
        # # FANDANGO Family
        # # -------------------------
        {
            'tool': 'fandango',
            'config_name': 'constraints',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False,
                'N': 2000  # - N is how many generation we want for fitness function
            }
        },
        {
            'tool': 'fandango',
            'config_name': 'no_constraints',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False,

            }
        },

        # -------------------------
        # ISLA Family
        # -------------------------
        {
            'tool': 'isla',
            'config_name': 'constraints',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False
            }
        },
        {
            'tool': 'isla',
            'config_name': 'no_constraints',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False
            }
        },

        # -------------------------
        # OPENAI / LLM Family
        # -------------------------
        {
            'tool': 'openai',
            'config_name': 'with_grammar',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False,
                'batch_size': 200
            }
        },
        {
            'tool': 'openai',
            'config_name': 'without_grammar',
            'file_gen_config': {
                'sentences_per_file': 1,
                'add_eof_marker': False,
                'batch_size': 200
            }
        }
    ]
}



# Helper: Override tools dynamically from CLI
# -------------------------------------------------------------------------
def filter_tools_from_cli(config, selected_tools):
    """
    If a user provides specific tools (comma-separated),
    keep only those from config['generators'].
    """
    if not selected_tools:
        return config  # use all

    selected_tools = [t.strip().lower() for t in selected_tools.split(',')]
    config['generators'] = [
        g for g in config['generators'] if g['tool'].lower() in selected_tools
    ]
    if not config['generators']:
        print(f"[WARN] No matching tools found for: {selected_tools}. Using all available.")
    else:
        print(f"[INFO] Selected tools for generation: {', '.join(selected_tools)}")
    return config


# -------------------------------------------------------------------------
# MAIN EXECUTION PIPELINE
# -------------------------------------------------------------------------
def main(args=None):
    # -------------------------------
    # 1. Parse CLI arguments
    # -------------------------------
    parser = argparse.ArgumentParser(
        description="Generate grammar-based test inputs for compilers/interpreters."
    )
    parser.add_argument("--subject", type=str, help="Subject program name (e.g., basic, CALC, rhino)")
    parser.add_argument("--tools", type=str, help="Comma-separated list of tools to use (e.g., fuzzingbook,fandango)")
    parser.add_argument("--num_inputs", type=int, help="Number of inputs to generate per tool")
    parser.add_argument("--runs", type=int, help="Number of random runs per tool", default=None)
    parser.add_argument("--clean", action="store_true", help="Clean previous result before generation")

    cli_args = parser.parse_args(args)

    # -------------------------------
    # 2. Merge CLI arguments into config
    # -------------------------------
    config = pipeline_config.copy()

    if cli_args.subject:
        config['subject_program'] = cli_args.subject.lower()
    if cli_args.num_inputs:
        config['num_inputs_per_tool'] = cli_args.num_inputs
    if cli_args.runs:
        config['num_random_runs'] = cli_args.runs

    if cli_args.clean:
        config['clean_previous_data'] = True

    # Filter only selected tools (if provided)
    config = filter_tools_from_cli(config, cli_args.tools)

    # -------------------------------
    # 3. Prepare environment
    # -------------------------------
    logger = setup_logger()
    subj = config['subject_program']
    logger.info(f"=== Starting input generation for: {subj.upper()} ===")

    if config.get('clean_previous_data', False):
        logger.info("Cleaning old generated input directories...")
        clean_directories(subj)
    else:
        logger.info("Keeping existing input directories...")

    # -------------------------------
    # 4. Generate Inputs
    # -------------------------------
    if config.get('generate_inputs', False):
        logger.info("Generating new test inputs...")
        generate_all_inputs(config)  ### ENTRY FUNCTION FOR INPUT GENERATION
    else:
        logger.info("Skipping input generation (flag is False).")

    # -------------------------------
    # 5. Finish
    # -------------------------------
    logger.info(f"Input generation finished for {subj.upper()}")
    logger.info(f"All generated result saved under ../../GENERATED_INPUTS/{subj.upper()}")


# -------------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------------
# python Generation_Test_Inputs.py --subject basic --tools fuzzingbook,fandango --runs 3
if __name__ == "__main__":
    system = platform.system()
    if system == "Windows":
        multiprocessing.set_start_method("spawn", force=True)
    else:
        multiprocessing.set_start_method("fork", force=True)
    print(f"Running on {system} with multiprocessing context:", multiprocessing.get_start_method())

    main()
