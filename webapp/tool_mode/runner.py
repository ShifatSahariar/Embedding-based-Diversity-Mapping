"""Confirmed command execution and smoke testing for tool mode."""

import shlex
import subprocess
from pathlib import Path
from typing import Any


def run_sut_command(
    command_template: str,
    input_file: Path,
    working_directory: Path,
    input_execution_mode: str,
    timeout: int = 15,
) -> dict[str, Any]:
    """Execute only after UI confirmation; inspection never calls this."""
    command_text = command_template.replace("{input_file}", str(input_file))
    args = shlex.split(command_text)
    stdin_text = None
    if input_execution_mode == "stdin":
        stdin_text = input_file.read_text(encoding="utf-8", errors="ignore")
    try:
        completed = subprocess.run(
            args,
            cwd=str(working_directory),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "return_code": None, "stdout": "", "stderr": "Timeout expired."}

    stdout = completed.stdout[-4000:]
    stderr = completed.stderr[-4000:]
    looks_like_usage = "usage:" in stdout.lower()[:500] or "usage:" in stderr.lower()[:500]
    return {
        "ok": completed.returncode == 0 and not looks_like_usage,
        "return_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "looks_like_usage": looks_like_usage,
    }

