# Step 1 – Connect Project: System Design & Hardening Plan

## Context

Step 1 ("Connect Project") is functionally wired but lacked:
- Frontend validation — the form could be submitted with an empty SUT path or the wrong grammar tab active
- Meaningful permission section — the checkboxes were non-functional (backend auto-approves local paths)
- Browse button UX — no loading state during native OS dialog launch (1–2 s freeze)
- Language analysis surfacing — `detect_project_profile()` results were only partially shown in the findings panel
- Input constraint chips — no quick-add shortcuts for common generation constraints

This document captures the design decisions and implementation for the hardening pass.

---

## 1. Frontend Validation Guards

A `validateStep1()` function runs **before** the `fetch()` call in `inspectProject()`. It clears all prior errors, checks each rule, returns `false` (aborting the fetch) on failure. Field-level errors write into `<span class="field-error">` anchors adjacent to each input and add `.input-invalid` (red border) to the failing element.

### Error spans added to `index.html`

| Anchor ID | Placement |
|---|---|
| `sut_location_error` | After `.input-row` div inside SUT field |
| `grammar_location_error` | Inside `#grammar_file_tab` after `.input-row` |
| `grammar_text_error` | Inside `#grammar_paste_tab` after `<textarea>` |

### Rules per grammar tab

| Active tab | Checked field | Error message |
|---|---|---|
| `grammar_file` | `#grammar_location` non-empty | "Enter a grammar file path or URL, or switch to Paste or Infer mode." |
| `grammar_paste` | `#grammar_text` non-empty | "Paste your grammar text above, or switch to Upload or Infer mode." |
| `grammar_later` | — no block — | Inline `.warn-info` notice shown on tab load: "Only LLM generation works without a grammar." |
| SUT (always) | `#sut_location` non-empty | "Project path is required. Enter a local folder path or a GitHub URL." |

---

## 2. Permission Card Redesign

Removed: non-functional `approve_local_read` / `approve_machine_read` checkboxes. These were silently ignored by Pydantic because `InspectRequest` never declared them.

Replaced with an informational trust card:
- "Files within the selected project folder only"
- "The grammar file or text you provide on this screen"
- "SpreadEx never reads outside your project folder, sends files externally, or executes project code during this step."

---

## 3. Language Analysis in Findings Panel

`manifest.sut_analysis` fields (`language`, `build_system`, `confidence`, `entry_point`, `run_command_template`, `run_command_candidates`, `warnings`) are surfaced as typed chat bubbles in `renderFindingsPanel()`:

- **`.chat-bubble.lang`** — always shown, displays language/build/confidence/run template
- **Entry point** — when `profile.entry_point` is set
- **Multiple candidates** — when `run_command_candidates.length > 1`
- **Low-confidence warning** — when `confidence < 0.5`; also auto-opens Advanced settings in Step 3
- **Inspector warnings** — each `profile.warnings[]` entry
- **Grammar adapter confidence** — format name + confidence % + first adapter warning if any

---

## 4. Browse Button UX Fix

Root cause: `/browse/sut` → backend runs `osascript` (macOS native dialog) in subprocess. Button had no loading state during the 1–2 s launch.

Fix: Both browse buttons immediately show "Opening…" (disabled state) on click and restore original `innerHTML` in a `finally` block.

---

## 5. Input Generation Constraints UX

- Improved placeholder with more concrete examples
- Three quick-add `.chip-btn` elements that append text to the `llm_constraints` textarea (semicolon-separated, no duplicates)

---

## 6. Agent Decision

**Verdict: Keep deterministic pipeline. No LLM agent for Step 1.**

The inspection pipeline (`detect_project_profile → read_text_source → analyze_and_adapt_grammar → detect_dependency_readiness`) is fast (<2 s), accurate, and deterministic. No LLM benefit at any stage for this phase.

**Future insertion point (not this phase):** When `confidence < 0.5` and no entry point is found, a README-reading LLM call could infer the run command. Treat as a separate feature request.

---

## Files Changed

| File | Changes |
|---|---|
| `webapp/static/index.html` | Error spans, mine-later `.warn-info` notice, informational permission card, improved placeholder, constraint chips |
| `webapp/static/main.js` | `validateStep1()`, browse loading states, extended `renderFindingsPanel()`, chip listeners, removed vestigial DOM refs |
| `webapp/static/styles.css` | `.field-error`, `.input-invalid`, `.warn-info`, `.chat-bubble.lang`, 2-col permission card, `.permission-list`, `.permission-never`, `.constraint-chips`, `.chip-btn` |

No backend changes required.

---

## Verification Checklist

1. Empty SUT → click Analyze → red border + error message → no network request
2. Upload grammar tab + empty path → error on `#grammar_location` → no request
3. Paste grammar tab + empty textarea → error on `#grammar_text` → no request
4. Mine later tab → `.warn-info` notice visible immediately → Analyze proceeds
5. Fix all fields → errors clear before fetch fires
6. Browse SUT button → "Opening…" while OS dialog open → restores on close
7. Permission card → no checkboxes → bullet list → no console errors
8. Java project inspect → `.chat-bubble.lang` shows language/build/confidence → run command pre-filled
9. Low-confidence project → warn bubble + Advanced settings auto-opens
10. Constraint chips → click appends → second click does not duplicate
11. Full flow (Step 1 → 2 → 3) still completes with `run_id` intact
