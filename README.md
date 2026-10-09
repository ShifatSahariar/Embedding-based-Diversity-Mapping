# Embedding-based Diversity Mapping — replication package

<p align="center">
  <img src="research/docs/assets/spreadex_logo.png" alt="SpreadEx logo" width="620">
</p>

This repository is the replication package for:

> **Embedding-based Diversity Mapping for Test Generator Selection and Input Prioritization in Grammar-based Testing**  
> Accepted at ICST 2026

It contains the research code, data and step-by-step guides behind the paper: test inputs are embedded, a diversity map is built by clustering, and that map is used to select the best test generator or to prioritize a budget-aware subset of inputs.

The full artifact archive (all subject programs, raw results, pre-computed data) is on Zenodo: [https://doi.org/10.5281/zenodo.20071065](https://doi.org/10.5281/zenodo.20071065)

> **The SpreadEx tool now lives in its own repository:** [github.com/ShifatSahariar/SpreadEx](https://github.com/ShifatSahariar/SpreadEx).
> SpreadEx is the standalone Workbench that brings this approach to your own system under test. This repository is research-only: it was moved here from that address in 2026, with its full history, and the earlier prototype web tool (`webapp/`) was removed from it. That prototype remains in this repository's history.

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

---

## Repository Structure

```
.
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
