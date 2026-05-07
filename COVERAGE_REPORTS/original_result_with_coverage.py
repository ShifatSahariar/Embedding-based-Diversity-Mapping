import os

from COVERAGE_REPORTS.Coverage_Profile import concatenate_statement_coverage_profiles
from COVERAGE_REPORTS.Coverage_Reports import coverage_all_input_file
from Helper_Functions.Coverage_Helping_Functions import parse_xml_get_statement_coverage_ci
from Helper_Functions.configs.coverage_configs import subject_program_config

"""
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> COVERAGE REPORTS USING JACOCO <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
- For each Input File CODE COVERAGE REPORT GENERATE
- for each input file in some point the parser may crash [due to unassigned variable]
- we have to track the state or do some operation for each file !
"""
# Pass the directory from where we will read the files
"""
        input_files_directory: The directory from where we will read the input files
        source_class_directory: The directory containing the classes to be instrumented.
        Instrument_class_directory (str): The directory where the instrumented classes will be saved.
        reports_directory: Where we will save the coverage reports
"""


def build_filter_rules(key: str, subj: dict):
    """Derives package/basename filters for XML parsing (BASIC/CALC/RHINO)."""
    allowed_packages = None
    allowed_basenames = None

    includes = subj.get("agent_includes") or []
    pkg_includes = [inc.split("/*")[0] for inc in includes if inc.endswith("/*")]

    if pkg_includes:
        allowed_packages = pkg_includes
    else:
        # Handle default-package (Calc-style)
        star_includes = [inc for inc in includes if "*" in inc]
        if star_includes:
            orig_entry = subject_program_config.get(key, {})
            class_files = orig_entry.get("class_files", [])
            if class_files:
                allowed_basenames = {
                    os.path.splitext(os.path.basename(p))[0] for p in class_files
                }

    return allowed_packages, allowed_basenames


def extract_and_aggregate_profiles(
        reports_dir: str,
        key: str,
        allowed_packages=None,
        allowed_basenames=None
):
    """
    Iterates over all per-input report folders:
      - Extracts per-file coverage profiles (*.xml → *_profile.txt)
      - Aggregates them using your existing concatenate function
    """

    for subdir in sorted(os.listdir(reports_dir)):
        p = os.path.join(reports_dir, subdir)
        if not os.path.isdir(p):
            continue

        # Parse XML coverage report
        try:
            parse_xml_get_statement_coverage_ci(
                p,
                allowed_packages=allowed_packages,
                allowed_basenames=allowed_basenames
            )
        except TypeError:
            # Backwards compatibility (older signature)
            parse_xml_get_statement_coverage_ci(p)

        # Concatenate coverage profiles into a global profile file
        concatenate_statement_coverage_profiles(p, key, subject_program_config)


def _normalize_subject_config(subj_key: str, subject_program_config: dict) -> dict:
    raw = subject_program_config[subj_key]
    subject_name = raw.get("subject_program_name")
    # ORIGINAL classes root (required)
    classes_root = raw.get("source_classes_directory") or raw.get("classes_root")
    if not classes_root:
        raise ValueError("[CFG] Missing 'source_classes_directory' (or 'classes_root') for ONLINE mode.")
    if "instrumented" in classes_root.lower():
        raise ValueError("[CFG] classes_root points to an instrumented path; use ORIGINAL classes.")

    # 1) Prefer explicit includes if present
    agent_includes = list(raw.get("agent_includes", []) or [])

    # 2) Infer from package for packaged subjects (BASIC)
    pkg = raw.get("package_prefix")
    if not agent_includes and pkg:
        # JaCoCo expects JVM-style slashes; for a simple single-segment package name this is fine.
        agent_includes = [f"{pkg}/*"]  # e.g., "basic/*"  "org.mozilla.javascript/*"

    # 3) Default-package subjects (CALC): infer from class_files/main_class
    if not agent_includes and not pkg:
        basenames = [os.path.splitext(os.path.basename(p))[0]
                     for p in raw.get("class_files", [])]
        basenames = [b for b in basenames if b]

        if basenames:
            # Try a meaningful common prefix; else whitelist exact names
            lcp = os.path.commonprefix(basenames)
            if lcp and lcp[0].isalpha() and len(lcp) >= 3:
                agent_includes = [f"{lcp}*"]  # e.g., "Calc*"
            else:
                agent_includes = sorted(set(basenames))  # exact default-package class names
        else:
            mc = (raw.get("main_class") or "").split(".")[-1]
            agent_includes = [mc] if mc else ["*"]

    # Prefer explicit ORIGINAL class files for the report; else fall back to the root dir
    report_classfiles = []
    for p in raw.get("class_files", []):
        if p and "instrumented" not in p.lower():
            report_classfiles.append(p)
    if not report_classfiles:
        report_classfiles = [classes_root]

    # Support additional dependencies for multi-module SUTs (like Rhino)
    deps = raw.get("dependencies", [])
    if subj_key == "rhino" and deps:
        # Deduplicate + preserve order
        deps = [d for i, d in enumerate(deps) if d not in deps[:i]]
    # Deduplicate and keep order
    seen = set()
    agent_includes = [x for x in agent_includes if not (x in seen or seen.add(x))]
    seen.clear()
    report_classfiles = [x for x in report_classfiles if not (x in seen or seen.add(x))]

    return {
        "subject_name": subject_name,
        "classes_root": classes_root,
        "main_class": raw["main_class"],
        "dependencies": raw.get("dependencies", []),
        "input_execution_mode": raw.get("input_execution_mode"),
        "jvm_flags": raw.get("jvm_flags", []),
        "agent_includes": agent_includes,
        "report_classfiles": report_classfiles,

    }


