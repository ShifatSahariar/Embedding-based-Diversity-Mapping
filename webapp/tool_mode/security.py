"""Security helpers for local/Git project access in tool mode."""

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from .errors import ToolModeError
from .storage import safe_mkdir

SUBJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")


def validate_subject_key(subject: str) -> str:
    subject_norm = subject.strip().lower()
    if not SUBJECT_PATTERN.match(subject_norm):
        raise ToolModeError("Subject key must use lowercase letters, numbers, '-' or '_' and be at most 50 chars.")
    return subject_norm


def is_git_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "ssh", "git"} or value.startswith("git@")


def safe_resolve_local_path(value: str) -> Path:
    path = Path(value).expanduser()
    try:
        return path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ToolModeError(f"Path does not exist: {value}") from exc


def ensure_inside_root(candidate: Path, root: Path) -> Path:
    """Keep all local reads and execution working directories inside the approved project root."""
    resolved = candidate.resolve(strict=True)
    root_resolved = root.resolve(strict=True)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ToolModeError("Path escapes approved project root.")
    return resolved


def ensure_inside_allowed_scope(candidate: Path, approved_root: Path, machine_read_approved: bool) -> Path:
    """Restrict local reads to project root unless user explicitly approves machine-level access."""
    resolved = candidate.resolve(strict=True)
    if machine_read_approved:
        return resolved
    return ensure_inside_root(resolved, approved_root)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def clone_git_project(git_url: str, workspace_dir: Path) -> Path:
    if shutil.which("git") is None:
        raise ToolModeError("Git is not installed or not in PATH.")
    target_dir = workspace_dir / "repo"
    safe_mkdir(workspace_dir)
    command = ["git", "clone", "--depth", "1", git_url, str(target_dir)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as exc:
        raise ToolModeError(f"Git clone failed: {exc.stderr[-1000:]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolModeError("Git clone timed out.") from exc
    return target_dir.resolve(strict=True)
