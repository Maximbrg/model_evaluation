# Model Evaluation Framework - LangGraph Orchestrator

This framework coordinates a multi-agent system to evaluate domain-specific models (e.g., Use Case Diagrams, Class Diagrams) against strict metamodels and compliance guidelines. It uses **LangGraph** to manage the state and transitions between agents.

---

## 📋 Requirements & Installation

### 1. Prerequisites
- **Python 3.10+** (Python 3.13 is recommended and tested).
- An **OpenAI API Key** with access to GPT-4o or GPT-4o-mini.

### 2. Setup Environment
Clone the repository and create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install langgraph langchain-core openai pyyaml requests
```

---

## 🛠️ Configuration (`config.yaml`)

The system is controlled by `multi_agent/compliance_core/config.yaml`. Below is a typical example for evaluating **Use Case Diagrams**:

```yaml
openai:
  api_key: "YOUR_OPENAI_API_KEY"
  model: "o4-mini"  # or gpt-4o

inputs:
  # General language info
  language_name: "Use Case Diagram"
  language_formal_definition_path: "grammar" # Keyword for internal logic
  
  # Domain info
  domain_identifier: "ParkWise"
  domain_description_path: "artifacts/parkWise/ParkWise-Description.txt"
  
  # Target models to evaluate
  cases_dir: "artifacts/parkWise/ucd_2"

execution:
  # Pointer to the prompts file
  prompts_file: "../../artifacts/prompts/prompts_9.yaml"
  
  # MODE:
  # 1: Full run (Stage 1 -> 2 -> 3)
  # 2: Resume from Stage 2 (Drafting Guidelines) - Requires language_template_path
  # 3: Resume from Stage 3 (Compliance Check)  - Requires reference_guidelines_path
  mode: 2
  
  # STOP AFTER:
  # Set to 2 to stop after generating/refining stage 2 guidelines.
  # Set to null for a complete run.
  stop_after_stage: 2
  
  phase2_inputs:
    language_template_path: "artifacts/stable_output_stage_1/stable_ucd_lang_temp.json"

  # Iteration limits
  max_stage2_refinement_iterations: 3
  max_case_iterations: 5
```

---

## 🏃 How to Run `graph2.py` for the First Time

1. **Verify your API Key**: Ensure your key is in `config.yaml`.
2. **Set the Mode**: 
   - If you want the system to understand the language from scratch, set `mode: 1`.
   - If you want to use a pre-existing language template (faster), set `mode: 2` and ensure `language_template_path` is correct.
3. **Execute**:
   Run the graph script from the root directory:
   ```bash
   python multi_agent/compliance_core/graph2.py
   ```
4. **Monitor**:
   - The terminal will log 🔄 transitions between nodes (e.g., `agent2_develop_guidelines`, `agent1_answer_question`).
   - Detailed logs and snapshots are saved in `multi_agent/compliance_core/outputs/[TIMESTAMP]/`.

---

## 📂 Artifacts Explanation

The `artifacts/` directory contains the foundational logic used by the agents.

| Artifact | Description |
| :--- | :--- |
| `metamodel_ucd.txt` | The formal rules for **Use Case Diagrams**. Defines what is a valid Actor, Use Case, Association, etc. |
| `metamodel_cd.txt` | The formal rules for **Class Diagrams**. Defines Classes, Attributes, and Relationships. |
| `prompts/prompts_9.yaml` | The heart of the system. Contains structured instructions for each Agent stage (Language Advising, Guideline Drafting, Compliance Labeling). |
| `parkWise/` | A sample dataset for an automated parking system. Includes the textual description and several "Case" diagrams (as PlantUML text). |
| `stable_output_stage_1/` | Contains pre-processed JSON templates of the languages. Using these in `mode: 2` saves time and API costs. |

---

## 📊 Outputs & Tracking

Every run creates a timestamped folder in `multi_agent/compliance_core/outputs/` containing:
- **`final_reference_guidelines.json`**: The absolute latest version of the reference guidelines, enriched with system capabilities. This is saved at the top level for easy access.
- **`transition_logs.txt`**: A full textual log of every LLM interaction, including system prompts, user prompts, and raw outputs.
- **`stage2_agent2_domain/iterations/`**: Contains a numbered snapshot of the guidelines after every refinement iteration (e.g., `reference_guidelines_iter_1.json`).
- **`stage3_agent3_compliance/`**:
    - `final_compliance_vector.json`: The evaluation output for each case model.
    - `guideline_change_tracker.json`: A JSON list of all modifications made during Stage 3/4 rethinking.
- **`interaction_log.json`**: A structured JSON trace for analysis of node transitions across the entire execution.

---

## ⚠️ Troubleshooting

- **Python Version**: Ensure you use Python 3.10+, preferably 3.13. Older versions might have compatibility issues with `langgraph`.
- **API Key Errors**: Double-check that `openai.api_key` in `config.yaml` is valid and has sufficient credits.
- **Langgraph Version**: If you see errors about "proxy" keywords in `openai`, ensure your `langgraph` and `openai` libraries are up to date.
- **Node Not Reachable**: If you receive a `ValueError: Node X is not reachable`, verify that your `config.yaml` has the correct `mode` and that you've installed all dependencies listed in `requirements.txt`.
