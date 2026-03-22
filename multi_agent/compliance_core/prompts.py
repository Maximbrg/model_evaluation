import os
import yaml

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config.yaml"))
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        prompts_filename = config.get('execution', {}).get('prompts_file', 'prompts.yaml')
except Exception:
    prompts_filename = 'prompts.yaml'

# Environment variable override
prompts_filename = os.getenv('PROMPTS_FILE', prompts_filename)

PROMPTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), prompts_filename))
print(f"Loading prompts from: {prompts_filename}")
with open(PROMPTS_PATH, 'r', encoding='utf-8') as f:
    PROMPTS = yaml.safe_load(f)

def safe_format(template: str, **kwargs) -> str:
    """Replaces {key} with value in the template without throwing errors on other { } brackets."""
    result = template
    for key, value in kwargs.items():
        v_str = str(value)
        # Remove potential control characters that could break JSON
        sanitized = "".join(ch for ch in v_str if ch.isprintable() or ch in "\n\r\t")
        result = result.replace(f"{{{key}}}", sanitized)
    return result

def get_prompt(key: str, default_key: str = "") -> str:
    """Returns the prompt for the given key, or a default key if the primary is missing."""
    if key in PROMPTS:
        return PROMPTS[key]
    if default_key and default_key in PROMPTS:
        return PROMPTS[default_key]
    if key.endswith("user") or default_key.endswith("user"):
        return "Please proceed with the task according to the system instructions."
    raise KeyError(f"Prompt key '{key}' (or default '{default_key}') not found in {prompts_filename}")

# Agent 1 Tasks
def get_agent_1_language_guidance_system_prompt(language_name: str, language_reference_manual: str, language_formal_definition: str) -> str:
    template = get_prompt("task_1_1_develop_template_system", "task_1_1_language_guidance_system")
    return safe_format(template,
        language_name=language_name,
        language_reference_manual=language_reference_manual if language_reference_manual else "Not provided",
        language_formal_definition=language_formal_definition if language_formal_definition else "Not provided"
    )

def get_agent_1_language_guidance_user_prompt() -> str:
    return get_prompt("task_1_1_develop_template_user", "task_1_1_language_guidance_user")

def get_agent_1_answer_question_system_prompt(language_name: str, language_template: str, language_reference_manual: str, language_formal_definition: str, questions: str) -> str:
    template = get_prompt("task_1_2_answer_language_questions_system", "task_1_2_answer_question_system")
    return safe_format(template,
        language_name=language_name,
        language_template=language_template,
        language_guidelines=language_template,
        language_reference_manual=language_reference_manual if language_reference_manual else "Not provided",
        language_formal_definition=language_formal_definition if language_formal_definition else "Not provided",
        questions=questions
    )

def get_agent_1_answer_question_user_prompt() -> str:
    return get_prompt("task_1_2_answer_language_questions_user", "task_1_2_answer_question_user")

# Agent 2 Tasks
def get_agent_2_develop_guidelines_system_prompt(language_template: str, domain_description: str, questions_answers: str, reference_guidelines_draft: str, language_name: str, domain_identifier: str, external_guidelines: str = "None") -> str:
    template = get_prompt("task_2_1_develop_guidelines_system")
    return safe_format(template,
        language_template=language_template,
        domain_description=domain_description,
        questions_answers=questions_answers if questions_answers else "None",
        reference_guidelines_draft=reference_guidelines_draft if reference_guidelines_draft else "None",
        language_name=language_name,
        domain_identifier=domain_identifier,
        external_guidelines=external_guidelines,
        agent1_capabilities="{agent1_capabilities}"
    )

def get_agent_2_develop_guidelines_initial_user_prompt() -> str:
    return get_prompt("task_2_1_develop_guidelines_initial_user")

def get_agent_2_develop_guidelines_iterate_user_prompt() -> str:
    return get_prompt("task_2_1_develop_guidelines_iterate_user")

def get_agent_2_answer_domain_questions_system_prompt(domain_description: str, reference_guidelines: str, question_text: str) -> str:
    template = get_prompt("task_2_2_answer_domain_questions_system")
    return safe_format(template,
        domain_description=domain_description,
        reference_guidelines=reference_guidelines,
        question_text=question_text,
        domain_identifier="{domain_identifier}"
    )

def get_agent_2_answer_domain_questions_user_prompt() -> str:
    return get_prompt("task_2_2_answer_domain_questions_user")

def get_agent_2_iterate_guidelines_revision_system_prompt(current_guidelines: str, domain_qa_with_flags: str, language_guidelines: str, language_answers: str, iteration: int) -> str:
    template = get_prompt("task_2_2_iterate_guidelines_revision_system")
    return safe_format(template,
        current_guidelines=current_guidelines,
        domain_qa_with_flags=domain_qa_with_flags,
        language_guidelines=language_guidelines,
        language_answers=language_answers if language_answers else "None",
        iteration=iteration
    )

def get_agent_2_iterate_guidelines_revision_user_prompt() -> str:
    return get_prompt("task_2_2_iterate_guidelines_revision_user")

# Agent 3 Tasks (Three-Stage Pipeline)
def get_agent_3_extract_evidence_system_prompt(case_model: str, reference_guidelines: str) -> str:
    template = get_prompt("task_3_1_map_existing_system", "task_3_1_extract_evidence_system")
    return safe_format(template,
        case_model=case_model,
        reference_guidelines=reference_guidelines
    )

