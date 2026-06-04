import concurrent.futures
import glob
import re
import subprocess


from COVERAGE_REPORTS.Coverage_Reports import _graal_classpath
from Helper_Functions.HelperFunctions import extract_exception_type

from Helper_Functions.Mutation_Helping_Functions import replace_class_with_mutant, \
    restore_original_classes
from Helper_Functions.configs.coverage_configs import subject_program_config

from Helper_Functions.graaljs.jar_config import replace_mutant_in_jar, restore_original_jars, _build_graal_jar_index

SUT_FILTERS = {
    "BASIC": [
        "Type 'exit' to quit",
        "JavaBASIC Version 1.0",
        "Copyright (C) 1996 Chuck McManis. All Rights Reserved.",
    ],
    "RHINO": [
        "Rhino", "Mozilla", "js>", "JavaScript Engine",
    ],
    "CALC": [
        "Calc Interpreter", "Ready>", "MathLib Loaded",
    ],
}

def _norm_text(s: str) -> str:
    if not s:
        return ""
    # normalize newlines + collapse whitespace
    return " ".join(s.replace("\r\n", "\n").replace("\r", "\n").split())

def _filter_output_keep_yours(output: str, sut_name: str = "BASIC") -> str:
    """Remove known banners per SUT, preserving other text."""
    if not output:
        return "No output."
    output = output.replace('\r\n', '\n').replace('\r', '\n')

    irrelevant_phrases = SUT_FILTERS.get(sut_name.upper(), [])

    clean_lines = []
    for line in output.strip().splitlines():
        for phrase in irrelevant_phrases:
            line = line.replace(phrase, "")
        cleaned = line.strip()
        if cleaned:
            clean_lines.append(cleaned)
    return "\n".join(clean_lines)


def _normalize_exception_for_compare(s: str) -> str:
    """
    Normalize to a single comparable token (lowercased):
      - If it's a Java exception line like 'NullPointerException: ...', return 'nullpointerexception'
      - If '<no_exception>', return exactly that
      - If it's an ANTLR diagnostic ('line i:j ...'), keep the line lowercased
    Uses your existing extract_exception_type if available.
    """
    if not s:
        return "<no_exception>"
    s = s.strip()

    # Prefer your existing helper if present
    try:
        t = extract_exception_type(s)  # should return a short type or '<no_exception>'
        if t:
            return t.strip().lower()
    except NameError:
        pass

    if s == "<no_exception>":
        return "<no_exception>"

    # Try to pull a Java Exception/Error short name
    m = re.search(r'([A-Za-z_]\w*(?:Exception|Error))', s)
    if m:
        return m.group(1).lower()

    # Fallback: ANTLR diagnostic or other text
    return s.lower()

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def extract_exception_normalized(stderr_s: str, stdout_s: str = "") -> str:
    """
    Return a single-line normalized exception summary for aggregation & comparison.
    Priority:
      1) Java exception on 'Exception in thread ...'
      2) 'Caused by: ...'
      3) ANTLR diagnostic like 'line i:j ...'
      4) <no_exception>
    (Matches how we wrote exception.txt during coverage runs.)
    """
    stderr_s = stderr_s or ""
    stdout_s = stdout_s or ""

    m = re.search(r'Exception in thread ".*?" ([\w.$]+)(?::\s*(.*))?', stderr_s)
    if m:
        etype = m.group(1).split(".")[-1]
        msg = (m.group(2) or "").strip()
        return f"{etype}: {msg}" if msg else etype

    m = re.search(r'Caused by:\s+([\w.$]+)(?::\s*(.*))?', stderr_s)
    if m:
        etype = m.group(1).split(".")[-1]
        msg = (m.group(2) or "").strip()
        return f"{etype}: {msg}" if msg else etype

    m = re.search(r'line\s+\d+:\d+\s+.+', stderr_s) or re.search(r'line\s+\d+:\d+\s+.+', stdout_s)
    if m:
        return m.group(0).strip()

    return "<no_exception>"


