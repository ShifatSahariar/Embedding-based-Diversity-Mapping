
from concurrent.futures import ProcessPoolExecutor
import subprocess, re



import os, shutil

from Helper_Functions.Coverage_Helping_Functions import generate_jacoco_report

JACOCO_AGENT = "COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/jacocoagent.jar"
JACOCO_EXEC  = "jacoco.exec"
def _graal_classpath(parts):
    """
    Build classpath from a list of directories/JARs.
    - If a part is a directory, include the directory AND all *.jar inside it.
    - If part is a jar file, include it directly.
    """
    cp_entries = []

    for p in parts:
        if not p:
            continue

        if os.path.isdir(p):
            # Add the folder itself (needed for classes)
            cp_entries.append(p)

            # Add all .jar files inside the folder
            for jar in os.listdir(p):
                if jar.endswith(".jar"):
                    cp_entries.append(os.path.join(p, jar))

        else:
            # Direct JAR path
            cp_entries.append(p)

    return os.pathsep.join(cp_entries)

def _classpath(parts):
    return os.pathsep.join([p for p in parts if p])  # OS-safe
def safe_rmtree(path):
    """Robustly remove directory tree, even with open handles or hidden files."""
    import errno
    if not os.path.exists(path):
        return
    def _onerror(func, p, exc_info):
        err = exc_info[1]
        if isinstance(err, FileNotFoundError):
            return
        if getattr(err, "errno", None) == errno.ENOTEMPTY:
            try:
                for sub in os.listdir(p):
                    subp = os.path.join(p, sub)
                    if os.path.isdir(subp):
                        safe_rmtree(subp)
                    else:
                        os.remove(subp)
                os.rmdir(p)
            except Exception:
                pass
        else:
            raise
    shutil.rmtree(path, onerror=_onerror)

def _java_cmd_with_agent(subj, destfile=JACOCO_EXEC):
    cp = _classpath([subj["classes_root"]] + subj.get("dependencies", []))
    agent = f"-javaagent:{JACOCO_AGENT}=destfile={destfile}"
    inc   = subj.get("agent_includes") or []
    if inc:
        agent += ",includes=" + ":".join(inc)
    return ["java", agent, "-cp", cp, subj["main_class"]]

def _uses_file_arg(subject_program_config):
    return subject_program_config.get("input_execution_mode") == "file_arg"

