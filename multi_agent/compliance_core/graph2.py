import os
import csv
import yaml
from datetime import datetime
from langgraph.graph import StateGraph, END
from state import AgentState



import nodes
from nodes import (
    create_language_guidance,
    answer_language_question,
    develop_reference_guidelines,
    extract_language_question,
    save_and_next_case,
    extract_evidence,
    discover_alternatives,
    analyze_additional_elements,
    answer_domain_question,
    _merge_capabilities_into_json,
    identify_deviation_patterns,
    classify_variability
)

def load_file_content(path):
    if not path: return ""
    local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), path))
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    full_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), path))
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def build_graph(entry_point="agent1_language_guidance"):
    """
    Constructs the three-stage compliance pipeline (Graph 2).
    Stages: Evidence Extraction -> Alternative Discovery -> Compliance Labeling
    """
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("agent1_language_guidance", create_language_guidance)
    workflow.add_node("agent1_answer_question", answer_language_question)
    workflow.add_node("agent2_develop_guidelines", develop_reference_guidelines)
    workflow.add_node("extract_guideline_question", extract_language_question)
    workflow.add_node("extract_evidence", extract_evidence)
    workflow.add_node("discover_alternatives", discover_alternatives)
    workflow.add_node("agent2_answer_domain_question", answer_domain_question)
    workflow.add_node("analyze_additional_elements", analyze_additional_elements)
    workflow.add_node("save_and_next_case", save_and_next_case)
    workflow.add_node("identify_deviation_patterns", identify_deviation_patterns)
    workflow.add_node("classify_variability", classify_variability)
    
    # Edges - Phase 1 & 2
    workflow.set_entry_point(entry_point)
    
    def should_stop_after_stage1(state: AgentState) -> str:
        if state.get("stop_after_stage") == 1:
            return "end"
        return "develop_guidelines"

    workflow.add_conditional_edges(
        "agent1_language_guidance",
        should_stop_after_stage1,
        {
            "end": END,
            "develop_guidelines": "agent2_develop_guidelines"
        }
    )
    workflow.add_edge("agent2_develop_guidelines", "extract_guideline_question")
    
    def should_continue_guideline_iteration(state: AgentState) -> str:
        max_guideline_iters = state.get('max_stage2_refinement_iterations', 2)
        if state.get('current_language_question', '').strip() and state.get('guideline_iteration_count', 0) < max_guideline_iters:
            return "ask_agent_1"
        if state.get("stop_after_stage") == 2:
            return "end"
        return "continue"

    workflow.add_conditional_edges(
        "extract_guideline_question",
        should_continue_guideline_iteration,
        {
            "ask_agent_1": "agent1_answer_question",
            "end": END,
            "continue": "extract_evidence"
        }
    )
    def should_route_agent1_answer(state: AgentState) -> str:
        """Routes Agent 1's answer back to the correct stage."""
        stage = state.get('current_stage', 0)
        if stage == 4:
            return "analyze_additional_elements"
        if stage == 3 or state.get('intermediate_evidence'):
            return "discover_alternatives"
        return "agent2_develop_guidelines"

    workflow.add_conditional_edges(
        "agent1_answer_question",
        should_route_agent1_answer,
        {
            "agent2_develop_guidelines": "agent2_develop_guidelines",
            "discover_alternatives": "discover_alternatives",
            "analyze_additional_elements": "analyze_additional_elements"
        }
    )
    
    # Edges - Phase 3 (Three-Stage Compliance Pipeline)
    # The router logic is now embedded or simplified
    workflow.add_edge("extract_evidence", "discover_alternatives")
    
    def should_continue_discovery(state: AgentState) -> str:
        """Determines if we need to ask experts about discovered alternatives."""
        a1_iter = state.get('discovery_agent1_iteration_count', 0)
        a2_iter = state.get('discovery_agent2_iteration_count', 0)
        max_a1 = state.get('max_stage3_discovery_agent1_iterations', 3)
        max_a2 = state.get('max_stage3_discovery_agent2_iterations', 3)

        q1 = state.get('current_language_question', '').strip()
        q2 = state.get('current_domain_question', '').strip()

        if q1 and a1_iter < max_a1:
            return "ask_agent_1"
        if q2 and a2_iter < max_a2:
            return "ask_agent_2"
            
        if q1 and a1_iter >= max_a1:
            print(f"⚠️ Max discovery Agent 1 iterations ({max_a1}) reached. Skipping.")
        if q2 and a2_iter >= max_a2:
            print(f"⚠️ Max discovery Agent 2 iterations ({max_a2}) reached. Skipping.")

        return "analyze_additional_elements"

    workflow.add_conditional_edges(
        "discover_alternatives",
        should_continue_discovery,
        {
            "ask_agent_1": "agent1_answer_question",
            "ask_agent_2": "agent2_answer_domain_question",
            "analyze_additional_elements": "analyze_additional_elements"
        }
    )
    
    # Loop back from answers to discovery or additional analysis
    workflow.add_conditional_edges(
        "agent2_answer_domain_question",
        lambda state: "discover_alternatives" if state.get('current_stage') == 3 else "analyze_additional_elements",
        {
            "discover_alternatives": "discover_alternatives",
            "analyze_additional_elements": "analyze_additional_elements"
        }
    )
    
    def should_continue_additional_analysis(state: AgentState) -> str:
        """Determines if we need to ask experts during Stage 4."""
        a1_iter = state.get('additional_agent1_iteration_count', 0)
        a2_iter = state.get('additional_agent2_iteration_count', 0)
        max_a1 = state.get('max_stage3_additional_agent1_iterations', 3)
        max_a2 = state.get('max_stage3_additional_agent2_iterations', 3)

        q1 = state.get('current_language_question', '').strip()
        q2 = state.get('current_domain_question', '').strip()

        if q1 and a1_iter < max_a1:
            return "ask_agent_1"
        if q2 and a2_iter < max_a2:
            return "ask_agent_2"
            
        if q1 and a1_iter >= max_a1:
            print(f"⚠️ Max analysis Agent 1 iterations ({max_a1}) reached. Skipping.")
        if q2 and a2_iter >= max_a2:
            print(f"⚠️ Max analysis Agent 2 iterations ({max_a2}) reached. Skipping.")

        return "finish"

    workflow.add_conditional_edges(
        "analyze_additional_elements",
        should_continue_additional_analysis,
        {
            "ask_agent_1": "agent1_answer_question",
            "ask_agent_2": "agent2_answer_domain_question",
            "finish": "save_and_next_case"
        }
    )
    
    def should_process_next_case(state: AgentState) -> str:
        cases = state.get('cases', [])
        current_index = state.get('current_case_index', 0)
        return "next_case" if current_index < len(cases) else "identify_deviation_patterns"
        
    workflow.add_conditional_edges(
        "save_and_next_case",
        should_process_next_case,
        {
            "next_case": "extract_evidence",
            "identify_deviation_patterns": "identify_deviation_patterns"
        }
    )
    
    workflow.add_edge("identify_deviation_patterns", "classify_variability")
    workflow.add_edge("classify_variability", END)
    
    return workflow.compile()

