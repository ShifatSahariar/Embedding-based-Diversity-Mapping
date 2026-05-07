
import re
import glob
import shutil
from openai import OpenAI
import os, logging

def get_fandango_executable():
    """
    Return the most reliable Fandango executable path.
    Priority:
      1. User-defined env variable FANDANGO_BIN
      2. Base Anaconda install (/opt/anaconda3/bin/fandango)
      3. Current environment version (fallback)
    """
    env_path = shutil.which("fandango")
    base_path = "/opt/anaconda3/bin/fandango"

    # If base version exists, prefer it unless overridden
    if os.path.exists(os.environ.get("FANDANGO_BIN", base_path)):
        return os.environ.get("FANDANGO_BIN", base_path)
    elif env_path:
        return env_path
    else:
        raise FileNotFoundError("Fandango executable not found in PATH.")

def _is_fandango_installed():
    """
    Check whether Fandango fuzzer is installed and available.
    """
    fandango_path = shutil.which("fandango")
    if fandango_path:
        print(f"[OK] Fandango detected at: {fandango_path}")
        return True
    print("\n[WARN] Fandango not found in PATH.")
    print("To install it, follow the official guide:")
    print("👉 https://fandango-fuzzer.github.io/Setup.html")
    print("Or install directly from PyPI:")
    print("    pip install fandango-fuzzer\n")
    return False

def _short_tool_name(tool_name: str) -> str:
    return {
        'fuzzingbook': 'fuzz',
        'fandango': 'fan',
        'isla': 'isla',
        'openai': 'openai'
    }.get(tool_name, tool_name[:4])

def _short_config_name(config_name: str) -> str:
    if not config_name:
        return "cfg"
    s = config_name.lower()
    s = s.replace("constraints", "con")
    s = s.replace("no_constraints", "no_con")
    s = s.replace("without_constraints", "no_con")
    s = s.replace("probabilistic", "prob")
    s = s.replace("equal_prob", "equal")
    s = s.replace("with_grammar", "gram")
    s = s.replace("without_grammar", "no_gram")
    return s

def rename_isla_outputs(output_dir: str, config_name: str):
    """
    Rename raw ISLA-generated files (0.txt, 1.txt, 2.txt, ...) in a given directory
    to canonical names like isla_con_1.txt or isla_no_con_1.txt.

    Args:
        output_dir (str): Path where ISLA outputs were generated.
        config_name (str): The ISLA configuration name (used to infer 'con' or 'no_con').
    """
    # --- Identify raw ISLA output files ---
    pattern = os.path.join(output_dir, "*.txt")
    generated_files = [
        f for f in glob.glob(pattern)
        if re.match(r".*[\\/][0-9]+\.txt$", f)  # strict numeric filename pattern
    ]
    generated_files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))

    if not generated_files:
        print(f"[WARN] No ISLA raw output files (0.txt, 1.txt, ...) found in {output_dir}")
        return

    # --- Short tool/config naming ---
    short_tool = "isla"
    short_cfg = "con" if "no" not in config_name.lower() and "without" not in config_name.lower() else "no_con"

    # --- Determine starting index (if previous ISLA files exist) ---
    existing_pattern = os.path.join(output_dir, f"{short_tool}_{short_cfg}_*.txt")
    existing = glob.glob(existing_pattern)
    start_index = 1
    if existing:
        nums = []
        for p in existing:
            name = os.path.basename(p)
            parts = name.rsplit("_", 1)
            if len(parts) == 2 and parts[1].split(".", 1)[0].isdigit():
                nums.append(int(parts[1].split(".", 1)[0]))
        if nums:
            start_index = max(nums) + 1

    # --- Rename only numeric ISLA files ---
    for i, src in enumerate(generated_files, start=start_index):
        new_name = f"{short_tool}_{short_cfg}_{i}.txt"
        dst = os.path.join(output_dir, new_name)
        shutil.move(src, dst)

    print(f"[ISLA] ✅ Renamed {len(generated_files)} raw ISLA files → {output_dir}")


def generate_and_save_inputs(fuzzer, num_to_generate, output_dir,
                             sut_program, gen_config, tool_name=None, config_name=None):
    """
    Generates test inputs and saves them into individual files.
    Handles EOF markers if required and encodes tool/config in filename.
    """

    sentences_per_file = gen_config.get('sentences_per_file', 1)
    add_eof = gen_config.get('add_eof_marker', False)

    # Map program -> EOF marker
    eof_marker = None
    if add_eof:
        eof_marker = {
            'calc': 'exit',
            'basic': 'bye'
        }.get(sut_program.lower(), None)

    # Derive compact tool + config prefixes for filenames
    short_tool = {
        'fuzzingbook': 'fuzz',
        'fandango': 'fan',
        'isla': 'isla',
        'openai': 'openai'
    }.get(tool_name, tool_name[:4] if tool_name else "tool")

    short_cfg = ""
    if config_name:
        short_cfg = config_name \
            .replace("constraints", "con") \
            .replace("no_constraints", "no_con") \
            .replace("probabilistic", "prob") \
            .replace("equal_prob", "equal") \
            .replace("with_grammar", "gram") \
            .replace("without_grammar", "no_gram")

    # Generate and save files
    for i in range(num_to_generate):
        # unified filename format
        file_name = f"{short_tool}_{short_cfg}_{i + 1}.txt"
        file_path = os.path.join(output_dir, file_name)

        with open(file_path, 'w') as f:
            for _ in range(sentences_per_file):
                f.write(fuzzer.fuzz() + "\n")
            if eof_marker:
                f.write(f"{eof_marker}\n")

    print(f"[{tool_name.upper()}] Saved {num_to_generate} files → {output_dir}")




def _init_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error(
            "\n[OPENAI] ❌ Missing API key.\n"
            "Please set it using:\n"
            "   export OPENAI_API_KEY='your_api_key_here'\n"
            "or in Windows PowerShell:\n"
            "   setx OPENAI_API_KEY 'your_api_key_here'\n"
            "→ Required to generate inputs using GPT-4.1."
        )
        return None

    try:
        client = OpenAI(api_key=api_key)
        logging.info("[OPENAI] ✅ API key detected. Client initialized successfully.")
        return client
    except Exception as e:
        logging.error(f"[OPENAI] ❌ Failed to initialize client: {e}")
        return None

