"""FastAPI routes for the SpreadEx agentic tool-mode UI."""

import json
import platform
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from webapp.tool_mode.dependency_checker import detect_dependency_readiness
from webapp.tool_mode.config import (
    GENERATOR_FAMILIES,
    MODEL_OPTIONS,
    PROVIDER_BY_MODEL,
    RUNS_ROOT,
    STATIC_ROOT,
    TOOL_MODE_NATIVE_BROWSE_ENABLED,
)
from webapp.tool_mode.errors import ToolModeError
from webapp.tool_mode.grammar_adapter import analyze_and_adapt_grammar, map_families_to_internal_modes
from webapp.tool_mode.grammar_validator import read_text_source
from webapp.tool_mode.pipeline import execute_run
from webapp.tool_mode.project_inspector import detect_project_profile
from webapp.tool_mode.schemas import InspectRequest, RunRequest
from webapp.tool_mode.security import (
    clone_git_project,
    ensure_inside_allowed_scope,
    is_git_url,
    safe_resolve_local_path,
    validate_subject_key,
)
from webapp.tool_mode.storage import RunState, read_run_json, safe_mkdir, utc_now, write_run_json


app = FastAPI(title="SpreadEx Tool UI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/ui", StaticFiles(directory=str(STATIC_ROOT), html=True), name="ui")


@app.middleware("http")
async def redirect_legacy_ui_route(request, call_next):
    if request.url.path in {"/ui", "/ui/"}:
        return RedirectResponse(url="/spreadex", status_code=307)
    return await call_next(request)


@app.get("/spreadex")
@app.get("/spreadex/")
def spreadex_dashboard():
    return FileResponse(STATIC_ROOT / "index.html")

RUNS: dict[str, RunState] = {}
RUNS_LOCK = threading.Lock()


@app.get("/api/options")
def get_options():
    return {
        "generators": list(GENERATOR_FAMILIES.keys()),
        "generator_families": GENERATOR_FAMILIES,
        "models": MODEL_OPTIONS,
        "providers": PROVIDER_BY_MODEL,
        "native_browse_enabled": TOOL_MODE_NATIVE_BROWSE_ENABLED,
        "upload_mode": {
            "supported": False,
            "placeholder_endpoint": "/api/uploads/scaffold",
        },
    }


@app.post("/api/inspect")
def inspect_project(request: InspectRequest):
    """Inspect project/grammar and write manifests; no project command is executed here."""
    try:
        subject = validate_subject_key(request.subject)
        location = request.sut_location.strip()
        if not location:
            raise ToolModeError("SUT location is required.")

        run_id = uuid.uuid4().hex[:12]
        run_root = RUNS_ROOT / run_id
        workspace = run_root / "workspace"
        safe_mkdir(workspace)

        if is_git_url(location):
            project_root = clone_git_project(location, workspace)
            source_kind = "git"
        else:
            project_root = safe_resolve_local_path(location)
            if not project_root.is_dir():
                raise ToolModeError("SUT location must be a directory.")
            source_kind = "local"

        profile = detect_project_profile(project_root, subject)

        all_families = list(GENERATOR_FAMILIES.keys())
        if request.grammar_mine_later:
            grammar_text = None
            grammar_meta = {"source": "mine_later", "format": "none"}
            grammar_report = analyze_and_adapt_grammar(
                run_id=run_id,
                grammar_text=None,
                grammar_meta=grammar_meta,
                selected_generators=all_families,
                llm_constraints=request.llm_constraints,
            )
        else:
            grammar_text, grammar_meta = read_text_source(
                request.grammar_location,
                request.grammar_text,
                project_root,
                machine_read_approved=False,
            )
            grammar_report = analyze_and_adapt_grammar(
                run_id=run_id,
                grammar_text=grammar_text,
                grammar_meta=grammar_meta,
                selected_generators=all_families,
                llm_constraints=request.llm_constraints,
            )
        dependency_report = detect_dependency_readiness(profile, grammar_report)
    except ToolModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    manifest = _build_manifest(
        run_id=run_id,
        subject=subject,
        source_kind=source_kind,
        sut_location=location,
        project_root=project_root,
        grammar_meta=grammar_meta,
        profile=profile,
        grammar_report=grammar_report,
        dependency_report=dependency_report,
    )
    inspection_report = {
        "sut_analysis": profile,
        "grammar_analysis": grammar_report,
        "dependency_readiness": dependency_report,
    }
    write_run_json(run_id, "project_manifest.json", manifest)
    write_run_json(run_id, "inspection_report.json", inspection_report)
    write_run_json(run_id, "sut_analysis_report.json", profile)
    write_run_json(run_id, "grammar_adapter_report.json", grammar_report)
    _write_run_grammar(run_root, grammar_text, grammar_report)

    state = RunState(run_id=run_id, created_at=manifest["created_at"], status="inspected", step="inspection_complete")
    state.config = {
        "subject": subject,
        "source_kind": source_kind,
        "approved_project_root": str(project_root),
        "selected_generator_families": grammar_report.get("selected_generators", []),
    }
    state.outputs = inspection_report
    with RUNS_LOCK:
        RUNS[run_id] = state
    return manifest