def preflight_restore_originals(original_class_directory: str, package_prefix: str | None = None) -> int:
    """
    Restores any <class>.class.backup files found anywhere under the original_class_directory.
    - Handles nested packages (e.g., org.mozilla.javascript.ast.*)
    - Safe to call before starting a new mutation run.
    - Automatically skips non-existent or already restored paths.
    """
    if not original_class_directory or not os.path.isdir(original_class_directory):
        print(f"[RESTORE] No valid class directory found at {original_class_directory}")
        return 0

    # Build search root — typically the whole compiled output folder
    if package_prefix:
        # e.g., org.mozilla.javascript → org/mozilla/javascript
        pkg_path = package_prefix.replace(".", "/")
        search_root = os.path.join(original_class_directory, pkg_path)
        if not os.path.isdir(search_root):
            # fallback to full scan if package path missing (multi-package systems)
            search_root = original_class_directory
    else:
        search_root = original_class_directory

    restored = 0
    for root, _, files in os.walk(search_root):
        for name in files:
            if name.endswith(".backup"):
                backup_path = os.path.join(root, name)
                target_path = os.path.join(root, name[:-7])
                try:
                    os.replace(backup_path, target_path)
                    restored += 1
                except Exception as e:
                    print(f"[RESTORE] Failed: {backup_path} → {target_path}: {e}")

    if restored:
        print(f"[RESTORE] Pre-flight restored {restored} class file(s) under {search_root}")
    else:
        print(f"[RESTORE] No backup files found under {search_root} (clean state).")

    return restored


def get_sorted_mutants(mutants_dir):
    """
    """
    # Getting and sort the mutant folders based on folder names as integers
    mutant_folders = sorted(
        [f for f in os.listdir(mutants_dir) if os.path.isdir(os.path.join(mutants_dir, f))],
        key=lambda x: int(x)
    )

    mutants = {folder: os.path.join(mutants_dir, folder) for folder in mutant_folders}

    return mutants



# input_files = [f for f in os.listdir(input_files_directory) if f.endswith(".txt")]
def get_sorted_input_files(input_files_directory):
    """
    Returns a sorted list of .txt files in natural order.
    Handles both numeric (1.txt, 2.txt) and alphanumeric (fan_con_1.txt, isla_con_2.txt) filenames.
    """
    def extract_sort_key(filename):
        base = os.path.splitext(filename)[0]
        # Extract last number if present, e.g., fan_con_12 -> 12
        match = re.search(r'(\d+)$', base)
        return int(match.group(1)) if match else float('inf')

    input_files = [f for f in os.listdir(input_files_directory) if f.endswith(".txt")]
    input_files.sort(key=extract_sort_key)
    return input_files


'''
 -> We have to read 3 things for each input file from the original file:
    -> return code
    -> exception
    -> stdout [output of the program]
 -> Then we will use this information to compare with mutants information in same way
'''

"""
ENTRY POINT TO HAVE MUTATION KILLING PROFILE
"""
import os, concurrent.futures, traceback