# --- TOP-LEVEL WORKER (must be defined at module scope) ---
def _process_single_input(args):
    """Worker function for a single input file (parallel-safe)."""
    (fname, input_files_directory, reports_directory,
     subject_program_config, generate_coverage, adaptive_timeout) = args



    # --- Paths ---
    file_path = os.path.join(input_files_directory, fname)
    out_dir   = os.path.join(reports_directory, os.path.splitext(fname)[0])
    os.makedirs(out_dir, exist_ok=True)
    exec_file = None

    # --- Generate JaCoCo report (only if coverage enabled) ---
    # --- Special case: GraalJS (no coverage + different run command) ---

    subject_name = subject_program_config.get("subject_name") or subject_program_config.get("subject_program_name")
    if subject_name == "graaljs":
        # we are not generating coverage report with GraalVM for now since ,
        # graal run with jar file rather than compiled files
        # GraalVM-specific JVM command
        cp = _graal_classpath([subject_program_config["classes_root"]] +
                        subject_program_config.get("dependencies", []))


        jvm_flags = subject_program_config.get("jvm_flags", [])

        cmd = ["java"] + jvm_flags + ["-cp", cp, subject_program_config["main_class"]]

    # --- Normal JVM execution (Calc, Rhino, BASIC) ---
    else:
        if generate_coverage:
            exec_file = os.path.join(str(out_dir), "jacoco.exec")
            cmd = _java_cmd_with_agent(subject_program_config, destfile=exec_file)
        else:
            cp = _classpath([subject_program_config["classes_root"]] +
                            subject_program_config.get("dependencies", []))
            cmd = ["java", "-cp", cp, subject_program_config["main_class"]]

    # --- Run the program ---
    # Some subjects, such as KarateJS, expect the script path as argv[0].
    # Others are interactive/batch interpreters that read the input from stdin.
    if _uses_file_arg(subject_program_config):
        run_cmd = cmd + [file_path]
        stdin_source = subprocess.DEVNULL
        close_stdin = False
    else:
        run_cmd = cmd
        stdin_source = open(file_path, "r", encoding="utf-8")
        close_stdin = True

    try:
        try:
            proc = subprocess.Popen(run_cmd, stdin=stdin_source,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=adaptive_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            with open(os.path.join(str(out_dir), "exception.txt"), "w", encoding="utf-8") as f:
                f.write("Timeout (possible infinite loop)\n")
            return fname
    finally:
        if close_stdin:
            stdin_source.close()

    rc   = proc.returncode
    out  = stdout.decode("utf-8", errors="replace").strip()
    err  = stderr.decode("utf-8", errors="replace").strip()

    # --- Write artifacts ---
    def _normalize_exception(stderr_s: str, stdout_s: str = "") -> str:
        if not stderr_s and not stdout_s:
            return "<no_exception>"
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
        return "<no_exception>"

    norm_exc = _normalize_exception(err, out)

    with open(os.path.join(str(out_dir), "return_code.txt"), "w", encoding="utf-8") as f:
        f.write(f"Return Code: {rc}\n")
    with open(os.path.join(str(out_dir), "exception.txt"), "w", encoding="utf-8") as f:
        f.write(norm_exc + "\n")
    if err:
        with open(os.path.join(str(out_dir), "stderr_full.txt"), "w", encoding="utf-8") as f:
            f.write(err + "\n")
    cleaned_out = "\n".join(l for l in out.splitlines()
                            if "Type 'exit' to quit" not in l)
    with open(os.path.join(str(out_dir), "program_output.txt"), "w", encoding="utf-8") as f:
        f.write("Program Output:\n" + (cleaned_out or "No output.") + "\n")

    # --- Generate JaCoCo report (AFTER run completes) ---
    if generate_coverage and os.path.exists(exec_file):
            try:
                class_files = [subject_program_config["classes_root"]] + subject_program_config.get("dependencies", [])
                generate_jacoco_report(
                    jacoco_exec_file=exec_file,
                    class_files=class_files,
                    output_dir=out_dir,
                    fileName=fname,
                )
            except Exception as e:
                print(f"[WARN] Failed to generate JaCoCo report for {fname}: {e}")
    elif generate_coverage:
            print(f"[SKIP] No jacoco.exec found for {fname}")
    return fname

def coverage_all_input_file(
    input_files_directory: str,
    reports_directory: str,
    subject_program_config: dict,
    generate_coverage: bool = True,
    adaptive_timeout: float = 1.5,
    parallel_mode: bool = True,
    max_workers: int = None
):
    """
    ONLINE mode batch runner (refined + parallel safe).

    For each *.txt input:
      - Runs SUT with or without JaCoCo agent.
      - Writes per-input artifacts: return_code.txt, exception.txt, stderr_full.txt, program_output.txt.
      - Optionally generates JaCoCo HTML/XML/CSV reports.
      - Supports parallel execution with isolated per-input jacoco.exec files.
    """

    # --------------------------
    # setup
    # --------------------------
    safe_rmtree(reports_directory)
    os.makedirs(reports_directory, exist_ok=True)

    if generate_coverage:
        assert os.path.exists(JACOCO_AGENT), f"JaCoCo agent not found at {JACOCO_AGENT}"
        assert os.path.exists(subject_program_config["classes_root"]), \
            f"classes_root not found: {subject_program_config['classes_root']}"

    files = sorted(f for f in os.listdir(input_files_directory) if f.endswith(".txt"))
    if not files:
        print(f"[WARN] No .txt files in {input_files_directory}")
        return

    # --------------------------
    # execution strategy
    # --------------------------
    if parallel_mode:
        workers = max_workers or os.cpu_count() or 4
        print(f"[INFO] Running in parallel mode with {workers} workers...")

        args_list = [
            (fname, input_files_directory, reports_directory,
             subject_program_config, generate_coverage, adaptive_timeout)
            for fname in files
        ]

        with ProcessPoolExecutor(max_workers=workers) as executor:
            for _ in executor.map(_process_single_input, args_list):
                pass  # just triggering the calls
    else:
        for fname in files:
            _process_single_input((
                fname, input_files_directory, reports_directory,
                subject_program_config, generate_coverage, adaptive_timeout
            ))

    print(f"[ALL DONE] Processed {len(files)} inputs → {reports_directory}")
