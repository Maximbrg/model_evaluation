import os

try:
    from langgraph.graph import StateGraph, START, END
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
except ImportError:
    print("❌ Error: 'langgraph' is not installed or frameworks are missing.")
    exit(1)

def build_labeled_graph():
    """Builds an isolated graph purely for visualization with Agent Names injected straight into the node keys."""
    workflow = StateGraph(AgentState)
    
    # Define cleaner display names for the nodes
    n_trigger = "Trigger Phase 1\n[Agent 4]"
    n_ask_template = "Ask For Template?\n[Agent 2]"
    n_create_template = "Create Evaluation Template\n[Agent 1]"
    n_draft = "Draft Guidelines & Constraints\n[Agent 2]"
    n_refine = "Refine Guidelines & Constraints (Checker)\n[Agent 2]"
    n_answer = "Answer Syntax Questions\n[Agent 1]"
    n_receive = "Receive Guidelines Constraints\n[Agent 4]"
    
    # 1. Add nodes mapping them to the original functions (so it compiles legally)
    workflow.add_node(n_trigger, trigger_agent_2)
    workflow.add_node(n_ask_template, ask_agent_1_for_template)
    workflow.add_node(n_create_template, create_evaluation_template)
    workflow.add_node(n_draft, draft_guidelines_constraints)
    workflow.add_node(n_refine, refine_guidelines_constraints) 
    workflow.add_node(n_answer, answer_syntax_questions)
    workflow.add_node(n_receive, receive_guidelines_constraints)
    
    # 2. Add edges using the visual names
    workflow.add_edge(START, n_trigger)
    workflow.add_edge(n_trigger, n_ask_template)
    
    workflow.add_conditional_edges(
        n_ask_template,
        needs_template_condition,
        {
            "create_evaluation_template": n_create_template,
            "draft_guidelines_constraints": n_draft
        }
    )
    
    workflow.add_edge(n_create_template, n_draft)
    workflow.add_edge(n_draft, n_refine)
    workflow.add_edge(n_answer, n_refine)
    
    # 3. Add conditional edge for the verification path
    workflow.add_conditional_edges(
        n_refine,
        is_guidelines_satisfactory,
        {
            "receive_guidelines": n_receive,
            "draft_guidelines": n_draft,
            "answer_syntax_questions": n_answer
        }
    )
    
    workflow.add_edge(n_receive, END)
    
    return workflow.compile()

def main():
    print("Building LangGraph for visualization...")
    graph = build_labeled_graph()
    
    print("Generating flowchart string...")
    mermaid_str = graph.get_graph().draw_mermaid()
    
    md_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "langgraph_diagram.md"))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# LangGraph Framework Flow\n\n```mermaid\n")
        f.write(mermaid_str)
        f.write("\n```\n")
    print(f"✅ Success! Mermaid markdown saved to: {md_path}")
    
    print("Generating local PNG image...")
    try:
        # Generate the raw bytes locally using LangGraph's native method (no API)
        png_data = graph.get_graph().draw_mermaid_png()
        output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "langgraph_visualization.png"))
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        print(f"✅ Success! Flowchart PNG saved locally to: {output_path}")
    except Exception as e:
        print(f"❌ Error generating image: {e}")

if __name__ == "__main__":
    main()
