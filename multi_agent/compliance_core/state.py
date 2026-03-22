from typing import TypedDict

class AgentState(TypedDict, total=False):
    # API Config
    api_key: str
    model: str
    
    # Inputs for Agent 1 (Task 1.1)
    language_name: str
    language_reference_manual: str
    language_formal_definition: str
    
    # Outputs from Agent 1 (Task 1.1)
    language_template: str
    agent1_capabilities: str  # JSON string of agent_capabilities block from A1-T1 output
    
    # Inputs for Agent 1 (Task 1.2)
    current_language_question: str
    
    # Outputs from Agent 1 (Task 1.2)
    current_language_answer: str
    
    # Inputs for Agent 2 (Tasks 2.1 & 2.2)
    domain_identifier: str
    domain_description: str
    external_guidelines: str
    questions_answers: str
    iteration_count: int
    guideline_iteration_count: int
    compliance_domain_iteration_count: int
    compliance_lang_iteration_count: int
    
    # Execution Limits
    max_stage3_discovery_agent1_iterations: int
    max_stage3_discovery_agent2_iterations: int
    max_stage3_additional_agent1_iterations: int
    max_stage3_additional_agent2_iterations: int
    discovery_agent1_iteration_count: int
    discovery_agent2_iteration_count: int
    additional_agent1_iteration_count: int
    additional_agent2_iteration_count: int
    current_stage: int # 3 for Discovery, 4 for Additional
    stop_after_stage: int # If set, stop after this stage (1 or 2)
    
    # Inputs for Agent 2 (Task 2.3)

    current_domain_question: str
    
    # Outputs from Agent 2
    reference_guidelines_draft: str
    agent2_capabilities: str  # JSON string of domain_capabilities block from A2-T3 output
    current_domain_answer: str

    # Inputs for Agent 3 (Task 3.1)
    cases: list[dict] # Format: [{"case_id": "C1", "case_model": "..."}]
    current_case_index: int
    case_iteration_count: int
    
    # Outputs from Agent 3 (Task 3.1)
    compliance_vector_draft: str
    cases_feedback: list # Accumulated feedback for all cases as JSON objects
    domain_questions_answers: str
    lang_questions_answers: str
    guideline_change_log: list # Accumulated changelog of guideline modifications during Stage 3
    case_qa_log: list  # Per-case Q&A pairs; reset after each case is saved
    suggested_alternatives: str # Suggested modeling alternatives from Agent 3 to Agent 2
    alternative_change_log: list # Log of changes specifically to alternative_description field
    verifier_feedback: str # Feedback from Agent 4 to Agent 3
    verification_iteration_count: int # Count of verification loops
    intermediate_evidence: dict # Extracted fragments per guideline (Stage 1)
    discovered_alternatives: dict # New modeling patterns found for non-matched guidelines (Stage 2)
    additional_elements_evaluation: list # Evaluation of elements not covered by guidelines (Stage 4)
    
    # Stage 4 outputs
    deviation_patterns: str
    variability_classifications: str

    # Global variables for saving
    output_dir: str