def run_mutants_with_inputs(subject_program,
                            mutants_paths,
                            input_start=1,
                            input_end=None,
                            chunk_size=10,
                            adaptive_timeout=10,
                            input_files_directory=None,
                            original_results_directory=None,
                            reports_directory=None,
                            ):


    cfg = subject_program_config.get(subject_program, {})

    # GraalJS uses JAR runtime — not class directories
    is_graal = (subject_program.lower() == "graaljs")
    original_class_directory = cfg.get("source_classes_directory")
    main_class = cfg.get("main_class")
    classpath  = get_dynamic_classpath(subject_program)
    pkg_prefix = cfg.get("package_prefix")

    # ----------------------------------------------------------------------
    # INITIAL GRAALJS SETUP
    # ----------------------------------------------------------------------
    jar_runtime_path = None
    jar_index = None
    modified_jars = set()

    if is_graal:
        jar_runtime_path = cfg["dependencies"][0]
        print(f"[GRAALJS] Runtime jar folder = {jar_runtime_path}")

        # SINGLE INDEX BUILD for speed
        jar_index = _build_graal_jar_index(jar_runtime_path)

        # Initial restore (no-op but ensures clean jars)
        restore_original_jars(jar_runtime_path, modified_jars=set(), jar_index=jar_index)

    else:
        print(f"Source class directory: {original_class_directory}")
        preflight_restore_originals(original_class_directory, pkg_prefix)

    # =============== LOADING ORIGINAL OUTPUTS =================
    total_mutants = max(10, len(mutants_paths))

    original_results = read_original_results(input_files_directory, original_results_directory)
    sorted_input_files = get_sorted_input_files(input_files_directory)
    # slice based on start/end (convert to 0-index)
    start_idx = max(0, input_start - 1)
    end_idx = input_end or len(sorted_input_files)
    selected_inputs = sorted_input_files[start_idx:end_idx]

    print(f"[INFO] Loaded {len(selected_inputs)} inputs, {total_mutants} mutants.")

    # =============== CHUNK INPUTS ==========================
    chunks = [selected_inputs[i:i + chunk_size] for i in range(0, len(selected_inputs), chunk_size)]

    # MAIN MUTATION LOOP
    # =======================================================
    for chunk_idx, input_chunk in enumerate(chunks, start=1):
        print(f"\n[CHUNK {chunk_idx}/{len(chunks)}] Processing {len(input_chunk)} inputs...")

        # Initialize profiles for this chunk only
        mutation_profiles = {inp: [0] * total_mutants for inp in input_chunk}

        # --- Mutant loop ---
        for mutant_id, mutant_dir in enumerate(mutants_paths, start=1):
            print(f"[RUN] Mutant {mutant_id}/{total_mutants} ({os.path.basename(mutant_dir)})")

            # =======================
            # MUTANT REPLACEMENT
            # =======================
            if is_graal:
                ok = replace_mutant_in_jar(mutant_dir, jar_runtime_path, jar_index, modified_jars)
                if not ok:
                    print(f"[SKIP] Mutant not applicable.")
                    continue
            else:
                replaced_files = replace_class_with_mutant(mutant_dir, original_class_directory)
                if not replaced_files:
                    print(f"[SKIP] No valid class replaced.")
                    continue

            # =======================
            # RUN INPUTS IN PARALLEL
            # =======================
            try:
                # Parallelize per chunk to limit total JVM count
                with concurrent.futures.ProcessPoolExecutor(max_workers=14) as executor:
                    futures = [
                        executor.submit(
                            process_input_with_mutant,
                            input_file,
                            mutant_id,
                            original_results,
                            main_class,
                            input_files_directory,
                            classpath,
                            adaptive_timeout,
                            subject_program
                        )
                        for input_file in input_chunk
                    ]

                    for future in concurrent.futures.as_completed(futures):
                        try:
                            input_file, killing_status = future.result()
                            mutation_profiles[input_file][mutant_id - 1] = killing_status
                        except Exception as e:
                            print(f"[ERROR] While processing mutant {mutant_id}: {e}")
                            print(traceback.format_exc())

            finally:
                # =======================
                # RESTORE ORIGINAL
                # =======================
                if is_graal:
                    restore_original_jars(jar_runtime_path, modified_jars, jar_index)
                    modified_jars.clear()
                else:
                    restore_original_classes(original_class_directory)

                print(f"[RESTORE] Original restored after mutant {mutant_id}.")

        # ======= WRITE RESULTS FOR THIS CHUNK ========
        for input_file, mutation_results in mutation_profiles.items():
            out_path = os.path.join(reports_directory, input_file)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(" ".join(map(str, mutation_results)))

        print(f"[CHUNK {chunk_idx}] Completed → results written to {reports_directory}")

    print(f"\n✅ Finished processing all {len(mutants_paths)} mutants across {len(chunks)} input chunks.")
    print(f"[DONE] Mutation profiles stored in {reports_directory}")


def log_input_timing(mutant_id, input_file, elapsed, timed_out=False):
    """Append per-input timing to a log file for utils."""
    log_path = "MUT_KILLING_PROFILE/input_timing_log.csv"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        if timed_out:
            f.write(f"{mutant_id},{input_file},TIMEOUT\n")
        else:
            f.write(f"{mutant_id},{input_file},{elapsed:.4f}\n")



# Determine if the Mutant is KILLED or SURVIVED by the provided input(Test Case)
def process_input_with_mutant(input_file, mutant_id, original_results, main_class, input_files_directory,
                              classpath, adaptive_timeout,subject_program):
    input_path = os.path.join(input_files_directory, input_file)
    if not os.path.exists(input_path):
        print(f"Warning: Input file {input_path} not found. Skipping...")
        return input_file, 0  # treat as alive

    original_result = original_results.get(input_file)
    if original_result is None:
        print(f"Original result for {input_file} not found, skipping...")
        return input_file, 0  # treat as alive


    mutant_result = run_test_with_mutant(
        input_files_directory, input_file, main_class, classpath, timeout=adaptive_timeout,subject_program=subject_program
    )

    # if mutant_result[0] == "timeout":
    #     print(f"Mutant {mutant_id} caused a timeout. Marking as killed.")
    #     return input_file, 1  # killed

    if mutant_result[0] == "timeout":
        if original_is_timeout(original_result):
            # both timeout → NOT killed
            return input_file, 0
        # mutant timeout but original did not → killed (your old intent)
        return input_file, 1

    original_tuple = convert_original_result_to_tuple(original_result)
    killed = determine_mutant_status(mutant_result, original_tuple)
    return input_file, killed