@app.post("/api/fs/list")
def browse_local_fs(payload: dict[str, Any]):
    """List local directories/files to support path browsing in Step 1."""
    location = str(payload.get("location") or "").strip()
    if not location:
        location = str(Path.home())

    try:
        base = safe_resolve_local_path(location)
    except ToolModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Browse location must be a directory.")

    entries: list[dict[str, Any]] = []
    try:
        for child in sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:200]:
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "is_dir": child.is_dir(),
                    "is_file": child.is_file(),
                }
            )
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Unable to browse directory: {exc}") from exc

    parent = str(base.parent) if base.parent != base else None
    return {"location": str(base), "parent": parent, "entries": entries}


@app.post("/api/fs/pick")
def pick_local_path(payload: dict[str, Any]):
    """Open a native file/folder picker on the server machine for local-tool UX."""
    mode = str(payload.get("mode") or "").strip().lower()
    if mode not in {"file", "directory"}:
        raise HTTPException(status_code=400, detail="Pick mode must be 'file' or 'directory'.")

    initial = str(payload.get("initial") or "").strip()
    initial_dir = None
    if initial:
        try:
            p = safe_resolve_local_path(initial)
            initial_dir = str(p if p.is_dir() else p.parent)
        except ToolModeError:
            initial_dir = str(Path.home())

    selected = _pick_with_native_dialog(mode, initial_dir)
    if selected is None:
        selected = _pick_with_tkinter(mode, initial_dir)

    if not selected:
        return {"selected": None}
    return {"selected": str(Path(selected).resolve())}


@app.post("/browse/sut")
def browse_sut(payload: dict[str, Any] | None = None):
    if not TOOL_MODE_NATIVE_BROWSE_ENABLED:
        raise HTTPException(status_code=403, detail="Native browse is disabled in hosted/public mode.")
    initial_dir = _resolve_initial_dir((payload or {}).get("initial"))
    selected = _pick_with_native_dialog("directory", initial_dir)
    if selected is None:
        selected = _pick_with_tkinter("directory", initial_dir)
    if selected is None:
        raise HTTPException(status_code=400, detail="Native folder picker is unavailable in this runtime.")
    return {"path": str(Path(selected).resolve()) if selected else None}


@app.post("/browse/grammar")
def browse_grammar(payload: dict[str, Any] | None = None):
    if not TOOL_MODE_NATIVE_BROWSE_ENABLED:
        raise HTTPException(status_code=403, detail="Native browse is disabled in hosted/public mode.")
    initial_dir = _resolve_initial_dir((payload or {}).get("initial"))
    selected = _pick_with_native_dialog("file", initial_dir)
    if selected is None:
        selected = _pick_with_tkinter("file", initial_dir)
    if selected is None:
        raise HTTPException(status_code=400, detail="Native file picker is unavailable in this runtime.")
    return {"path": str(Path(selected).resolve()) if selected else None}


