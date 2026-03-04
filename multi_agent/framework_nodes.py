import os
import json
import csv
from openai import OpenAI
from framework_state import AgentState
import framework_prompts

def log_interaction(output_dir: str, state_name: str, agent_ask: str, agent_response: str, transition: str):
    """Helper to log the state transition directly to a stage_interactions CSV and print it."""
    log_path = os.path.join(output_dir, "stage_interactions.csv")
    file_exists = os.path.exists(log_path)
    with open(log_path, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["state name", "agent ask", "agent response", "from state to state"])
        writer.writerow([state_name, agent_ask, agent_response, transition])
    
    print(f"\n\033[36m--- LOG: {state_name} ---\033[0m")
    print(f"\033[36mAsk:\033[0m {agent_ask[:150]}...")
    print(f"\033[36mResponse:\033[0m {agent_response[:150]}...")
    print(f"\033[36mTransition:\033[0m {transition}")

def trigger_agent_2(state: AgentState):
    print("\n\033[35m[System/Agent 4]: Triggering Phase 1 - Build Evaluation Guidelines/Constraints.\033[0m")
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="trigger_agent_2",
        agent_ask="Trigger Phase 1: Build Evaluation Guidelines.",
        agent_response="Acknowledged.",
        transition="trigger_agent_2 -> ask_agent_1_for_template"
    )
    
    return {"iteration": 0, "guidelines": "", "feedback": ""}

def ask_agent_1_for_template(state: AgentState):
    print("\n\033[33m[Agent 2]: Deciding whether to ask Agent 1 for a template...\033[0m")
    client = OpenAI(api_key=state['api_key'])
    
    system_prompt = framework_prompts.get_agent_2_ask_template_system_prompt()
    user_prompt = framework_prompts.get_agent_2_ask_template_user_prompt(state['domain_desc'])
    
    response = client.chat.completions.create(
        model=state['model_name'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    raw_response = response.choices[0].message.content
    try:
        evaluation = json.loads(raw_response)
        needs_template = evaluation.get("needs_template", True)
    except Exception:
        needs_template = True
        
    print(f"\033[31m[Agent 2]: Needs template? {needs_template}\033[0m")
    
    transition = "ask_agent_1_for_template -> create_evaluation_template" if needs_template else "ask_agent_1_for_template -> draft_guidelines_constraints"
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="ask_agent_1_for_template",
        agent_ask=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}",
        agent_response=raw_response,
        transition=transition
    )
    
    return {"needs_template": needs_template}

def needs_template_condition(state: AgentState):
    if state.get("needs_template", True):
        return "create_evaluation_template"
    return "draft_guidelines_constraints"

def create_evaluation_template(state: AgentState):
    print("\n\033[33m[Agent 1]: Creating evaluation template...\033[0m")
    client = OpenAI(api_key=state['api_key'])
    
    system_prompt = framework_prompts.get_agent_1_template_system_prompt(state['model_type'], state['instructions_text'])
    user_prompt = framework_prompts.get_agent_1_template_user_prompt()
    
    response = client.chat.completions.create(
        model=state['model_name'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    template = response.choices[0].message.content
    print(f"\033[32m[Agent 1]: Returned template.\033[0m")
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="create_evaluation_template",
        agent_ask=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}",
        agent_response=template,
        transition="create_evaluation_template -> draft_guidelines_constraints"
    )
    
    return {"template": template}

def draft_guidelines_constraints(state: AgentState):
    iteration = state.get('iteration', 0)
    print(f"\n\033[34m[Agent 2]: Drafting guidelines (Iteration {iteration})...\033[0m")
    client = OpenAI(api_key=state['api_key'])
    
    system_prompt = framework_prompts.get_agent_2_draft_system_prompt()
    user_prompt = framework_prompts.get_agent_2_draft_user_prompt(state['domain_desc'], state['template'], state.get('feedback', ''), state.get('syntax_history', ''))
    
    response = client.chat.completions.create(
        model=state['model_name'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    guidelines = response.choices[0].message.content
    print("\033[32m[Agent 2]: Guidelines drafted/refined.\033[0m")
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="draft_guidelines_constraints",
        agent_ask=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}",
        agent_response=guidelines,
        transition="draft_guidelines_constraints -> refine_guidelines_constraints"
    )
    
    return {"guidelines": guidelines, "iteration": iteration + 1}

