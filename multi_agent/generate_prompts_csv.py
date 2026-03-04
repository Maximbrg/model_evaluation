import os
import csv

def main():
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "prompts_summary.csv"))
    
    rows = [
        {
            "state name": "trigger_agent_2",
            "agent name": "Agent 4 (Orchestrator)",
            "prompt": "Trigger Phase 1: Build Evaluation Guidelines.",
            "format": "Initialization step / string"
        },
        {
            "state name": "ask_agent_1_for_template",
            "agent name": "Agent 2 (Analyzer)",
            "prompt": (
                "SYSTEM: You are Agent 2: Domain Understanding (Analyzer).\n"
                "You are preparing to draft Evaluation Guidelines and Constraints.\n"
                "Decide if you need to ask Agent 1 for a structural CSV template.\n"
                "Output JSON exactly...\n\n"
                "USER: --- DOMAIN DESCRIPTION ---\n{domain_desc}\n\n"
                "Do you need a structural template from Agent 1 before drafting the guidelines?"
            ),
            "format": 'JSON { "needs_template": true/false, "reasoning": "..." }'
        },
        {
            "state name": "create_evaluation_template",
            "agent name": "Agent 1 (Interpreter)",
            "prompt": (
                "SYSTEM: You are Agent 1: Language Understanding (Interpreter).\n"
                "You hold the metamodel and syntactic rules for a '{model_type}'.\n\n"
                "--- LANGUAGE DEFINITION ---\n{instructions_text}\n\n"
                "Your task: Provide a rigorous CSV formatting template for constraints.\n\n"
                "USER: Please provide the structural CSV template."
            ),
            "format": "CSV String"
        },
        {
            "state name": "draft_guidelines_constraints",
            "agent name": "Agent 2 (Analyzer)",
            "prompt": (
                "SYSTEM: You are Agent 2: Domain Understanding (Analyzer).\n"
                "You are responsible for generating Evaluation Guidelines and Constraints formatted as CSV.\n\n"
                "USER: --- DOMAIN DESCRIPTION ---\n{domain_desc}\n\n"
                "--- TEMPLATE ---\n{template}\n\n"
                "--- SYNTAX ANSWERS FROM AGENT 1 ---\n{syntax_history}\n\n"
                "--- PREVIOUS FEEDBACK ---\n{feedback}\n"
                "Please refine the guidelines based on this feedback and the syntax answers."
            ),
            "format": "CSV String"
        },
        {
            "state name": "refine_guidelines_constraints",
            "agent name": "Agent 2 (Checker)",
            "prompt": (
                "SYSTEM: You are Agent 2 / Refinement Checker.\n"
                "Review the generated guidelines against the case models and syntax rules.\n"
                "Output JSON exactly in ONE of these two formats:\n"
                "Format 1: { \"needs_syntax_answer\": true, \"syntax_question\": \"...\" }\n"
                "Format 2: { \"needs_syntax_answer\": false, \"is_satisfactory\": true/false, \"feedback\": \"...\" }\n\n"
                "USER: --- CASE MODEL ---\n{case_model}\n\n"
                "--- CURRENT GUIDELINES ---\n{guidelines}\n\n"
                "--- PREVIOUS SYNTAX ANSWERS ---\n{syntax_history}\n\n"
                "Evaluate if the guidelines are satisfactory. If you are stuck on syntax, ask Agent 1 instead of giving feedback."
            ),
            "format": 'JSON'
        },
        {
            "state name": "answer_syntax_questions",
            "agent name": "Agent 1 (Interpreter)",
            "prompt": (
                "SYSTEM: You are Agent 1: Language Understanding (Interpreter).\n"
                "You hold the metamodel and syntactic rules for a '{model_type}'.\n\n"
                "--- LANGUAGE DEFINITION ---\n{instructions_text}\n\n"
                "Your task: Answer syntax and structural questions definitively based ONLY on the Language Definition.\n\n"
                "USER: {syntax_question}"
            ),
            "format": "Text String"
        },
        {
            "state name": "receive_guidelines_constraints",
            "agent name": "Agent 4 (Orchestrator)",
            "prompt": "Output final guidelines to file.",
            "format": "File Write (Finalized CSV)"
        }
    ]
    
    with open(output_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["state name", "agent name", "prompt", "format"])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"✅ Generated prompts summary at: {output_path}")

if __name__ == "__main__":
    main()
