"""Project inspection without executing user project commands."""

import os
import re
import json
from pathlib import Path
from typing import Any

from .config import MAX_SCAN_FILES, MAX_TEXT_BYTES
from .security import ensure_inside_root, safe_relative


def iter_project_files(project_root: Path) -> list[Path]:
    skipped_dirs = {".git", "node_modules", "target", "build", "dist", ".venv", "__pycache__"}
    files: list[Path] = []
    for current_root, dirs, filenames in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skipped_dirs and not d.startswith(".gradle")]
        root_path = Path(current_root)
        for filename in filenames:
            path = root_path / filename
            try:
                ensure_inside_root(path, project_root)
            except Exception:
                continue
            files.append(path)
            if len(files) >= MAX_SCAN_FILES:
                return files
    return files


def detect_project_profile(project_root: Path, subject: str) -> dict[str, Any]:
    """Suggest build/run metadata; this never executes the detected commands."""
    files = iter_project_files(project_root)
    rel_files = {safe_relative(p, project_root) for p in files}
    names = {p.name for p in files}
    build_systems: list[str] = []
    build_commands: list[str] = []
    run_candidates: list[str] = []
    evidence: list[str] = []
    warnings: list[str] = []
    entry_point: str | None = None

    if "pom.xml" in names:
        build_systems.append("maven")
        build_commands.append("mvn test-compile")
        evidence.append("Found pom.xml; Maven build is likely.")
    if "build.gradle" in names or "gradlew" in names:
        build_systems.append("gradle")
        build_commands.append("./gradlew build")
        evidence.append("Found Gradle build file or wrapper.")
    if "package.json" in names:
        build_systems.append("npm")
        build_commands.append("npm install")
        evidence.append("Found package.json; npm/Node.js project is likely.")
    if "Makefile" in names:
        build_systems.append("make")
        build_commands.append("make")
        evidence.append("Found Makefile.")
    if any(p.suffix == ".py" for p in files):
        build_systems.append("python")
        evidence.append("Found Python source files.")
    if any(p.suffix == ".class" for p in files) or any(p.suffix == ".jar" for p in files):
        build_systems.append("java-classpath")
        evidence.append("Found compiled Java classes or JAR files.")

    main_class = _detect_java_main_class(files)
    if subject == "karatejs" or "karate-js/target/classes/io/karatelabs/js/JsLauncher.class" in rel_files:
        run_candidates.append("java -cp karate-js/target/classes:karate-js/target/dependency/* io.karatelabs.js.JsLauncher {input_file}")
        entry_point = "io.karatelabs.js.JsLauncher"
        evidence.append("Detected KarateJS launcher classpath layout.")
    if main_class:
        run_candidates.append(f"java -cp target/classes {main_class} {{input_file}}")
        entry_point = entry_point or main_class
        evidence.append(f"Found Java main class {main_class}.")
    for path in files:
        if path.name in {"main.py", "cli.py"}:
            run_candidates.append(f"python {safe_relative(path, project_root)} {{input_file}}")
            entry_point = entry_point or safe_relative(path, project_root)
            evidence.append(f"Found likely Python entrypoint {safe_relative(path, project_root)}.")
            break
    if "package.json" in names:
        npm_command = _detect_package_json_command(files) or "npm test -- {input_file}"
        run_candidates.append(npm_command)
        evidence.append(f"Suggested npm command: {npm_command}")
    if not run_candidates:
        run_candidates.append("{command} {input_file}")
        warnings.append("No clear entrypoint detected. User must provide a run command template.")

    readme_hints = _readme_command_hints(files)
    evidence.extend(readme_hints[:5])
    if _has_example_inputs(files):
        evidence.append("Found example/input-like files or folders.")

    language = _detect_language(files, build_systems)
    build_system = _primary_build_system(build_systems)
    confidence = _confidence(run_candidates[0], evidence, warnings)

    return {
        "project_root": str(project_root),
        "language": language,
        "build_system": build_system,
        "build_command": build_commands[0] if build_commands else "",
        "entry_point": entry_point or "",
        "confidence": confidence,
        "evidence": evidence,
        "warnings": warnings,
        "detected_files_sample": sorted(list(rel_files))[:80],
        "build_systems": sorted(set(build_systems)) or ["unknown"],
        "build_commands": build_commands,
        "run_command_template": run_candidates[0],
        "run_command_candidates": run_candidates,
        "input_execution_mode": "file_arg" if "{input_file}" in run_candidates[0] else "stdin",
        "working_directory": str(project_root),
        "timeout_seconds": 15,
    }


def _detect_java_main_class(files: list[Path]) -> str | None:
    for path in files:
        if path.suffix != ".java":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_BYTES]
        except OSError:
            continue
        if "public static void main" not in text:
            continue
        package_match = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE)
        return path.stem if package_match is None else f"{package_match.group(1)}.{path.stem}"
    return None


def _detect_language(files: list[Path], build_systems: list[str]) -> str:
    suffixes = [p.suffix.lower() for p in files]
    if any(bs in build_systems for bs in {"maven", "gradle", "java-classpath"}) or ".java" in suffixes:
        return "Java"
    if "npm" in build_systems or any(s in suffixes for s in {".js", ".ts", ".mjs"}):
        return "JavaScript/Node.js"
    if "python" in build_systems:
        return "Python"
    return "unknown"


def _primary_build_system(build_systems: list[str]) -> str:
    priority = ["maven", "gradle", "npm", "make", "java-classpath", "python"]
    for item in priority:
        if item in build_systems:
            return item
    return "unknown"


def _confidence(command: str, evidence: list[str], warnings: list[str]) -> float:
    if command.startswith("{command}"):
        return 0.2
    score = 0.45 + min(len(evidence), 6) * 0.08 - len(warnings) * 0.08
    return round(max(0.0, min(0.95, score)), 2)


def _detect_package_json_command(files: list[Path]) -> str | None:
    for path in files:
        if path.name != "package.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return None
        scripts = data.get("scripts") or {}
        for name in ("start", "test", "cli"):
            if name in scripts:
                return f"npm run {name} -- {{input_file}}"
    return None


def _readme_command_hints(files: list[Path]) -> list[str]:
    hints: list[str] = []
    for path in files:
        if path.name.lower() not in {"readme.md", "readme.txt", "readme"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_BYTES]
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if any(token in stripped for token in ("java ", "python ", "npm ", "mvn ", "gradle ", "./")):
                hints.append(f"README command hint: {stripped[:160]}")
            if len(hints) >= 5:
                return hints
    return hints


def _has_example_inputs(files: list[Path]) -> bool:
    markers = {"input", "inputs", "examples", "samples", "tests"}
    for path in files:
        parts = {part.lower() for part in path.parts}
        if markers & parts:
            return True
    return False