def read_original_results(input_files_directory, original_results_directory):
    """
    Reads reference outputs (return code, exception, stdout) for each input file.
    Compatible with both numeric (1, 2, 3) and descriptive (fan_con_1, isla_con_3) folder names.
    """
    original_results = {}
    sorted_input_files = get_sorted_input_files(input_files_directory)

    def _norm_text(s: str) -> str:
        return " ".join((s or "").replace("\r\n", "\n").replace("\r", "\n").split())

    # Collect all available subdirectories in original results
    available_dirs = {os.path.basename(d): d for d in glob.glob(os.path.join(original_results_directory, "*")) if os.path.isdir(d)}

    for input_file in sorted_input_files:
        base_name = os.path.splitext(input_file)[0]  # e.g., "fan_con_1" or "1"
        base_dir = os.path.join(original_results_directory, base_name)

        # fallback: if base_name not found, try numeric or substring match
        if not os.path.exists(base_dir):
            # try case-insensitive lookup
            matched = [d for name, d in available_dirs.items() if name.lower() == base_name.lower()]
            if not matched:
                # try substring fallback (e.g., "fan_con_1" ≈ "1")
                matched = [d for name, d in available_dirs.items() if name.endswith(f"_{base_name}") or name.endswith(base_name)]
            if matched:
                base_dir = matched[0]
            else:
                print(f"[WARN] No result folder found for input '{base_name}' → skipped.")
                continue

        # ---- read return_code, exception, stdout ----
        return_code_file    = os.path.join(base_dir, "return_code.txt")
        exception_file      = os.path.join(base_dir, "exception.txt")
        program_output_file = os.path.join(base_dir, "program_output.txt")

        results = {"return_code": None, "exception": None, "stdout": ""}

        if os.path.exists(return_code_file):
            with open(return_code_file, "r", encoding="utf-8") as f:
                line = f.readline().strip()
            if ": " in line:
                results["return_code"] = line.split(": ", 1)[1]

        if os.path.exists(exception_file):
            with open(exception_file, "r", encoding="utf-8") as f:
                exception_message = f.read().strip()
            if exception_message.startswith("Exception:"):
                exception_message = exception_message[len("Exception:"):].strip()
            results["exception"] = exception_message

        if os.path.exists(program_output_file):
            with open(program_output_file, "r", encoding="utf-8") as f:
                program_output = f.read().strip()
            if program_output.startswith("Program Output:"):
                program_output = program_output[len("Program Output:"):].strip()
            results["stdout"] = _norm_text(program_output)

        original_results[input_file] = results

    return original_results



def get_dynamic_classpath(subject_program: str) -> str:
    config = subject_program_config.get(subject_program)
    if not config:
        raise ValueError(f"No config found for subject program: {subject_program}")

    class_dir = config.get("source_classes_directory") or config.get("classes_root")
    deps = config.get("dependencies", [])
    if not isinstance(deps, (list, tuple)):
        deps = [deps] if deps else []

    parts = [p for p in [class_dir] + deps if p]
    return os.pathsep.join(parts)  # ':' on Unix, ';' on Windows


def _uses_file_arg(subject_program: str | None) -> bool:
    if not subject_program:
        return False
    config = subject_program_config.get(subject_program)
    return bool(config and config.get("input_execution_mode") == "file_arg")


"""
    -> For each mutant : we will replace in the source folder and re-instrument
    -> with the instrumented class we will execute the input file
    - get the output and return for further usage
"""

