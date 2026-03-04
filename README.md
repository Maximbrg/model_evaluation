# Multi-Agent Language/Model Evaluation Framework

This repository contains a LangGraph-based framework for orchestrating multiple AI agents to evaluate models and text inputs against customized semantic logic and taxonomies.

## Core Agents:
- **Agent 1 (Interpreter):** Understands the strict semantic rules from the metamodel.
- **Agent 2 (Analyzer & Refiner):** Generates guidelines, checks constraint evaluations against syntax, and communicates with Agent 1.
- **Agent 3 (Reasoner):** Executes cases against constraints.
- **Agent 4 (Orchestrator & Classifier):** Routes tasks between Agents 1-3, coordinates looping processes, and builds the final variability taxonomy.

## Quick-Start
Modify `config.yaml` to specify your `api_key`, then run:
```bash
python multi_agent/main.py
```
Outputs and final CSVs are generated locally in `outputs/`.