@app.post("/api/uploads/scaffold")
def upload_mode_scaffold():
    return JSONResponse(
        status_code=501,
        content={
            "message": "Mode A upload flow is not implemented yet.",
            "planned": {
                "sut_multipart_field": "sut_files[]",
                "grammar_multipart_field": "grammar_file",
                "workspace_root_pattern": "runs/<run_id>/sut/",
            },
        },
    )


def _pick_with_native_dialog(mode: str, initial_dir: str | None) -> str | None:
    system = platform.system()
    if system != "Darwin":
        return None

    # Use Finder-native dialogs first on macOS; this works better than tkinter in many envs.
    if mode == "directory":
        script = 'POSIX path of (choose folder with prompt "Select SUT Folder")'
    else:
        script = 'POSIX path of (choose file with prompt "Select Grammar File")'
    if initial_dir:
        script = script.replace(")", f' default location (POSIX file "{initial_dir}"))', 1)

    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception:
        return None

    if completed.returncode != 0:
        # User cancel typically returns a non-zero AppleScript code.
        return ""
    return completed.stdout.strip()


def _resolve_initial_dir(initial_value: Any) -> str | None:
    initial = str(initial_value or "").strip()
    if not initial:
        return None
    try:
        p = safe_resolve_local_path(initial)
        return str(p if p.is_dir() else p.parent)
    except ToolModeError:
        return str(Path.home())


def _pick_with_tkinter(mode: str, initial_dir: str | None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.update()
        if mode == "directory":
            selected = filedialog.askdirectory(initialdir=initial_dir or str(Path.home()), title="Select SUT Folder")
        else:
            selected = filedialog.askopenfilename(
                initialdir=initial_dir or str(Path.home()),
                title="Select Grammar File",
                filetypes=[
                    ("Grammar/Text", "*.bnf *.ebnf *.isla *.fan *.py *.txt"),
                    ("All files", "*.*"),
                ],
            )
        root.destroy()
        return selected
    except Exception:
        return None


@app.post("/api/runs")
async def create_run(background_tasks: BackgroundTasks, request: RunRequest):
    manifest_path = RUNS_ROOT / request.run_id / "project_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Run inspection manifest not found. Inspect project first.")

    manifest = read_run_json(request.run_id, "project_manifest.json")
    config = _validate_run_request(request, manifest)
    state = RUNS.get(request.run_id) or RunState(run_id=request.run_id, created_at=utc_now())
    state.status = "queued"
    state.step = "queued"
    state.logs = []
    state.config = config
    state.outputs = {}
    state.error = None
    with RUNS_LOCK:
        RUNS[request.run_id] = state

    background_tasks.add_task(_execute_run_threadsafe, request.run_id, request.openai_api_key, request.codestral_api_key)
    return {"run_id": request.run_id, "status": "queued"}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with RUNS_LOCK:
        state = RUNS.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {
        "run_id": state.run_id,
        "created_at": state.created_at,
        "status": state.status,
        "step": state.step,
        "logs": state.logs[-300:],
        "config": state.config,
        "outputs": state.outputs,
        "error": state.error,
    }


@app.get("/api/runs/{run_id}/download")
def download_prioritized_zip(run_id: str):
    zip_path = RUNS_ROOT / run_id / "outputs" / "prioritized_inputs.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Output ZIP not found.")
    return FileResponse(str(zip_path), media_type="application/zip", filename="prioritized_inputs.zip")


@app.get("/api/health")
def health():
    return JSONResponse({"ok": True, "timestamp": utc_now()})


def _build_manifest(
    run_id: str,
    subject: str,
    source_kind: str,
    sut_location: str,
    project_root: Path,
    grammar_meta: dict[str, Any],
    profile: dict[str, Any],
    grammar_report: dict[str, Any],
    dependency_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": utc_now(),
        "subject": subject,
        "source_kind": source_kind,
        "sut_location": sut_location,
        "approved_project_root": str(project_root),
        "grammar": grammar_meta,
        "project_profile": profile,
        "sut_analysis": profile,
        "grammar_validation": grammar_report,
        "grammar_analysis": grammar_report,
        "adapted_grammars": grammar_report.get("adapted_grammars", {}),
        "dependency_readiness": dependency_report,
        "security": {
            "commands_require_confirmation": True,
            "path_root_restriction": str(project_root),
        },
    }


