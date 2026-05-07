import os
import subprocess
from xml.etree import ElementTree as ET


"""
 we are deciding what kind of configuration we need for the targeted subject program to run 
 - to instrument
 - which classes we are targeting to generate reports
 - if there are any dependencies
"""
JACOCO_MODE = "online"   # "online" (recommended) or "offline"
JACOCO_AGENT = "COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/jacocoagent.jar"
JACOCO_CLI   = "COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/jacococli.jar"
JACOCO_EXEC  = "jacoco.exec"




def get_coverage_filename(subject_program):
    """
    Returns the coverage profile filename based on the subject program.

    Args:
        subject_program (str): The subject program (e.g., 'CALC', 'basic').

    Returns:
        str: The appropriate coverage profile filename for the subject program.
    """
    if subject_program == 'CALC':
        return 'aggregated_profile.txt'  # CalcParser_profile.txt
    elif subject_program == 'basic':
        return 'aggregated_profile.txt'
    else:
        raise ValueError(f"Unsupported subject program: {subject_program}")


def parse_xml_get_statement_coverage_ci(folder_path,allowed_packages=None, allowed_basenames=None):
    """
    Parsing XML files and generating coverage reports for each statement.

    - We are checking the `ci` (covered instruction) attribute for each line in the XML files.
    - If `ci` > 0 (meaning the instruction is covered), we assign a coverage value of 1.
    - Otherwise, we assign a coverage value of 0.
    - This creates a coverage profile for each file and saves it as a text file in the same folder.

    Args:
        folder_path (str): The path to the directory containing the XML files.

    Example:
        Given an XML report in `folder_path/report.xml`:

        <sourcefile name="Example.java">
            <line nr="1" ci="2" />
            <line nr="2" ci="0" />
        </sourcefile>

        The resulting profile file would be named `Example_profile.txt` and contain:
        1 0

        This means line 1 was covered (ci > 0), and line 2 was not covered (ci = 0).
    """
    report_path = os.path.join(folder_path, "report.xml")
    if not os.path.isfile(report_path):
        return

    with open(report_path, "r", encoding="utf-8") as file:
        xml_data = file.read()

    root = ET.fromstring(xml_data)

    for pkg in root.findall(".//package"):
        pkg_name = pkg.attrib.get("name", "")  # "" for default package

        # Package filter (when present)
        if allowed_packages is not None:
            # default package is allowed only if "" in allowed_packages
            if (pkg_name or "") not in set(allowed_packages):
                continue

        pkg_tag = (pkg_name.replace(".", "/") or "_default_").replace("/", "_")

        for sourcefile in pkg.findall("sourcefile"):
            base = os.path.splitext(sourcefile.attrib["name"])[0]

            # Basename filter for default-package subjects (Calc)
            if allowed_basenames is not None and base not in allowed_basenames:
                continue

            bits = []
            for line in sourcefile.findall("line"):
                ci = int(line.attrib.get("ci", "0"))
                bits.append("1" if ci > 0 else "0")

            out_name = f"{pkg_tag}__{base}_profile.txt"
            with open(os.path.join(folder_path, out_name), "w", encoding="utf-8") as out_file:
                out_file.write(" ".join(bits))



def generate_jacoco_report(jacoco_exec_file, class_files, output_dir, fileName):
    jacoco_cli_path = JACOCO_CLI  # use the shared constant

    output_subdir = os.path.join(output_dir, os.path.splitext(os.path.basename(fileName))[0])
    os.makedirs(output_subdir, exist_ok=True)

    # We already wrote artifacts in the runner; don't duplicate here.

    # Abort early if no .exec (prevents “missing report” confusion)
    if not os.path.exists(jacoco_exec_file):
        print(f"[SKIP] {fileName}: '{jacoco_exec_file}' not found. No coverage recorded for this run.")
        return

    # Build CLI command
    command = ["java", "-jar", jacoco_cli_path, "report", jacoco_exec_file]
    for classpath in class_files:
        command.extend(["--classfiles", classpath])

    command.extend(["--html", output_subdir])
    command.extend(["--csv", os.path.join(str(output_subdir), "report.csv")])
    command.extend(["--xml", os.path.join(str(output_subdir), "report.xml")])



    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print("[JaCoCo CLI] Error:", stderr.decode("utf-8", errors="replace"))
    else:
        print("Report generated successfully:", output_subdir)