def coverage_profile_with_original_result(
        sut_program: str = "CALC",
        inputs_root_dir: str = None,
        generate_coverage: bool = True,
        adaptive_timeout: float = 1.5,
        parallel_mode: bool = True,
        run_limit: int = None,
        analyze_results: bool = False
) -> None:
    """
    Dynamically run coverage collection for each input batch/run folder.
    Creates separate coverage report folders: coverage_run_1, coverage_run_2, etc.
    """
    key = sut_program.lower()
    subj = _normalize_subject_config(key, subject_program_config)

    base_reports_dir = f"COVERAGE_REPORTS/{key.upper()}"
    os.makedirs(base_reports_dir, exist_ok=True)

    # Discover input folders automatically
    if not inputs_root_dir:
        inputs_root_dir = f"GENERATED_INPUTS/FUZZ_TOOL_SELECTOR/{key.upper()}"
    if not os.path.exists(inputs_root_dir):
        print(f"[ERROR] Input root not found: {inputs_root_dir}")
        return

    def run_sort_key(folder_name):
        try:
            return int(folder_name.rsplit("_", 1)[-1])
        except ValueError:
            return folder_name

    run_folders = sorted(
        [f for f in os.listdir(inputs_root_dir) if f.startswith("input_pool_by_run_")],
        key=run_sort_key
    )
    if run_limit is not None:
        run_folders = run_folders[:run_limit]
    if not run_folders:
        print(f"[WARN] No run folders found under {inputs_root_dir}")
        return
    print(f"[CFG] Running coverage for {sut_program.upper()} across {len(run_folders)} run(s).")

    for run_name in run_folders:
        input_dir = os.path.join(inputs_root_dir, run_name)
        report_dir = os.path.join(base_reports_dir, f"coverage_{run_name}")
        os.makedirs(report_dir, exist_ok=True)

        print(f"\n[RUN] Generating coverage for {run_name}")
        print(f"      Inputs: {input_dir}")
        print(f"      Reports: {report_dir}")

        # Run coverage for all inputs in this run folder
        coverage_all_input_file(
            input_files_directory=input_dir,
            reports_directory=report_dir,
            subject_program_config=subj,
            generate_coverage=generate_coverage,
            adaptive_timeout=adaptive_timeout,
            parallel_mode=parallel_mode,
            max_workers=10
        )
        # Optional XML aggregation
        if generate_coverage:
            print(f"[POST] Extracting coverage profiles from XML reports for {run_name}...")
            allowed_packages, allowed_basenames = build_filter_rules(key, subj)
            extract_and_aggregate_profiles(
                reports_dir=report_dir,
                key=key,
                allowed_packages=allowed_packages,
                allowed_basenames=allowed_basenames
            )
        else:
            print(f"[SKIP] Coverage report parsing skipped (coverage={generate_coverage}).")

        if analyze_results:
            from Helper_Functions.Visualization import analyze_return_codes_and_exceptions
            print(f"[POST] Analyzing return codes and exceptions for {run_name}...")
            analyze_return_codes_and_exceptions(report_dir)
        else:
            print("[SKIP] Return/exception plotting skipped.")

    # always run return/exception statistics ----
    print(f"\n✅ Completed coverage generation for {len(run_folders)} runs of {sut_program.upper()}.")