def _write_run_grammar(run_root: Path, grammar_text: str | None, grammar_report: dict[str, Any]) -> None:
    if not grammar_text:
        return
    grammar_dir = run_root / "grammars"
    safe_mkdir(grammar_dir)
    ext = grammar_report.get("format") or "txt"
    (grammar_dir / f"grammar.{ext}").write_text(grammar_text, encoding="utf-8")


def _validate_run_request(request: RunRequest, manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        if request.embedding_model.lower() not in MODEL_OPTIONS:
            raise ToolModeError("Unsupported embedding model.")
        if request.prioritization_budget <= 0:
            raise ToolModeError("prioritization_budget must be > 0.")
        if request.input_execution_mode == "file_arg" and "{input_file}" not in request.run_command_template:
            raise ToolModeError("Run command must include {input_file} for file-arg mode.")

        grammar_analysis = manifest["grammar_analysis"]
        compat = grammar_analysis.get("generator_status", {})

        # Resolve generator list: empty or auto_select → use all compatible families
        if not request.generators or request.auto_select_generator:
            compatible_families = [
                f for f in GENERATOR_FAMILIES
                if compat.get(f, {}).get("compatible", False)
            ]
            # In auto mode with a grammar available, prefer non-LLM generators if no API key
            if not request.openai_api_key and compatible_families != ["llm"]:
                non_llm = [f for f in compatible_families if f != "llm"]
                compatible_families = non_llm if non_llm else compatible_families
            selected_families = compatible_families or list(GENERATOR_FAMILIES.keys())
            generator_selection_mode = "auto_cc"
        elif len(request.generators) == 1:
            selected_families = request.generators
            generator_selection_mode = "single"
        else:
            selected_families = request.generators
            generator_selection_mode = "cc"

        for family in selected_families:
            if family not in GENERATOR_FAMILIES:
                raise ToolModeError(f"Unsupported generator family: {family}")

        has_grammar = grammar_analysis.get("original_format") not in ("unknown", "none", None)
        internal_generators = map_families_to_internal_modes(selected_families, has_grammar)

        provider = PROVIDER_BY_MODEL[request.embedding_model.lower()]
        uses_openai_generator = any(gen.startswith("openai") for gen in internal_generators)
        if (provider == "openai" or uses_openai_generator) and not request.openai_api_key:
            raise ToolModeError("OPENAI API key required for OpenAI model or generator.")
        if provider == "codestral" and not request.codestral_api_key:
            raise ToolModeError("MISTRAL API key required for codestral model.")

        project_root = Path(manifest["approved_project_root"]).resolve(strict=True)
        working_directory = Path(
            request.working_directory or manifest["project_profile"]["working_directory"]
        ).expanduser()
        ensure_inside_allowed_scope(working_directory, project_root, False)
    except ToolModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "subject": manifest["subject"],
        "generator_families": selected_families,
        "generators": internal_generators,
        "generator_selection_mode": generator_selection_mode,
        "adapted_grammars": manifest.get("adapted_grammars", {}),
        "embedding_model": request.embedding_model.lower(),
        "provider": provider,
        "prioritization_budget": request.prioritization_budget,
        "num_inputs_per_generator": request.num_inputs_per_generator,
        "run_command_template": request.run_command_template,
        "input_execution_mode": request.input_execution_mode,
        "working_directory": str(working_directory),
        "approved_project_root": str(project_root),
        "openai_api_key_masked": _mask_secret(request.openai_api_key),
        "codestral_api_key_masked": _mask_secret(request.codestral_api_key),
    }


def _execute_run_threadsafe(run_id: str, openai_api_key: str | None, codestral_api_key: str | None) -> None:
    with RUNS_LOCK:
        state = RUNS[run_id]

    def set_step(step: str) -> None:
        with RUNS_LOCK:
            state.step = step

    def log(msg: str) -> None:
        with RUNS_LOCK:
            state.log(msg)

    execute_run(state, openai_api_key, codestral_api_key, set_step, log)


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) < 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"
