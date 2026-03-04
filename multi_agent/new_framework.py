import os
import datetime
import yaml

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    print("❌ Error: 'langgraph' is not installed. Please pip install langgraph.")
    exit(1)

from framework_state import AgentState
from framework_nodes import (
    trigger_agent_2,
    ask_agent_1_for_template,
    needs_template_condition,
    create_evaluation_template,
    draft_guidelines_constraints,
    refine_guidelines_constraints,
    answer_syntax_questions,
    is_guidelines_satisfactory,
    receive_guidelines_constraints
)

def load_file_content(filepath: str) -> str:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', filepath))
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add nodes
    workflow.add_node("trigger_agent_2", trigger_agent_2)
    workflow.add_node("ask_agent_1_for_template", ask_agent_1_for_template)
    workflow.add_node("create_evaluation_template", create_evaluation_template)
    workflow.add_node("draft_guidelines_constraints", draft_guidelines_constraints)
    workflow.add_node("refine_guidelines_constraints", refine_guidelines_constraints) # Also acts as the check
    workflow.add_node("answer_syntax_questions", answer_syntax_questions)
    workflow.add_node("receive_guidelines_constraints", receive_guidelines_constraints)
    
    # 2. Add edges
    workflow.add_edge(START, "trigger_agent_2")
    workflow.add_edge("trigger_agent_2", "ask_agent_1_for_template")
    
    workflow.add_conditional_edges(
        "ask_agent_1_for_template",
        needs_template_condition,
        {
            "create_evaluation_template": "create_evaluation_template",
            "draft_guidelines_constraints": "draft_guidelines_constraints"
        }
    )
    
    workflow.add_edge("create_evaluation_template", "draft_guidelines_constraints")
    workflow.add_edge("draft_guidelines_constraints", "refine_guidelines_constraints")
    workflow.add_edge("answer_syntax_questions", "refine_guidelines_constraints")
    
    # 3. Add conditional edge for the verification path
    workflow.add_conditional_edges(
        "refine_guidelines_constraints",
        is_guidelines_satisfactory,
        {
            "receive_guidelines": "receive_guidelines_constraints",
            "draft_guidelines": "draft_guidelines_constraints",
            "answer_syntax_questions": "answer_syntax_questions"
        }
    )
    
    workflow.add_edge("receive_guidelines_constraints", END)
    
    return workflow.compile()

def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    api_key = config.get('openai', {}).get('api_key')
    if not api_key or api_key == "your-openai-api-key-here":
        print("❌ Error: API key missing in config.yaml.")
        return

    model = config.get('openai', {}).get('model', 'o4-mini')
    paths = config.get('paths', {})
    eval_config = config.get('evaluation', {})
    model_type = eval_config.get('model_type', 'class diagram')
    domain_name = eval_config.get('domain_name', 'unknown')

    instructions_text = load_file_content(paths.get('instructions', 'artifacts/metamodel.txt'))
    problem_desc = load_file_content(paths.get('problem_description', 'artifacts/problem_description.txt'))
    student_diagram = load_file_content(paths.get('student_diagram', 'artifacts/student_diagram.txt'))

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", f"langgraph_framework_{domain_name}_{timestamp}"))
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Initializing LangGraph Framework with model: {model}")
    print(f"Outputs will be saved to: {output_dir}")
    print(f"Detailed stage interactions will be logged to: stage_interactions.csv")
    
    # Initial state injection
    initial_state = {
        "api_key": api_key,
        "model_name": model,
        "output_dir": output_dir,
        "model_type": model_type,
        "instructions_text": instructions_text,
        "domain_desc": problem_desc,
        "case_model": student_diagram,
        "iteration": 0
    }
    
    graph = build_graph()
    
    # Render ASCII graph structure just to show
    print("\n--- LangGraph Pipeline ---")
    print("START -> trigger_agent_2 -> ask_agent_1_for_template")
    print("ask_agent_1_for_template -> (if needs_template) -> create_evaluation_template -> draft_guidelines_constraints")
    print("ask_agent_1_for_template -> (if NO template needed) -> draft_guidelines_constraints")
    print("draft_guidelines_constraints -> refine_guidelines_constraints")
    print("refine_guidelines_constraints -> (if is_satisfactory) -> receive_guidelines_constraints -> END")
    print("refine_guidelines_constraints -> (if not is_satisfactory) -> draft_guidelines_constraints (LOOP)")
    print("refine_guidelines_constraints -> (if needs syntax help) -> answer_syntax_questions -> refine_guidelines_constraints (INNER LOOP)")
    print("--------------------------\n")

    # Run LangGraph pipeline
    final_state = graph.invoke(initial_state)
    print("\n\033[36m[System]: LangGraph Pipeline Finished successfully!\033[0m")
    print(f"Total Iterations: {final_state['iteration']}")

if __name__ == "__main__":
    main()