def main():
    print("Loading config.yaml...")
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "config.yaml"))
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    api_key = config.get('openai', {}).get('api_key')
    if not api_key or api_key == "your-openai-api-key-here":
        print("❌ Error: API key missing in config.yaml.")
        return
        
    inputs = config.get('inputs', {})
    cases = []
    
    # Load cases logic
    case_path = inputs.get('case_model_path', '')
    if case_path:
        cases.append({"case_id": str(inputs.get('case_id', 'Case001')), "case_model": load_file_content(case_path)})
    if 'cases' in inputs:
        for c in inputs['cases']:
            cases.append({"case_id": str(c.get('case_id', 'Unknown')), "case_model": load_file_content(c.get('case_model_path', ''))})
    cases_dir = inputs.get('cases_dir', '')
    if cases_dir:
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), cases_dir))
        if not os.path.exists(local_dir): local_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), cases_dir))
        if os.path.exists(local_dir) and os.path.isdir(local_dir):
            file_names = sorted([f for f in os.listdir(local_dir) if f.lower().endswith('.txt')])
            for f_name in file_names:
                prefix = f_name.split('_')[0] if '_' in f_name else f_name.replace('.txt', '')
                full_path = os.path.join(local_dir, f_name)
                with open(full_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read().strip()
                    if content: cases.append({"case_id": prefix.strip(), "case_model": content})

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "outputs", timestamp))
    os.makedirs(os.path.join(output_dir, "stage1_agent1_language"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "stage2_agent2_domain"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "stage3_agent3_compliance"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "stage4_agent4_variability"), exist_ok=True)
    nodes.LOG_PATH = os.path.join(output_dir, "transition_logs.txt")
    
    execution_config = config.get('execution', {})
    mode = execution_config.get('mode', 1)
    
    import json
    language_template, reference_guidelines_draft, agent1_capabilities, agent2_capabilities = "", "", "{}", "{}"
    entry_point = "agent1_language_guidance"
    
    if mode == 2:
        entry_point = "agent2_develop_guidelines"
        language_template = load_file_content(execution_config.get('phase2_inputs', {}).get('language_template_path', ''))
        if language_template:
            data = nodes.extract_json_from_text(language_template)
            if isinstance(data, dict):
                agent1_capabilities = json.dumps(data.get("agent_capabilities", data.get("agent1_capabilities", {})))
    elif mode == 3:
        entry_point = "extract_evidence" # Modified entry point for Phase 3 in Graph 2
        p3_inputs = execution_config.get('phase3_inputs', {})
        reference_guidelines_draft = load_file_content(p3_inputs.get('reference_guidelines_path', ''))
        language_template = load_file_content(p3_inputs.get('language_template_path', ''))
        if language_template:
            data = nodes.extract_json_from_text(language_template)
            if isinstance(data, dict):
                agent1_capabilities = json.dumps(data.get("agent_capabilities", data.get("agent1_capabilities", {})))
        if reference_guidelines_draft:
            data = nodes.extract_json_from_text(reference_guidelines_draft)
            if isinstance(data, dict):
                agent2_capabilities = json.dumps(data.get("agent2_capabilities", data.get("domain_capabilities", {})))

    initial_state = AgentState(
        api_key=api_key, model=config.get('openai', {}).get('model', 'gpt-4o'),
        language_name=inputs.get('language_name', ''), language_reference_manual=load_file_content(inputs.get('language_reference_manual_path', '')),
        language_formal_definition=load_file_content(inputs.get('language_formal_definition_path', '')),
        domain_identifier=inputs.get('domain_identifier', ''), domain_description=load_file_content(inputs.get('domain_description_path', '')),
        cases=cases, current_case_index=0, case_iteration_count=0, cases_feedback=[], guideline_change_log=[],
        questions_answers=inputs.get('questions_answers', ''), current_language_question=inputs.get('current_language_question', ''),
        current_domain_question=inputs.get('current_domain_question', ''), lang_questions_answers="", domain_questions_answers="",
        language_template=language_template, current_language_answer="", reference_guidelines_draft=reference_guidelines_draft,
        current_domain_answer="", compliance_vector_draft="", iteration_count=0, guideline_iteration_count=0,
        compliance_domain_iteration_count=0, compliance_lang_iteration_count=0, case_qa_log=[],
        agent1_capabilities=agent1_capabilities, agent2_capabilities=agent2_capabilities,
        suggested_alternatives="", alternative_change_log=[], verifier_feedback="", verification_iteration_count=0,
        intermediate_evidence={}, discovered_alternatives={},
        additional_iteration_count=0,
        current_stage=0,
        max_stage2_refinement_iterations=execution_config.get('max_stage2_refinement_iterations', execution_config.get('max_guideline_iterations', 5)),
        max_stage3_discovery_agent1_iterations=execution_config.get('max_stage3_discovery_agent1_iterations', 3),
        max_stage3_discovery_agent2_iterations=execution_config.get('max_stage3_discovery_agent2_iterations', 3),
        max_stage3_additional_agent1_iterations=execution_config.get('max_stage3_additional_agent1_iterations', 3),
        max_stage3_additional_agent2_iterations=execution_config.get('max_stage3_additional_agent2_iterations', 3),
        discovery_agent1_iteration_count=0,
        discovery_agent2_iteration_count=0,
        additional_agent1_iteration_count=0,
        additional_agent2_iteration_count=0,
        stop_after_stage=execution_config.get('stop_after_stage'),
        external_guidelines=load_file_content(inputs.get('external_guidelines_path', '')),
        output_dir=output_dir
    )
    
    compiled_graph = build_graph(entry_point=entry_point)
    final_state = dict(initial_state)
    for step in compiled_graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in step.items():
            print(f"🔄 Transitioned TO: [{node_name}]")
            if isinstance(node_output, dict): final_state.update(node_output)
    
    # Save final results
    enriched_final = _merge_capabilities_into_json(final_state.get('reference_guidelines_draft', ''), final_state.get('agent1_capabilities', ''), final_state.get('agent2_capabilities', ''))
    with open(os.path.join(output_dir, "final_reference_guidelines.json"), 'w', encoding='utf-8') as f: f.write(enriched_final)
    
    with open(os.path.join(output_dir, "stage3_agent3_compliance", "final_compliance_vector.json"), 'w', encoding='utf-8') as f: json.dump(final_state.get('cases_feedback', []), f, indent=2)
    with open(os.path.join(output_dir, "stage3_agent3_compliance", "guideline_change_tracker.json"), 'w', encoding='utf-8') as f: json.dump(final_state.get('guideline_change_log', []), f, indent=2)
    with open(os.path.join(output_dir, "stage3_agent3_compliance", "alternative_guideline_changes.json"), 'w', encoding='utf-8') as f: json.dump(final_state.get('alternative_change_log', []), f, indent=2)
    
    interaction_log = [{"state": row["state_name"], "next_state": nodes.CSV_LOG_ROWS[i+1]["state_name"] if i+1 < len(nodes.CSV_LOG_ROWS) else "END", "prompt": row["prompt"], "answer": row["answer"]} for i, row in enumerate(nodes.CSV_LOG_ROWS)]
    with open(os.path.join(output_dir, "interaction_log.json"), 'w', encoding='utf-8') as f: json.dump(interaction_log, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
