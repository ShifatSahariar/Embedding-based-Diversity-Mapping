import glob
import subprocess
import os
import shutil
from pathlib import Path
import zipfile

"""
Later we will automate the process of mutant generation so user will only pass the tool name and others
- necessary details to generate mutants
"""


import platform
import subprocess

def generate_mutants_PIT(project_base, mutants_dir, lib_dir, target_classes, source_dirs, dependencies=None, target_tests=None, verbose=False):
    """
    Works on both Windows and macOS/Linux by adjusting the classpath separator automatically.

    PIT is used here only as a mutant exporter. PIT's command-line exporter
    still performs its own internal test-coverage discovery while creating the
    export, but those PIT coverage and kill/survive results are not used by
    this artifact. The artifact's mutation-killing profiles are produced later
    by running selected exported mutants against the generated input pools.
    """
    sep = ";" if platform.system() == "Windows" else ":"

    # # Normalize dependencies list
    if dependencies is None:
        dependencies = []
    if isinstance(project_base, list):
        project_dirs = project_base
    else:
        project_dirs = [project_base]
    # elif isinstance(dependencies, str):
    #     dependencies = [dependencies]
    #
    # # Build the classpath
    # classpath_parts = [lib_dir, project_base] + dependencies
    # full_classpath = sep.join(classpath_parts)
    # -------------------------------------------------------------
    # SPECIAL CASE: GRAALJS ⇒ expand JARs inside dependency folder
    # -------------------------------------------------------------
    expanded_cp = [lib_dir]  # PIT jars first

    for p in project_dirs + dependencies:
        if os.path.isdir(p):
            # add directory itself
            expanded_cp.append(p)
            # add all JARs inside
            for f in os.listdir(p):
                if f.endswith(".jar"):
                    expanded_cp.append(os.path.join(p, f))
        else:
            expanded_cp.append(p)

    full_classpath = sep.join(expanded_cp)

    # Build the PIT command
    command = [
        "java", "-cp", full_classpath,
        "org.pitest.mutationtest.commandline.MutationCoverageReport",
        "--reportDir", mutants_dir,
        "--targetClasses", target_classes,
        "--sourceDirs", source_dirs,
        "--export",
        "--mutators", "STRONGER",
        "--features", "+EXPORT",
    ]
    if verbose:
        command.append("--verbose")
    if target_tests:
        command.extend(["--targetTests", target_tests])

    pit_dir = os.path.dirname(lib_dir.rstrip("*"))
    pit_jars = glob.glob(os.path.join(pit_dir, "*.jar"))
    if not pit_jars:
        raise FileNotFoundError(
            "No PIT jars found for mutation generation. "
            f"Expected jars under {pit_dir}. "
            "Install PIT command-line jars before running --generate_mutants true."
        )

    pit_main_class = "org/pitest/mutationtest/commandline/MutationCoverageReport.class"
    has_pit_main = False
    for jar_path in pit_jars:
        try:
            with zipfile.ZipFile(jar_path) as jar:
                if pit_main_class in jar.namelist():
                    has_pit_main = True
                    break
        except zipfile.BadZipFile:
            continue
    if not has_pit_main:
        raise FileNotFoundError(
            "PIT jars were found, but the command-line main class was not. "
            f"Expected {pit_main_class} in one of the jars under {pit_dir}. "
            "Install the pitest-command-line jar and its runtime dependencies."
        )

    print(
        "[INFO] PIT export phase only: PIT may perform internal coverage/test execution "
        "to export mutants. These PIT coverage and kill/survive results are ignored; "
        "artifact killing is computed later with --running_mutants true."
    )
    print("[DEBUG] PIT command:\n", " ".join(command))
    subprocess.run(command, check=True)

    # descartes_mutators = (
    #     "void,null,true,false,empty,0,1,(byte)0,(byte)1,(short)0,(short)1,"
    #     "0L,1L,0.0,1.0,0.0f,1.0f,'\\40','A',\"\", \"A\""
    # )
    # command = [
    #     "java", "-cp", f"{lib_dir}:{project_base}",
    #     "org.pitest.mutationtest.commandline.MutationCoverageReport",
    #     "--reportDir", mutants_dir,
    #     "--targetClasses", target_classes,
    #     "--sourceDirs", source_dirs,
    #     "--mutationEngine", "descartes",
    #
    #     "--mutators", descartes_mutators,
    #     "--features", "+EXPORT",
    #     "--export",
    #     "--verbose"
    # ]


