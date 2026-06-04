"""Dependency readiness detection for project and generator execution."""

import shutil
from typing import Any


def detect_dependency_readiness(project_profile: dict[str, Any], grammar_report: dict[str, Any]) -> dict[str, Any]:
    commands = {
        "java": shutil.which("java"),
        "mvn": shutil.which("mvn"),
        "gradle": shutil.which("gradle"),
        "npm": shutil.which("npm"),
        "python": shutil.which("python") or shutil.which("python3"),
        "fandango": shutil.which("fandango"),
        "isla": shutil.which("isla"),
        "git": shutil.which("git"),
    }
    needs: list[str] = []
    build_systems = set(project_profile.get("build_systems", []))
    if "maven" in build_systems and not commands["mvn"]:
        needs.append("Maven not found in PATH.")
    if "gradle" in build_systems and not commands["gradle"]:
        needs.append("Gradle not found in PATH.")
    if "npm" in build_systems and not commands["npm"]:
        needs.append("npm not found in PATH.")
    if any(bs in build_systems for bs in {"java-classpath", "maven", "gradle"}) and not commands["java"]:
        needs.append("Java not found in PATH.")
    selected = set(grammar_report.get("selected_generators", []))
    if "fandango" in selected and not commands["fandango"]:
        needs.append("Fandango not found in PATH.")
    if "isla" in selected and not commands["isla"]:
        needs.append("ISLa not found in PATH.")

    return {
        "commands": {key: bool(value) for key, value in commands.items()},
        "needs": needs,
        "status": "ready" if not needs else "needs_install",
    }