def get_agent_3_discover_alternatives_system_prompt(case_model: str, reference_guidelines: str, intermediate_evidence: str, agent1_capabilities: str = "", agent2_capabilities: str = "", lang_questions_answers: str = "", domain_questions_answers: str = "", iteration: int = 1) -> str:
    template = get_prompt("task_3_2_discover_potential_system", "task_3_1_discover_alternatives_system")
    return safe_format(template,
        case_model=case_model,
        reference_guidelines=reference_guidelines,
        intermediate_evidence=intermediate_evidence,
        agent1_capabilities=agent1_capabilities if agent1_capabilities else "None",
        agent2_capabilities=agent2_capabilities if agent2_capabilities else "None",
        lang_questions_answers=lang_questions_answers if lang_questions_answers else "None",
        domain_questions_answers=domain_questions_answers if domain_questions_answers else "None",
        iteration=iteration
    )

def get_agent_3_label_compliance_system_prompt(case_id: str, reference_guidelines: str, intermediate_evidence: str, discovered_alternatives: str, lang_questions_answers: str = "", domain_questions_answers: str = "") -> str:
    template = get_prompt("task_3_1_label_compliance_system")
    return safe_format(template,
        case_id=case_id,
        reference_guidelines=reference_guidelines,
        intermediate_evidence=intermediate_evidence,
        discovered_alternatives=discovered_alternatives,
        lang_questions_answers=lang_questions_answers if lang_questions_answers else "None",
        domain_questions_answers=domain_questions_answers if domain_questions_answers else "None"
    )

def get_agent_3_analyze_alien_elements_system_prompt(case_id: str, case_model: str, reference_guidelines: str, domain_description: str, language_guidelines: str, compliance_vector: str, agent1_capabilities: str = "", agent2_capabilities: str = "") -> str:
    template = get_prompt("task_3_3_audit_uncovered_system", "task_3_4_audit_uncovered_system")
    return safe_format(template,
        case_id=case_id,
        case_model=case_model,
        reference_guidelines=reference_guidelines,
        domain_description=domain_description,
        language_guidelines=language_guidelines,
        compliance_vector=compliance_vector,
        agent1_capabilities=agent1_capabilities if agent1_capabilities else "None",
        agent2_capabilities=agent2_capabilities if agent2_capabilities else "None"
    )

def get_agent_3_analyze_alien_elements_user_prompt() -> str:
    return get_prompt("task_3_2_analyze_alien_elements_user")

def get_agent_3_send_cases_feedback_system_prompt(final_evaluation: str, case_model: str, guidelines_version: str) -> str:
    template = get_prompt("task_3_1_send_cases_feedback_system")
    return safe_format(template,
        final_evaluation=final_evaluation,
        case_model=case_model,
        guidelines_version=guidelines_version
    )

def get_agent_3_send_cases_feedback_user_prompt() -> str:
    return get_prompt("task_3_1_send_cases_feedback_user")

def get_agent_4_verify_compliance_system_prompt(case_model: str, case_id: str, reference_guidelines: str, compliance_vector: str) -> str:
    template = get_prompt("task_4_1_verifier_system")
    return safe_format(template,
        case_model=case_model,
        case_id=case_id,
        reference_guidelines=reference_guidelines,
        compliance_vector=compliance_vector
    )

def get_agent_4_verify_compliance_user_prompt() -> str:
    return get_prompt("task_4_1_verifier_user")

# Backward Compatibility Placeholders for Iterative Stage 3
def get_agent_3_iterate_case_evaluation_system_prompt(case_model: str, case_id: str, reference_guidelines: str, lang_questions_answers: str = "", domain_questions_answers: str = "", agent1_capabilities: str = "", agent2_capabilities: str = "", verifier_feedback: str = "") -> str:
    template = get_prompt("task_3_1_iterate_case_evaluation_system")
    return safe_format(template,
        case_model=case_model,
        case_id=case_id,
        reference_guidelines=reference_guidelines,
        lang_questions_answers=lang_questions_answers if lang_questions_answers else "None",
        domain_questions_answers=domain_questions_answers if domain_questions_answers else "None",
        agent1_capabilities=agent1_capabilities if agent1_capabilities else "None",
        agent2_capabilities=agent2_capabilities if agent2_capabilities else "None",
        verifier_feedback=verifier_feedback if verifier_feedback else "None"
    )

def get_agent_3_iterate_case_evaluation_initial_user_prompt() -> str:
    return get_prompt("task_3_1_iterate_case_evaluation_initial_user")

def get_agent_3_iterate_case_evaluation_iterate_user_prompt() -> str:
    return get_prompt("task_3_1_iterate_case_evaluation_iterate_user")

# Agent 4 Tasks
def get_agent_4_identify_deviation_patterns_system_prompt(compliance_vectors: str, uncovered_fragment_classifications: str, reference_guidelines: str) -> str:
    template = get_prompt("task_4_1_identify_deviation_patterns_system")
    return safe_format(template,
        domain_identifier="{domain_identifier}",
        compliance_vectors=compliance_vectors,
        uncovered_fragment_classifications=uncovered_fragment_classifications,
        reference_guidelines=reference_guidelines
    )

def get_agent_4_classify_variability_system_prompt(deviation_patterns: str, reference_guidelines: str, domain_description: str, lang_questions_answers: str = "", domain_questions_answers: str = "") -> str:
    template = get_prompt("task_4_2_classify_variability_system")
    return safe_format(template,
        domain_identifier="{domain_identifier}",
        deviation_patterns=deviation_patterns,
        reference_guidelines=reference_guidelines,
        domain_description=domain_description,
        lang_questions_answers=lang_questions_answers if lang_questions_answers else "None",
        domain_questions_answers=domain_questions_answers if domain_questions_answers else "None"
    )