def generate_mutants_major(compile_mml_file, mml_filename, source_dir, target_class, major_home, mutants_dir,
                           dependency_jar):

    # - Once we are done with generation with major
    original_java_home = os.environ.get('JAVA_HOME', '')
    original_path = os.environ.get('PATH', '')
    # Backup current directory
    original_dir = os.getcwd()

    temp_dir = None  # Initialize temp_dir to avoid the unbound local error
    try:
        # Set Java 7 for Major execution
        # - Since Few subject programs such as Calc use java 7 to compile and work
        # - moreover, major works with java 8.
        java_7_home = "/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home"
        os.environ['JAVA_HOME'] = java_7_home
        os.environ['PATH'] = f"{java_7_home}/bin:{original_path}"
        java_version_check = subprocess.run(
            ["javac", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        print("Compiler being used:", java_version_check.stdout.strip())

        # We will re-compile the mml file if needed by passing TRUE or FALSE and the file name which
        # we have modified or added.
        # Mml file is responsible to decide which mutation operators will be assigned
        if compile_mml_file:
            compile_mml_file_major(major_home, mml_filename)

        # First, we Copy the source directory to a temporary location for mutation
        # - we don't want to mess with the original compiled program with the latest java version
        temp_dir = os.path.join(major_home, "temp_repo_compile_with_major")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        shutil.copytree(source_dir, temp_dir)

        # Prepare the mutants directory inside the major_home directory
        absolute_major_home_path = os.path.abspath(major_home)
        mutant_output_dir = Path(f"{absolute_major_home_path}/mutants_output/{mutants_dir}")
        mutant_output_dir.mkdir(parents=True, exist_ok=True)

        # We Compile the program with Java 7 and Major
        # **Store absolute path to the Major tools**
        major_javac = os.path.abspath(f"{major_home}/bin/javac")
        mml_file = os.path.abspath(f"{major_home}/mml/all.mml.bin")
        temp_dir = os.path.abspath(temp_dir)

        # Change working directory to temp_dir
        os.chdir(temp_dir)
        # print(f"Looking in: {os.path.abspath(source_dir)}")
        # print(f"Files found: {glob.glob(os.path.join(source_dir, '*.java'))}")
        # print(f"Files found: {glob.glob(os.path.join(temp_dir, '*.java'))}")

        # we have added command to export the mutants as well as the location where the mutants will be exported
        compile_files = glob.glob(os.path.join(temp_dir, "*.java"))

        try:
            result = subprocess.run(
                ["javac", *compile_files],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True  # decode output as string
            )
            print("Compilation successful!")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print("Compilation failed.")
            print("Return code:", e.returncode)
            print("STDOUT:\n", e.stdout)
            print("STDERR:\n", e.stderr)
        java_7_home = "/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home"
        os.environ['JAVA_HOME'] = java_7_home
        os.environ['PATH'] = f"{java_7_home}/bin:{original_path}"
        compile_command = [
            major_javac,
            f"-XMutator={mml_file}",
            "-J-Dmajor.export.mutants=true",
            f"-J-Dmajor.export.directory={mutant_output_dir}",
            "-cp", f".:{dependency_jar}" if dependency_jar else ".",
            target_class
        ]

        # Run the Major mutation generation command
        subprocess.run(compile_command, check=True)

        mutants_log = Path(temp_dir) / "mutants.log"
        if mutants_log.exists():
            shutil.copy(str(mutants_log), str(mutant_output_dir / "mutants.log"))
            print(f"Mutants generated and stored in {mutants_dir}")

        # Compile all the mutant Java files to .class files
        # Compile and replace mutants in the temp_dir (acting as SUT)
        sut_source_dir = Path(temp_dir)  # Path to the SUT source files (temporary dir)
        # mutant_output_dir - as the directory from where we will copy and again put back the compiled class file
        # sut_source_dir - temporary folder will be used just to compile the file / depending on
        # subject program the compilation process could be differing
        compile_and_replace_mutants(mutant_output_dir, absolute_major_home_path)

    except Exception as e:
        print(f"Error generating mutants: {e}")
    finally:
        # Step 4: Clean up and restore the original environment
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        # Restore original working directory
        os.chdir(original_dir)
        # Restore original JAVA_HOME and PATH
        os.environ['JAVA_HOME'] = original_java_home
        os.environ['PATH'] = original_path

# if we want to modify the mml file: - we will use this function to re-compile which file we have modified
def compile_mml_file_major(major_home, mml_filename):
    try:
        # Path to the mmlc compiler
        mmlc_path = os.path.join(major_home, 'bin', 'mmlc')

        # File names for the mml file and the output .bin file
        mml_bin_file_path = os.path.join(major_home, 'mml', f'{mml_filename}.bin')
        mml_file_path = os.path.join(major_home, 'mml', mml_filename)

        # Compile the mml file
        command = [mmlc_path, mml_file_path, mml_bin_file_path]
        print(f"Running command: {' '.join(command)}")

        # Execute the command
        subprocess.run(command, check=True)

        print(f"Successfully compiled {mml_filename} to {mml_bin_file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {mml_filename}: {e}")


def compile_and_replace_mutants(mutant_output_dir, absolute_major_home_path):
    """
    Compiles each mutant in temp_dir (acting as SUT), replaces the original file, and
    moves the class file back into the mutant directory after compilation.
    """
    """
    Later we have to automate this process for other subject programs depending on the mutant_output_dir name.
    """

    # Convert mutant_output_dir to a Path object if it's a string
    mutant_output_dir = Path(mutant_output_dir)

    for mutant_dir in mutant_output_dir.iterdir():
        if mutant_dir.is_dir():
            java_files = list(mutant_dir.glob("*.java"))
            if java_files:
                for java_file in java_files:
                    try:
                        # Step 1: Remove any existing class file in SUT before copying the new mutant
                        sut_java_file = Path(java_file.name)  # The file we are copying to SUT
                        sut_class_file = Path(sut_java_file.with_suffix('.class').name)  # Expected class file

                        if sut_class_file.exists():  # Ensure the previous class file is deleted
                            sut_class_file.unlink()  # Remove the old class file
                            print(f"Removed old class file {sut_class_file} from SUT")

                        # Step 2: Copy the mutant .java file to the SUT (temp_dir)
                        shutil.copy(str(java_file), str(sut_java_file))  # Copy the mutant file
                        print(f"Replaced {sut_java_file} with mutant {java_file}")

                        # Step 3: Compile the SUT source file with dependencies
                        compile_command = [
                            os.path.join(absolute_major_home_path, "bin", "javac"),
                            "-cp", f".:antlr-3.2.jar",  # Ensure antlr-3.2.jar is on the classpath
                            str(sut_java_file)  # Compile the replaced Java file
                        ]
                        print(f"Compiling {sut_java_file} with dependencies...")
                        subprocess.run(compile_command, check=True)

                        # Step 4: Move the generated class file back to the mutant directory
                        if sut_class_file.exists():
                            shutil.copy(str(sut_class_file), str(mutant_dir / sut_class_file.name))
                            print(f"Moved {sut_class_file} to {mutant_dir}")

                    except subprocess.CalledProcessError as e:
                        print(f"Error compiling {sut_java_file}: {e}")
                    except Exception as e:
                        print(f"Error handling mutant {java_file}: {e}")