def run_test_with_mutant(input_files_directory, input_file, main_class, classpath, timeout=0.5,subject_program=None):
    """
    Run the mutant (no -javaagent). Returns (return_code:str, filtered_stdout:str, exception_one_line:str)
    or ("timeout", "", "<timeout>") on timeout.
    """
    is_graal = (subject_program and subject_program.lower() == "graaljs")

    # -------------------------
    # GRAALJS SPECIAL COMMAND
    # -------------------------
    if is_graal:
        cfg = subject_program_config["graaljs"]
        cp = _graal_classpath([cfg["dependencies"][0]])
        jvm_flags = cfg.get("jvm_flags", [])
        cmd = ["java"] + jvm_flags + ["-cp", cp, cfg["main_class"]]

    # -------------------------
    # NORMAL SUT COMMAND
    # -------------------------
    else:
        cmd = ["java", "-cp", classpath, main_class]

    in_path = os.path.join(input_files_directory, input_file)
    if _uses_file_arg(subject_program):
        run_cmd = cmd + [in_path]
        stdin_source = subprocess.DEVNULL
        close_stdin = False
    else:
        run_cmd = cmd
        stdin_source = open(in_path, "r", encoding="utf-8")
        close_stdin = True

    try:
        try:
            proc = subprocess.Popen(run_cmd, stdin=stdin_source, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=timeout)

            out_s = stdout.decode("utf-8", errors="replace").strip()
            err_s = stderr.decode("utf-8", errors="replace").strip()


            # Remove banner line
            out_lines = [line.strip() for line in out_s.splitlines()]
            filtered_output = "\n".join(l for l in out_lines if "Type 'exit' to quit" not in l)
            filtered_output = filtered_output.replace("\r\n", "\n").replace("\r", "\n")

            exception_message = extract_exception_normalized(err_s, out_s)
            return_code = str(proc.returncode)

            return return_code, filtered_output, exception_message

        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.communicate(timeout=0.5)
            except Exception:
                pass
            print(f"Mutant test timed out after {timeout} seconds.")
            return "timeout", "", "<timeout>"
    finally:
        if close_stdin:
            stdin_source.close()



def convert_original_result_to_tuple(original_result):

    # Extract the 'return_code' from the dictionary, or set to None if it doesn't exist
    return_code = original_result.get('return_code', None)

    # Extract the 'exception' message from the dictionary, or set to None if it doesn't exist
    exception_message = original_result.get('exception', None)

    # Extract the 'stdout' output from the dictionary, or set to None if it doesn't exist
    stdout_output = original_result.get('stdout', None)

    # Return the extracted values as a tuple
    return return_code, stdout_output, exception_message

def determine_mutant_status(mutant_result, original_result_tuple):
    """
    Your original order:
      1) return code
      2) exception
      3) stdout
    Kill if any differ; else alive.
    """
    mutant_return_code, mutant_output, mutant_exception = mutant_result
    original_return_code, original_output, original_exception = original_result_tuple

    # Return codes as ints (your original choice)
    m_rc = _safe_int(mutant_return_code, default=0)
    o_rc = _safe_int(original_return_code, default=0)

    # Filter/normalize outputs (keep your banner filter; add whitespace normalization)
    filtered_mutant_output   = _filter_output_keep_yours(mutant_output)
    filtered_original_output = _filter_output_keep_yours(original_output)
    m_out = _norm_text(filtered_mutant_output)
    o_out = _norm_text(filtered_original_output)

    # Normalize exceptions on both sides the same way
    m_ex = _normalize_exception_for_compare(mutant_exception)
    o_ex = _normalize_exception_for_compare(original_exception)

    # 1) Return code
    if o_rc == 0:
        if m_rc == 0:
            # both succeeded → compare outputs and exceptions
            return 0 if (m_out == o_out and m_ex == o_ex) else 1
        else:
            # mutant crashed but original didn't → killed
            return 1
    else:
        if m_rc == 0:
            # original crashed but mutant succeeded → killed
            return 1
        else:
            # both crashed → compare exceptions
            return 0 if m_ex == o_ex else 1


def original_is_timeout(original_result) -> bool:
    """
    Works whether original_result is a dict or any object containing exception text.
    Adjust keys/fields to match your read_original_results() output.
    """
    if original_result is None:
        return False

    # common cases: dict with 'exception', or tuple/list, or raw string
    if isinstance(original_result, dict):
        exc = (original_result.get("exception") or original_result.get("exception.txt") or "").strip()
        return "timeout" in exc.lower()

    if isinstance(original_result, (tuple, list)) and len(original_result) >= 3:
        exc = str(original_result[2] or "").strip()
        return "timeout" in exc.lower()

    # fallback: treat it as string
    return "timeout" in str(original_result).lower()
