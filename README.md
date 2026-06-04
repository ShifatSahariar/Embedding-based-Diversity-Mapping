# SpreadEx

<p align="center">
  <img src="research/docs/assets/spreadex_logo.png" alt="SpreadEx logo" width="620">
</p>

**SpreadEx** is a tool for diversity-driven test input selection in grammar-based testing. It embeds test inputs, builds a diversity map via clustering, and uses that map to either select the best test generator or prioritize a budget-aware subset of inputs.

This repository also serves as the replication package for:

> **Embedding-based Diversity Mapping for Test Generator Selection and Input Prioritization in Grammar-based Testing**  
> Accepted at ICST 2026

The full artifact archive (all subject programs, raw results, pre-computed data) is on Zenodo: [https://doi.org/10.5281/zenodo.20071065](https://doi.org/10.5281/zenodo.20071065)

---

## Getting Started

### Requirements

- Python >= 3.10
- An OpenAI API key (for embedding-based features)

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Launch the Tool

```bash
python -m webapp.run
```

Then open:

- **UI:** [http://localhost:8010/ui](http://localhost:8010/ui)
- **API health:** [http://localhost:8010/api/health](http://localhost:8010/api/health)

---

## Tool Workflow

SpreadEx walks you through five steps in the browser UI:

1. **Connect a project** — provide a local path, mounted workspace, or Git URL for your system under test.
2. **Inspect metadata** — review build/run commands and grammar compatibility.
3. **Configure generation** — pick compatible grammar-based generators and an embedding model.
4. **Smoke test** — run a quick sanity check before committing to full generation.
5. **Run & export** — SpreadEx runs generator selection or input prioritization and exports `prioritized_inputs.zip`.

### Security notes

- API keys are session-scoped and never written to disk in plaintext.
- Local paths require explicit approval and are sandboxed to the approved root.
- All detected commands are previewed and require confirmation before execution.

---

## Repository Structure

```
.
├── webapp/                  # Tool implementation (web app + API)
│   ├── run.py               # Entry point
│   ├── backend.py           # FastAPI application
│   ├── tool_mode/           # Core pipeline logic
│   └── static/              # Frontend (HTML/JS/CSS)
│
├── research/                # Replication package for the ICST 2026 paper
│   ├── docs/                # Step-by-step reproduction guides
│   ├── data/                # Pre-computed results and paper figures
│   ├── SUT/                 # Lightweight subject programs (KarateJS, basic)
│   ├── Generation_Test_Inputs.py
│   ├── Generation_Embeddings.py
│   ├── Cluster_Coverage.py
│   ├── Mutation_Analysis.py
│   └── ...                  # Other Phase 1 / Phase 2 scripts
│
├── requirements.txt
└── README.md
```

---

## Reproducing the Paper Results

All scripts, data, and documentation for reproducing the ICST 2026 paper are in [`research/`](research/).

### Quick result inspection (no execution needed)

1. Open [`research/data/`](research/data/).
2. Read [`research/docs/data_format_and_interpretation.md`](research/docs/data_format_and_interpretation.md).
3. Browse the Phase 1 and Phase 2 result folders.

### Full reproduction from scratch

Additional requirements: Java >= 17, JaCoCo jars, PIT jars (see [`research/docs/`](research/docs/) for setup).

Follow the phase guides:

- [Phase 1: Generator Selection](research/docs/phase1_generator_selection.md)
- [Phase 2: Input Prioritization](research/docs/phase2_input_prioritization.md)

The complete dataset is on Zenodo: [https://doi.org/10.5281/zenodo.20071065](https://doi.org/10.5281/zenodo.20071065)
