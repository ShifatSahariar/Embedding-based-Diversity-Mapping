# Agentic SpreadEx Setup Plan

## Summary
SpreadEx tool mode now uses a two-agent setup stage before generation and execution:

- SUT Analysis Agent: inspects the selected project and proposes build/run metadata without executing commands.
- Grammar Adapter Agent: detects the provided grammar format and prepares run-local grammar assets for selected generator families.

The user reviews both findings, edits the detected command/setup if needed, and explicitly approves before the full run starts.

## Generator Families
The UI exposes four generator families:

- FuzzingBook
- Fandango
- ISLa
- LLM Generator

For v1, these map to existing internal generator modes:

- `fuzzingbook` -> `fuzz_equal`
- `fandango` -> `fan_no_con`
- `isla` -> `isla_no_con`
- `llm` -> `openai_gram` when grammar exists, otherwise `openai_no_gram`

## Setup Reports
Inspection writes these run-local reports under `webapp_runs/{run_id}/`:

- `sut_analysis_report.json`
- `grammar_adapter_report.json`
- `inspection_report.json`
- `project_manifest.json`

Adapted grammar files are written under:

- `webapp_runs/{run_id}/adapted_grammars/`

## v1 Assumptions
- Grammar conversion is heuristic and local; LLM-assisted conversion is deferred.
- Probability editing for FuzzingBook is deferred.
- Fandango and ISLa constraints are optional; unsupported constraints produce warnings.
- Artifact reproduction scripts remain untouched.
