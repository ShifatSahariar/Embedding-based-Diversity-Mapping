# Replication Package  
## Embedding-based Diversity Mapping for Test Generator Selection and Input Prioritization in Grammar-based Testing

This repository contains the replication package for the ICST 2026 paper:

> Embedding-based Diversity Mapping for Test Generator Selection and Input Prioritization in Grammar-based Testing  
> (accepted at ICST 2026)

This artifact supports:

1. **Result Inspection (Fast Path)**  
   Users can directly inspect the experimental results reported in the paper without re-running the pipeline.

2. **Full Reproduction (From Scratch)**  
   Users can reproduce the complete experimental workflow, including generator selection, diversity mapping, and input prioritization.

The package enables the reproduction of all experiments reported in the paper,
including generator selection, diversity analysis, and budget-aware input prioritization.
---
## Overview

We present and evaluate a two-phase diversity-driven testing pipeline for grammar-based systems:

1. **Generator Selection**  
   Grammar-generated inputs are embedded and clustered to construct diversity maps.  
   Generator effectiveness is assessed using *Cluster Coverage (CC)*.

2. **Input Prioritization**  
   Inputs from the selected generator are prioritized under increasing budgets using the deterministic **SpreadEx** strategy.

The pipeline is evaluated on multiple grammar-based interpreters using mutation testing.

---

## Repository Structure


## Overview
We evaluate a two-phase diversity-based testing pipeline:
1. Generator selection using diversity maps (Cluster Coverage)
2. Budget-aware input prioritization using SpreadEx

## Repository Structure

```tree
.
├── data/
│   ├── Generator_Selection_Results/
│   └── Input_Prioritization_Results/
│   └── Paper-Figure_plots/
│
├── docs/
│   ├── phase1_generator_selection.md
│   ├── phase2_input_prioritization.md
│   └── data_format_and_interpretation.md
│
├── ..# experiment scripts and utilities
│
├── requirements.txt
└── README.md
```
### ✔️ Verify Results (Recommended)
### 📂 `data/` — Experimental Results (Verification)
## Quick Start
If you only want to inspect and validate the results reported in the paper:

1. Navigate to the `data/` directory  
2. Follow the instructions in: docs/data_format_and_interpretation.md


This directory contains all **processed experimental results** reported in the
paper, organized by evaluation phase.

- Results corresponding to **Phase 1 (Generator Selection)**  
- Results corresponding to **Phase 2 (Input Prioritization)**  
- Aggregated statistics, tables, and values used to generate figures

➡️ **No execution is required** to inspect or validate the results.

---


### 📄 `docs/` — Reproduction Instructions

This directory contains **step-by-step documentation** for reproducing the
experiments from scratch, including:

- Phase-specific execution instructions  
- Required configuration details  
- Execution order and expected outputs  

Start here if you want to **re-run the experiments**, rather than only inspect
the reported results.
Key documents:
- [Phase 1: Generator Selection](docs/phase1_generator_selection.md)
- [Phase 2: Input Prioritization](docs/phase2_input_prioritization.md)

### 🔁 Reproduce Experiments (From Scratch)
We recommend using an IDE (e.g., PyCharm or VS Code) for convenience, although all scripts can also be executed via the command line.

If you want to re-run the experiments:

1. Create and activate a Python environment:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Verify the required runtimes:
```bash
python --version
java -version
```

## Requirements

- Python >= 3.10
- Java >= 17
- Python packages listed in `requirements.txt`
- PIT command-line jars, PIT JUnit 5 plugin, and JUnit runtime jars for mutation generation
- JaCoCo jars for coverage analysis

## Java Tool Setup

The scripts use fixed local paths for Java coverage and mutation tools:

- JaCoCo agent/CLI: `COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/`
- PIT command-line jars: `MUT_KILLING_PROFILE/pit_mut_tool/`

JaCoCo jars are included in this artifact under `COVERAGE_REPORTS/COVERAGE_TOOLS/Jacoco/`.
If you replace or reinstall them, keep `jacocoagent.jar` and `jacococli.jar` at those paths because the coverage helpers reference those filenames directly.

PIT jars must be placed in `MUT_KILLING_PROFILE/pit_mut_tool/`. The mutation-generation code builds the Java classpath from `MUT_KILLING_PROFILE/pit_mut_tool/*`, so the directory should contain the PIT command-line jar, PIT runtime jars, the PIT JUnit 5 plugin, and the JUnit runtime jars needed to discover tests. See the official PIT command-line quickstart for the required command-line distribution jars: https://pitest.org/quickstart/commandline

If Maven is available, the included `pitest-runtime-pom.xml` can fetch the required PIT and JUnit runtime jars:

```bash
mvn -Dmaven.repo.local=.m2/repository \
  -f pitest-runtime-pom.xml \
  org.apache.maven.plugins:maven-dependency-plugin:3.7.0:copy-dependencies \
  -DoutputDirectory=MUT_KILLING_PROFILE/pit_mut_tool \
  -DincludeScope=runtime
```

The temporary `.m2/` cache created by this command does not need to be archived with the artifact.

Example layout:
```tree
MUT_KILLING_PROFILE/
└── pit_mut_tool/
    ├── pitest-command-line-<version>.jar
    ├── pitest-<version>.jar
    ├── pitest-entry-<version>.jar
    ├── pitest-junit5-plugin-<version>.jar
    ├── junit-jupiter-engine-<version>.jar
    ├── junit-platform-launcher-<version>.jar
    └── ...
```

After the Python and Java dependencies are installed, follow the phase-specific reproduction instructions:

- [Phase 1: Generator Selection](docs/phase1_generator_selection.md)
- [Phase 2: Input Prioritization](docs/phase2_input_prioritization.md)
