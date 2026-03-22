import yaml
import os

PROMPTS_FILE = "prompts_8.yaml"
BASE_DIR = "/Users/maximbragilovski/model_evalution/multi_agent/new_langgraph_framework/"

EXPECTED_KEYS = [
    "task_1_1_develop_template_system",
    "task_1_1_develop_template_user",
    "task_1_2_answer_language_questions_system",
    "task_1_2_answer_language_questions_user",
    "task_2_1_develop_guidelines_system",
    "task_2_1_develop_guidelines_initial_user",
    "task_2_1_develop_guidelines_iterate_user",
    "task_2_2_answer_domain_questions_system",
    "task_2_2_answer_domain_questions_user",
    "task_2_2_iterate_guidelines_revision_system",
    "task_2_2_iterate_guidelines_revision_user",
    "task_3_1_map_existing_system",
    "task_3_1_map_existing_user",
    "task_3_2_discover_potential_system",
    "task_3_2_discover_potential_user",
    "task_3_3_audit_uncovered_system",
    "task_3_3_audit_uncovered_user",
    "task_3_1_send_cases_feedback_system",
    "task_3_1_send_cases_feedback_user",
    "task_4_1_verifier_system",
    "task_4_1_verifier_user",
    "task_3_1_iterate_case_evaluation_system",
    "task_3_1_iterate_case_evaluation_initial_user",
    "task_3_1_iterate_case_evaluation_iterate_user"
]

def validate():
    path = os.path.join(BASE_DIR, PROMPTS_FILE)
    if not os.path.exists(path):
        print(f"File {path} not found.")
        return
    
    with open(path, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except Exception as e:
            print(f"Invalid YAML: {e}")
            return
            
    missing = [k for k in EXPECTED_KEYS if k not in data]
    if missing:
        print(f"Missing keys: {missing}")
    else:
        print("All expected keys are present in " + PROMPTS_FILE)

if __name__ == "__main__":
    validate()
