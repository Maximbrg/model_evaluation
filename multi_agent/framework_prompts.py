def get_agent_1_template_system_prompt(model_type: str, instructions_text: str) -> str:
    return (
        "You are Agent 1: Language Understanding (Interpreter).\n"
        f"You hold the metamodel and syntactic rules for a '{model_type}'.\n\n"
        "--- LANGUAGE DEFINITION ---\n"
        f"{instructions_text if instructions_text else 'Apply standard theoretical rules.'}\n\n"
        "Your task: Provide a rigorous CSV formatting template for constraints."
    )

def get_agent_1_syntax_system_prompt(model_type: str, instructions_text: str) -> str:
    return (
        "You are Agent 1: Language Understanding (Interpreter).\n"
        f"You hold the metamodel and syntactic rules for a '{model_type}'.\n\n"
        "--- LANGUAGE DEFINITION ---\n"
        f"{instructions_text if instructions_text else 'Apply standard theoretical rules.'}\n\n"
        "Your task: Answer syntax and structural questions definitively based ONLY on the Language Definition."
    )

def get_agent_2_ask_template_system_prompt() -> str:
    return (
        "You are Agent 2: Domain Understanding (Analyzer).\n"
        "You are preparing to draft Evaluation Guidelines and Constraints.\n"
        "Decide if you need to ask Agent 1 for a structural CSV template.\n"
        "Output JSON exactly:\n"
        "{\n"
        "  \"needs_template\": true/false,\n"
        "  \"reasoning\": \"your reasoning\"\n"
        "}"
    )

def get_agent_2_ask_template_user_prompt(domain_desc: str) -> str:
    return (
        "--- DOMAIN DESCRIPTION ---\n"
        f"{domain_desc}\n\n"
        "Do you need a structural template from Agent 1 before drafting the guidelines?"
    )

def get_agent_1_template_user_prompt() -> str:
    return "Please provide the structural CSV template."

def get_agent_2_draft_system_prompt() -> str:
    return (
        "You are Agent 2: Domain Understanding (Analyzer).\n"
        "You are responsible for generating Evaluation Guidelines and Constraints formatted as CSV.\n"
    )

def get_agent_2_draft_user_prompt(domain_desc: str, template: str, feedback: str, syntax_history: str = "") -> str:
    prompt = (
        "--- DOMAIN DESCRIPTION ---\n"
        f"{domain_desc}\n\n"
        "--- TEMPLATE ---\n"
        f"{template}\n\n"
    )
    if syntax_history:
        prompt += f"--- SYNTAX ANSWERS FROM AGENT 1 ---\n{syntax_history}\n\n"
        
    if feedback:
        prompt += f"--- PREVIOUS FEEDBACK ---\n{feedback}\nPlease refine the guidelines based on this feedback and the syntax answers.\n"
    else:
        prompt += "Please draft the initial guidelines based on the domain description and template.\n"
    return prompt

def get_checker_system_prompt() -> str:
    return (
        "You are Agent 2 / Refinement Checker.\n"
        "Review the generated guidelines against the case models and syntax rules.\n"
        "Output JSON exactly in ONE of these two formats:\n"
        "Format 1 (If you are unsure about syntax and need to ask Agent 1 FIRST):\n"
        "{\n"
        "  \"needs_syntax_answer\": true,\n"
        "  \"syntax_question\": \"your question for Agent 1\"\n"
        "}\n\n"
        "Format 2 (If you can fully evaluate the guidelines):\n"
        "{\n"
        "  \"needs_syntax_answer\": false,\n"
        "  \"is_satisfactory\": true/false,\n"
        "  \"feedback\": \"your reasoning and feedback for the next draft (if false)\"\n"
        "}"
    )

def get_checker_user_prompt(case_model: str, guidelines: str, syntax_history: str = "") -> str:
    prompt = (
        "--- CASE MODEL ---\n"
        f"{case_model}\n\n"
        "--- CURRENT GUIDELINES ---\n"
        f"{guidelines}\n\n"
    )
    if syntax_history:
        prompt += f"--- PREVIOUS SYNTAX ANSWERS ---\n{syntax_history}\n\n"
        
    prompt += "Evaluate if the guidelines are satisfactory. If you are stuck on syntax, ask Agent 1 instead of giving feedback."
    return prompt