def refine_guidelines_constraints(state: AgentState):
    print("\n\033[33m[Agent 2]: Checking if guidelines are satisfactory against case model...\033[0m")
    client = OpenAI(api_key=state['api_key'])
    
    system_prompt = framework_prompts.get_checker_system_prompt()
    user_prompt = framework_prompts.get_checker_user_prompt(state['case_model'], state['guidelines'], state.get('syntax_history', ''))
    
    response = client.chat.completions.create(
        model=state['model_name'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    raw_response = response.choices[0].message.content
    try:
        evaluation = json.loads(raw_response)
        needs_syntax_answer = evaluation.get("needs_syntax_answer", False)
        if needs_syntax_answer:
            is_satisfactory = False
            feedback = state.get('feedback', '') # Retain previous feedback
            syntax_question = evaluation.get("syntax_question", "")
        else:
            is_satisfactory = evaluation.get("is_satisfactory", True)
            feedback = evaluation.get("feedback", "")
            syntax_question = ""
    except Exception:
        is_satisfactory = True
        feedback = ""
        needs_syntax_answer = False
        syntax_question = ""
        
    print(f"\033[31m[Checker]: Satisfactory? {is_satisfactory}. Needs Syntax Help? {needs_syntax_answer}. Feedback: {feedback[:50]}...\033[0m")
    
    iteration = state.get("iteration", 0)
    if needs_syntax_answer:
        transition = "refine_guidelines_constraints -> answer_syntax_questions"
    elif is_satisfactory or iteration >= 3:
        transition = "refine_guidelines_constraints -> receive_guidelines_constraints"
    else:
        transition = "refine_guidelines_constraints -> draft_guidelines_constraints"
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="refine_guidelines_constraints",
        agent_ask=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}",
        agent_response=raw_response,
        transition=transition
    )
    
    return {"is_satisfactory": is_satisfactory, "feedback": feedback, "needs_syntax_answer": needs_syntax_answer, "syntax_question": syntax_question}

def answer_syntax_questions(state: AgentState):
    print("\n\033[33m[Agent 1]: Answering syntax question...\033[0m")
    client = OpenAI(api_key=state['api_key'])
    
    system_prompt = framework_prompts.get_agent_1_syntax_system_prompt(state['model_type'], state['instructions_text'])
    user_prompt = state.get('syntax_question', 'No question provided.')
    
    response = client.chat.completions.create(
        model=state['model_name'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    answer = response.choices[0].message.content
    print(f"\033[32m[Agent 1]: Answered syntax question.\033[0m")
    
    log_interaction(
        output_dir=state['output_dir'],
        state_name="answer_syntax_questions",
        agent_ask=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}",
        agent_response=answer,
        transition="answer_syntax_questions -> refine_guidelines_constraints"
    )
    
    # Accumulate syntax history
    current_history = state.get('syntax_history', '')
    new_entry = f"Q: {user_prompt}\nA: {answer}\n"
    new_history = current_history + "\n" + new_entry if current_history else new_entry
    
    return {"syntax_history": new_history, "needs_syntax_answer": False}

def is_guidelines_satisfactory(state: AgentState):
    # LangGraph conditional edge
    if state.get("needs_syntax_answer", False):
        return "ask_agent_1"
    if state.get("is_satisfactory") or state.get("iteration", 0) >= 3:
        return "receive_guidelines"
    return "draft_guidelines"

def receive_guidelines_constraints(state: AgentState):
    print("\n\033[35m[Agent 4 (Orchestrator)]: Received Final Guidelines.\033[0m")
    
    output_dir = state['output_dir']
    with open(os.path.join(output_dir, "final_guidelines.csv"), "w", encoding='utf-8') as f:
        f.write(state['guidelines'])
        
    log_interaction(
        output_dir=state['output_dir'],
        state_name="receive_guidelines_constraints",
        agent_ask="Output final guidelines to file.",
        agent_response="Saved to final_guidelines.csv",
        transition="receive_guidelines_constraints -> END"
    )
        
    return {"guidelines": state['guidelines']}
