import os
import re
import json
from datetime import datetime
from openai import OpenAI
from state import AgentState
from prompts import (
    get_agent_1_language_guidance_system_prompt, 
    get_agent_1_language_guidance_user_prompt,
    get_agent_1_answer_question_system_prompt,
    get_agent_1_answer_question_user_prompt,
    get_agent_2_develop_guidelines_system_prompt,
    get_agent_2_develop_guidelines_initial_user_prompt,
    get_agent_2_develop_guidelines_iterate_user_prompt,
    get_agent_2_answer_domain_questions_system_prompt,
    get_agent_2_answer_domain_questions_user_prompt,
    get_agent_2_iterate_guidelines_revision_system_prompt,
    get_agent_2_iterate_guidelines_revision_user_prompt,
    get_agent_3_extract_evidence_system_prompt,
    get_agent_3_discover_alternatives_system_prompt,
    get_agent_3_label_compliance_system_prompt,
    get_agent_3_iterate_case_evaluation_system_prompt,
    get_agent_3_iterate_case_evaluation_initial_user_prompt,
    get_agent_3_iterate_case_evaluation_iterate_user_prompt
)

# Default log path — overridden by graph.py to point to the run's output directory
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "transition_logs.txt"))

# In-memory CSV buffer: list of dicts with keys state_name, prompt, answer
# graph.py reads this at the end to write the CSV (adding NEXT STATE by looking ahead)
CSV_LOG_ROWS: list[dict] = []

def log_interaction(node_name: str, system_prompt: str, user_prompt: str, output: str):
    """
    Appends the interaction details to the text log AND buffers a row for the CSV log.
    """
    # --- text log ---
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"🟢 NODE: {node_name}\n")
        f.write(f"{'-'*60}\n")
        f.write(f"[USER PROMPT]\n{user_prompt}\n")
        f.write(f"{'-'*60}\n")
        f.write(f"[OUTPUT]\n{output}\n")
        f.write(f"{'='*60}\n")

    # --- CSV buffer ---
    full_prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
    CSV_LOG_ROWS.append({
        "state_name": node_name,
        "prompt": full_prompt,
        "answer": output
    })

import json

def extract_json_from_text(text: str) -> dict:
    """
    Robustly extract and parse a JSON object from raw LLM output.

    Strategies tried in order:
    1. Direct parse of the raw text (already valid JSON).
    2. Extract the first ```json ... ``` or ``` ... ``` fenced block, then parse.
    3. Find the outermost { ... } span and parse with strict=False (tolerates
       unescaped newlines / control chars that PlantUML snippets introduce).
    4. Pro-active "cleaning" (regex-based fixing) before re-trying JSON parse.
    5. ast.literal_eval after replacing JSON booleans/null with Python equivalents.
    If all strategies fail, log a warning and return {}.
    """
    import ast
    import re

    if not text or not text.strip():
        print("⚠️ LLM output is empty.")
        return {}

    # ---------- helper: aggressive cleaning of common LLM JSON artefacts ----------
    def _clean(s: str) -> str:
        # 1. Remove // or /* */ comments (not standard JSON but LLMs love them)
        s = re.sub(r'//.*?\n', '\n', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        
        # 2. Normalise curly / smart quotes to straight ASCII quotes
        # (Handling some common unicode quotes)
        s = s.replace('\u201c', '"').replace('\u201d', '"')
        s = s.replace('\u2018', "'").replace('\u2019', "'")
        
        # 3. Strip trailing commas before ] or }
        s = re.sub(r',\s*([\]}])', r'\1', s)
        
        # 4. Try to fix missing commas between objects/arrays: } { -> }, {
        # This handles lists of objects where the LLM skipped a comma
        s = re.sub(r'\}\s*\{', '}, {', s)
        s = re.sub(r'\]\s*\[', '], [', s)
        s = re.sub(r'\}\s*\[', '}, [', s)
        s = re.sub(r'\]\s*\{', '], {', s)
        
        # 5. Handle missing commas between key-value pairs where next key starts: "val" "key":
        # Strategy: find " followed by space/newlines followed by "name":
        s = re.sub(r'("\s*)\s*("\w+":)', r'\1, \2', s)
        
        return s.strip()

    # ---------- Strategy 1: direct parse ----------
    try:
        return json.loads(text.strip(), strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # ---------- Strategy 2: fenced code block ----------
    fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if fence_match:
        candidate = _clean(fence_match.group(1))
        try:
            return json.loads(candidate, strict=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # ---------- Strategy 3: outermost { ... } ----------
    brace_start = text.find('{')
    brace_end   = text.rfind('}')
    if brace_start == -1 or brace_end <= brace_start:
        print("⚠️ No JSON object found in LLM output.")
        return {}

    candidate = _clean(text[brace_start:brace_end + 1])

    try:
        return json.loads(candidate, strict=False)
    except (json.JSONDecodeError, ValueError) as e:
        last_err = e

    # ---------- Strategy 4: ast.literal_eval ----------
    try:
        py_str = candidate.replace('true', 'True').replace('false', 'False').replace('null', 'None')
        result = ast.literal_eval(py_str)
        if isinstance(result, dict):
            return result
    except Exception as ast_e:
        print(f"⚠️ Failed to parse JSON from LLM output. Error: {last_err}")
        print(f"⚠️ AST fallback also failed. Error: {ast_e}")

    return {}

    return {}

def verify_json(data: dict, required_keys: list, node_name: str) -> dict:
    """
    Verifies that the extracted JSON dictionary contains the expected top-level keys.
    If keys are missing, it warns and ensures they exist with default values to prevent downstream crashes.
    """
    if not isinstance(data, dict):
        print(f"⚠️ {node_name}: Data is not a dictionary. Got {type(data)}.")
        return {key: [] for key in required_keys}
    
    missing = [key for key in required_keys if key not in data]
    if missing:
        print(f"⚠️ {node_name}: Missing expected JSON keys: {missing}")
        for key in missing:
            # Default to empty list/string based on typical usage
            if "question" in key or "comment" in key or "vector" in key:
                data[key] = ""
            else:
                data[key] = []
    
    return data

def _merge_capabilities_into_json(raw_json_str: str, agent1_capabilities: str, agent2_capabilities: str) -> str:
    """
    Parses raw_json_str, injects agent1_capabilities and agent2_capabilities blocks,
    and returns the enriched JSON string. Falls back to the original string on failure.
    """
    try:
        data = extract_json_from_text(raw_json_str)
        if not data:
            return raw_json_str
        if agent1_capabilities:
            try:
                data["agent1_capabilities"] = json.loads(agent1_capabilities)
            except Exception:
                data["agent1_capabilities"] = agent1_capabilities
        if agent2_capabilities:
            try:
                data["agent2_capabilities"] = json.loads(agent2_capabilities)
            except Exception:
                data["agent2_capabilities"] = agent2_capabilities
        return json.dumps(data, indent=2)
    except Exception as e:
        print(f"⚠️ _merge_capabilities_into_json failed: {e}")
        return raw_json_str

def create_language_guidance(state: AgentState) -> dict:
    """
    Node function representing Agent 1 (Language Advisor) executing A1-T1.
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: create_language_guidance (Agent 1)")
    
    system_prompt = get_agent_1_language_guidance_system_prompt(
        language_name=state.get('language_name', ''),
        language_reference_manual=state.get('language_reference_manual', ''),
        language_formal_definition=state.get('language_formal_definition', '')
    )
    user_prompt = get_agent_1_language_guidance_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print("✅ Language Guidance successfully generated.")
    
    log_interaction("agent1_language_guidance", system_prompt, user_prompt, output_content)
    
    # Save the language template directly in stage 1
    output_dir = state.get("output_dir", "")
    if output_dir:
        file_path = os.path.join(output_dir, "stage1_agent1_language", "language_template.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"\n[Node]: create_language_guidance - Saved to {file_path}")

    # Extract agent1_capabilities from the JSON output
    parsed = extract_json_from_text(output_content)
    agent1_caps = json.dumps(parsed.get("agent1_capabilities", []), indent=2) if parsed else ""

    return {
        "language_template": output_content,
        "agent1_capabilities": agent1_caps
    }

def answer_language_question(state: AgentState) -> dict:
    """
    Node function representing Agent 1 (Language Advisor) executing A1-T2.
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: answer_language_question (Agent 1)")
    
    system_prompt = get_agent_1_answer_question_system_prompt(
        language_name=state.get('language_name', ''),
        language_template=state.get('language_template', ''),
        language_reference_manual=state.get('language_reference_manual', ''),
        language_formal_definition=state.get('language_formal_definition', ''),
        questions=state.get('current_language_question', '[]')
    )
    user_prompt = get_agent_1_answer_question_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print("✅ Language question answered.")
    
    log_interaction("agent1_answer_question", system_prompt, user_prompt, output_content)
    
    # Append the Q&A to the running context
    qa_pair = f"Questions:\n{state.get('current_language_question', '')}\nAnswers:\n{output_content}\n---\n"
    updated_qa = state.get('questions_answers', '') + qa_pair
    
    lang_iter = state.get('compliance_lang_iteration_count', 0)
    qa_log = state.get('case_qa_log', [])
    qa_log = qa_log + [{
        "type": "language",
        "iteration": lang_iter + 1,
        "question": state.get('current_language_question', ''),
        "answer": output_content
    }]
    
    updates = {
        "current_language_answer": output_content,
        "questions_answers": updated_qa,
        "compliance_lang_iteration_count": lang_iter + 1,
        "case_qa_log": qa_log
    }
    
    stage = state.get('current_stage', 0)
    if stage == 3:
        updates["discovery_agent1_iteration_count"] = state.get("discovery_agent1_iteration_count", 0) + 1
    elif stage == 4:
        updates["additional_agent1_iteration_count"] = state.get("additional_agent1_iteration_count", 0) + 1
        
    return updates

def develop_reference_guidelines(state: AgentState) -> dict:
    """
    Node function representing Agent 2 (Reference Builder) executing A2-T1.
    Handles both initial creation and subsequent iterations within the loop.
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: develop_reference_guidelines (Agent 2)")
    
    guideline_iter = state.get('guideline_iteration_count', 0)
    system_prompt = get_agent_2_develop_guidelines_system_prompt(
        language_template=state.get('language_template', ''),
        domain_description=state.get('domain_description', ''),
        questions_answers=state.get('questions_answers', ''),
        reference_guidelines_draft=state.get('reference_guidelines_draft', ''),
        language_name=state.get('language_name', ''),
        domain_identifier=state.get('domain_identifier', ''),
        external_guidelines=state.get('external_guidelines', 'None')
    )
    
    # Use different user prompt based on iteration count
    if guideline_iter == 0:
        user_prompt = get_agent_2_develop_guidelines_initial_user_prompt()
    else:
        user_prompt = get_agent_2_develop_guidelines_iterate_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print("✅ Reference Guidelines updated.")
    
    # Save a snapshot of the guidelines after each iteration in Stage 2
    output_dir = state.get("output_dir", "")
    if output_dir:
        dest_dir = os.path.join(output_dir, "stage2_agent2_domain", "iterations")
        os.makedirs(dest_dir, exist_ok=True)
        file_name = f"reference_guidelines_iter_{guideline_iter + 1}.json"
        file_path = os.path.join(dest_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"📄 Iteration {guideline_iter + 1} saved to {file_path}")

    log_interaction("agent2_develop_guidelines", system_prompt, user_prompt, output_content)
    
    current_iter = state.get('iteration_count', 0)

    # Extract agent2_capabilities from the JSON output
    parsed = extract_json_from_text(output_content)
    agent2_caps = json.dumps(parsed.get("agent2_capabilities", []), indent=2) if parsed else ""

    return {
        "reference_guidelines_draft": output_content,
        "iteration_count": current_iter + 1,
        "guideline_iteration_count": guideline_iter + 1,
        "agent2_capabilities": agent2_caps
    }

def extract_language_question(state: AgentState) -> dict:
    """
    Parses the Reference Guidelines draft JSON for Questions to Agent 1.
    If questions exist, it sets current_language_question to the full list.
    """
    draft = state.get('reference_guidelines_draft', '')
    
    # Try to extract JSON from code blocks if present
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', draft, re.DOTALL)
    json_str = json_match.group(1) if json_match else draft.strip()
    
    try:
        data = json.loads(json_str)
        questions_list = data.get("questions_to_language_advisor", data.get("language_questions", []))
        
        if questions_list:
            questions_text = "\n".join(str(q) for q in questions_list)
            print(f"\n[Router]: Found Questions for Agent 1:\n{questions_text}")
            return {"current_language_question": questions_text}
            
    except json.JSONDecodeError:
        print("\n[Router Error]: Failed to parse JSON from Agent 2 Reference Guidelines.")

    print("\n[Router]: No questions found for Agent 1. Iteration complete.")
    return {"current_language_question": ""}

def answer_domain_question(state: AgentState) -> dict:
    """
    Node function representing Agent 2 (Reference Builder) executing A2-T2(a).
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: answer_domain_question (Agent 2)")
    
    system_prompt = get_agent_2_answer_domain_questions_system_prompt(
        domain_description=state.get('domain_description', ''),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        question_text=state.get('current_domain_question', '[]')
    )
    user_prompt = get_agent_2_answer_domain_questions_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print("✅ Domain question answered.")
    
    log_interaction("agent2_answer_domain_question", system_prompt, user_prompt, output_content)
    
    domain_iter = state.get('compliance_domain_iteration_count', 0)
    qa_log = state.get('case_qa_log', [])
    qa_log = qa_log + [{
        "type": "domain",
        "iteration": domain_iter + 1,
        "question": state.get('current_domain_question', ''),
        "answer": output_content
    }]
    
    updates = {
        "current_domain_answer": output_content,
        "compliance_domain_iteration_count": domain_iter + 1,
        "case_qa_log": qa_log
    }
    
    stage = state.get('current_stage', 0)
    if stage == 3:
        updates["discovery_agent2_iteration_count"] = state.get("discovery_agent2_iteration_count", 0) + 1
    elif stage == 4:
        updates["additional_agent2_iteration_count"] = state.get("additional_agent2_iteration_count", 0) + 1
        
    return updates

def rethink_reference_guidelines(state: AgentState) -> dict:
    """
    Node function representing Agent 2 executing A2-T2(b) (Iterate Reference Guidelines).
    This loop happens after answering Domain Questions, to revise the guidelines based on the answers.
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: rethink_reference_guidelines (Agent 2)")
    
    rethink_iter = state.get('rethink_iteration_count', 0)
    
    # Combine the question and answer for context
    domain_qa_with_flags = f"Question: {state.get('current_domain_question', 'N/A')}\n\nAnswer: {state.get('current_domain_answer', 'N/A')}"
    
    system_prompt = get_agent_2_iterate_guidelines_revision_system_prompt(
        current_guidelines=state.get('reference_guidelines_draft', ''),
        domain_qa_with_flags=domain_qa_with_flags,
        suggested_alternatives=state.get('suggested_alternatives', 'N/A'),
        language_guidelines=state.get('language_template', ''),
        language_answers=state.get('current_language_answer', ''),
        iteration=rethink_iter
    )
    user_prompt = get_agent_2_iterate_guidelines_revision_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print("✅ Reference Guidelines rethought and updated.")
    
    log_interaction("agent2_rethink_guidelines", system_prompt, user_prompt, output_content)
    
    # Extract and enrich change log
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case_id = cases[current_index].get('case_id', 'Unknown') if cases and current_index < len(cases) else 'Unknown'
    
    guideline_change_log = state.get('guideline_change_log', [])
    alternative_change_log = state.get('alternative_change_log', [])
    new_logs = []
    new_alt_logs = []
    
    # Extract and parse JSON
    data = extract_json_from_text(output_content)
    
    if data:
        changes = data.get("change_log", [])
        if isinstance(changes, list):
            for change in changes:
                if isinstance(change, dict):
                    change['case_id'] = current_case_id
                    change['rethink_iteration'] = rethink_iter
                    new_logs.append(change)
                    
                    # Filter for alternative_description changes
                    summary = str(change.get('summary', '')).lower()
                    if 'alternative_description' in summary:
                        alt_entry = change.copy()
                        alt_entry['suggested_by_case'] = current_case_id
                        alt_entry['trigger_suggestions'] = state.get('suggested_alternatives', 'N/A')
                        new_alt_logs.append(alt_entry)
                elif isinstance(change, str):
                    log_entry = {
                        "case_id": current_case_id,
                        "rethink_iteration": rethink_iter,
                        "summary": change
                    }
                    new_logs.append(log_entry)
                    if 'alternative_description' in change.lower():
                        alt_entry = log_entry.copy()
                        alt_entry['suggested_by_case'] = current_case_id
                        alt_entry['trigger_suggestions'] = state.get('suggested_alternatives', 'N/A')
                        new_alt_logs.append(alt_entry)
    else:
        print("\n[Node Error]: Failed to parse JSON from Agent 2 Rethink Guidelines.")
        
    # Extract agent2_capabilities from the rethink output
    parsed = extract_json_from_text(output_content)
    agent2_caps = json.dumps(parsed.get("agent2_capabilities", []), indent=2) if parsed else state.get("agent2_capabilities", "[]")

    return {
        "reference_guidelines_draft": output_content,
        "rethink_iteration_count": rethink_iter + 1,
        "guideline_change_log": guideline_change_log + new_logs,
        "alternative_change_log": alternative_change_log + new_alt_logs,
        "agent2_capabilities": agent2_caps
    }

def save_initial_reference_guidelines(state: AgentState) -> dict:
    """
    Saves the Reference Guidelines (enriched with capabilities) before Agent 3 begins.
    """
    output_dir = state.get("output_dir", "")
    if output_dir:
        enriched = _merge_capabilities_into_json(
            state.get("reference_guidelines_draft", ""),
            state.get("agent1_capabilities", ""),
            state.get("agent2_capabilities", "")
        )
        file_path = os.path.join(output_dir, "stage2_agent2_domain", "initial_reference_guidelines.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(enriched)
        print(f"\n[Node]: save_initial_reference_guidelines - Saved to {file_path}")
    return {}


def evaluate_compliance_initial(state: AgentState) -> dict:
    """
    Node function representing Agent 3 (Compliance Evaluator) executing A3-T1(a) (First Iteration).
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: evaluate_compliance_initial (Agent 3)")
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    system_prompt = get_agent_3_iterate_case_evaluation_system_prompt(
        case_model=current_case.get('case_model', ''),
        case_id=current_case.get('case_id', 'Unknown'),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        lang_questions_answers="",
        domain_questions_answers="",
        agent1_capabilities=state.get('agent1_capabilities', ''),
        agent2_capabilities=state.get('agent2_capabilities', ''),
        verifier_feedback=state.get('verifier_feedback', '')
    )
    user_prompt = get_agent_3_iterate_case_evaluation_initial_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print(f"✅ Initial Compliance Vector generated for {current_case.get('case_id', 'Unknown')}.")
    
    log_interaction("agent3_evaluate_compliance_initial", system_prompt, user_prompt, output_content)
    
    current_iter = state.get('case_iteration_count', 0)
    return {
        "compliance_vector_draft": output_content,
        "case_iteration_count": current_iter + 1
    }

def evaluate_compliance_iterate(state: AgentState) -> dict:
    """
    Node function representing Agent 3 (Compliance Evaluator) executing A3-T1(a) (Subsequent Iteration).
    """
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: evaluate_compliance_iterate (Agent 3)")
    
    current_iter = state.get('case_iteration_count', 0)
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    system_prompt = get_agent_3_iterate_case_evaluation_system_prompt(
        case_model=current_case.get('case_model', ''),
        case_id=current_case.get('case_id', 'Unknown'),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        lang_questions_answers=state.get('current_language_answer', ''),
        domain_questions_answers=state.get('current_domain_answer', ''),
        agent1_capabilities=state.get('agent1_capabilities', ''),
        agent2_capabilities=state.get('agent2_capabilities', ''),
        verifier_feedback=state.get('verifier_feedback', '')
    )
    user_prompt = get_agent_3_iterate_case_evaluation_iterate_user_prompt()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    output_content = response.choices[0].message.content
    print(f"✅ Compliance Vector updated for {current_case.get('case_id', 'Unknown')}.")
    
    log_interaction("agent3_evaluate_compliance_iterate", system_prompt, user_prompt, output_content)
    
    return {
        "compliance_vector_draft": output_content,
        "case_iteration_count": current_iter + 1
    }

def extract_compliance_questions(state: AgentState) -> dict:
    """
    Parses the Compliance Vector draft JSON for Questions to Agent 1 (Language) and Agent 2 (Domain).
    Sets current_language_question and current_domain_question.
    """
    draft = state.get('compliance_vector_draft', '')
    
    lang_q = ""
    domain_q = ""
    suggested_alts = []
    
    # Extract and parse JSON
    data = extract_json_from_text(draft)
    
    if data:
        # Agent 3 prompt outputs lowercase snake_case keys; fall back to PascalCase for safety
        lang_list = data.get("questions_to_language_advisor", data.get("language_questions", data.get("Language_Questions", [])))
        domain_list = data.get("questions_to_domain_advisor", data.get("domain_questions", data.get("Domain_Questions", [])))
        
        # Aggregate suggested alternatives from compliance_vector
        comp_vector = data.get("compliance_vector", data.get("Compliance_Vector", []))
        for entry in comp_vector:
            alts = entry.get("suggested_alternatives", entry.get("Suggested_Alternatives", []))
            if alts:
                # Format as GuidelineID: [Alternative1, Alternative2]
                g_id = entry.get("guideline_id", entry.get("Guideline_Id", "Unknown"))
                suggested_alts.append(f"{g_id}: {alts}")

        if lang_list:
            lang_q = "\n".join(str(q) for q in lang_list)
            print(f"\n[Router]: Found Language Questions:\n{lang_q}")
            
        if domain_list:
            domain_q = "\n".join(str(q) for q in domain_list)
            print(f"\n[Router]: Found Domain Questions:\n{domain_q}")        
            
        if suggested_alts:
            print(f"\n[Router]: Found Suggested Alternatives:\n" + "\n".join(suggested_alts))
    else:
        print("\n[Router Error]: Failed to parse JSON from Agent 3 Compliance Vector.")
    
    if not lang_q and not domain_q and not suggested_alts:
        print("\n[Router]: No questions or suggestions found. Iteration complete.")
        
    return {
        "current_language_question": lang_q,
        "current_domain_question": domain_q,
        "suggested_alternatives": "\n".join(suggested_alts) if suggested_alts else ""
    }

def save_and_next_case(state: AgentState) -> dict:
    """
    Saves the current case's evaluation to the accumulated feedback and increments the case index.
    Consolidates findings from Evidence Extraction (Stage 1), 
    Alternative Pattern Discovery (Stage 2), and Additional Elements Analysis (Stage 4).
    """
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    cases_feedback = state.get('cases_feedback', [])
    
    # 1. Get reference guidelines to iterate over
    ref_guidelines_raw = state.get('reference_guidelines_draft', '')
    ref_data = extract_json_from_text(ref_guidelines_raw)
    guidelines = ref_data.get('reference_guidelines', []) if isinstance(ref_data, dict) else []
    
    # 2. Get stage 1 & 2 findings (dicts keyed by guideline_id)
    evidence_dict = state.get('intermediate_evidence', {})
    discovered_dict = state.get('discovered_alternatives', {})
    
    # 3. Consolidate Evidence and Alternatives for each guideline
    compliance_vector = []
    for g in guidelines:
        # Agent 2 output uses 'id', Agent 3 stages use 'guideline_id'
        g_id = g.get('id') or g.get('guideline_id', 'Unknown')
        g_desc = g.get('description', 'Unknown')
        
        # Start with a base entry
        entry = {
            "guideline_id": g_id,
            "description": g_desc,
            "fragments": [],
            "new_fragments": [],
            "label": "Not-Satisfied",
            "justification": "",
            "matched_via": "none"
        }
        
        # Add Stage 1 evidence if found
        if g_id in evidence_dict:
            e = evidence_dict[g_id]
            entry["fragments"] = e.get("fragments", [])
            # Support both 'label' and 'compliance_status'
            entry["label"] = e.get("label") or e.get("compliance_status", "Not-Satisfied")
            entry["notes"] = e.get("notes", "")
            entry["matched_via"] = e.get("matched_via", "primary")
            
        # Add Stage 2 alternatives (and potentially upgrade label)
        if g_id in discovered_dict:
            a = discovered_dict[g_id]
            # Handle both 'new_fragment' and 'new_fragments'
            entry["new_fragments"] = a.get("new_fragments") or ([a.get("new_fragment")] if a.get("new_fragment") else [])
            entry["justification"] = a.get("justification", "")
            # Support both 'label' and 'compliance_status'
            a_label = a.get("label") or a.get("compliance_status", "Not-Satisfied")
            # Label priority: Satisfied > Partially-Satisfied > Not-Satisfied
            label_priority = {"Satisfied": 3, "Partially-Satisfied": 2, "Not-Satisfied": 1}
            # Cast label strings to str to avoid Pyre issues
            cur_label = str(entry["label"])
            new_label = str(a_label)
            if label_priority.get(new_label, 0) > label_priority.get(cur_label, 0):
                entry["label"] = new_label
                entry["matched_via"] = a.get("matched_via", "alternative")
            elif a_label != "Not-Satisfied" and entry["matched_via"] == "none":
                # Ensure matched_via is set if an alternative was considered even if label didn't improve
                entry["matched_via"] = a.get("matched_via", "alternative")

        compliance_vector.append(entry)
        
    # 4. Final data object per case
    data = {
        "case_id": current_case.get('case_id', 'Unknown'),
        "compliance_vector": compliance_vector,
        "additional_elements_evaluation": state.get('additional_elements_evaluation', [])
    }

    # Stamp iteration metadata before saving
    data['evaluation_iterations'] = state.get('case_iteration_count', 0)
    data['discovery_agent1_iterations'] = state.get('discovery_agent1_iteration_count', 0)
    data['discovery_agent2_iterations'] = state.get('discovery_agent2_iteration_count', 0)
    data['lang_question_iterations'] = state.get('compliance_lang_iteration_count', 0)
    data['domain_question_iterations'] = state.get('compliance_domain_iteration_count', 0)
    data['rethink_iterations'] = state.get('rethink_iteration_count', 0)
    data['additional_agent1_iterations'] = state.get('additional_agent1_iteration_count', 0)
    data['additional_agent2_iterations'] = state.get('additional_agent2_iteration_count', 0)
    data['qa_history'] = state.get('case_qa_log', [])

    # Save this specific case evaluation to its own file
    output_dir = state.get("output_dir", "")
    if output_dir:
        case_id_safe = str(data.get('case_id', 'unknown')).replace('/', '_').replace('\\', '_')
        case_file_path = os.path.join(output_dir, "stage3_agent3_compliance", f"{case_id_safe}.json")
        with open(case_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    # Append the dict to the cases feedback list
    new_feedback = cases_feedback + [data]
    
    print(f"\n[Node]: save_and_next_case - Combined results and saved feedback for {current_case.get('case_id', 'Unknown')}")
    
    return {
        "cases_feedback": new_feedback,
        "current_case_index": current_index + 1,
        "compliance_vector_draft": "",   # Reset draft for next case
        "current_language_question": "", # Clear questions from previous case
        "current_domain_question": "",
        "current_language_answer": "",   # Clear answers from previous case
        "current_domain_answer": "",
        "case_qa_log": [],               # Reset Q&A log for the next case
        # Reset all per-case iteration counters so the next case starts clean
        "case_iteration_count": 0,
        "compliance_domain_iteration_count": 0,
        "rethink_iteration_count": 0,
        "verifier_feedback": "",
        "verification_iteration_count": 0,
        "intermediate_evidence": {},
        "discovered_alternatives": {},
        "additional_elements_evaluation": [], # Reset for next case
        "discovery_agent1_iteration_count": 0,
        "discovery_agent2_iteration_count": 0,
        "additional_agent1_iteration_count": 0,
        "additional_agent2_iteration_count": 0,
    }

def extract_evidence(state: AgentState) -> dict:
    """
    Node function representing Stage 1 of Compliance Evaluation.
    Identifies exact fragments from the case model that match primary or alternative descriptions.
    """
    from prompts import get_agent_3_extract_evidence_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: extract_evidence (Stage 1)")
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    system_prompt = get_agent_3_extract_evidence_system_prompt(
        case_model=current_case.get('case_model', ''),
        reference_guidelines=state.get('reference_guidelines_draft', '')
    )
    user_prompt = "Execute Task 3.1 (A) — Evidence Extraction."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
    except Exception as e:
        print(f"\n❌ OpenAI Request Failed: {e}")
        raise e
    
    output_content = response.choices[0].message.content
    log_interaction("agent3_extract_evidence", system_prompt, user_prompt, output_content)
    
    data = extract_json_from_text(output_content)
    # Support both new prompts_9.yaml 'existing_mapping' and older 'evidence' keys
    if "existing_mapping" in data:
        data = verify_json(data, ["existing_mapping"], "agent3_extract_evidence")
        evidence = data.get("existing_mapping", [])
    else:
        data = verify_json(data, ["evidence"], "agent3_extract_evidence")
        evidence = data.get("evidence", [])
    
    # Store evidence as a dict for easier access in next stages
    evidence_dict = {}
    for item in evidence:
        if isinstance(item, dict):
            g_id = item.get("guideline_id", "Unknown")
            # Ensure label exists if LLM didn't provide it
            if "label" not in item:
                item["label"] = item.get("compliance_status", "Not-Satisfied")
            if "fragments" not in item:
                item["fragments"] = [item.get("evidence", "")] if item.get("evidence") else []
            evidence_dict[g_id] = item
    
    return {
        "intermediate_evidence": evidence_dict,
        "compliance_vector_draft": output_content # Initialize draft with Stage 1 results
    }

def discover_alternatives(state: AgentState) -> dict:
    """
    Node function representing Stage 2 of Compliance Evaluation.
    Searches for new modeling patterns for guidelines that currently lack evidence.
    """
    from prompts import get_agent_3_discover_alternatives_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: discover_alternatives (Stage 2)")
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    import json
    system_prompt = get_agent_3_discover_alternatives_system_prompt(
        case_model=current_case.get('case_model', ''),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        intermediate_evidence=json.dumps(state.get('intermediate_evidence', {})),
        agent1_capabilities=state.get('agent1_capabilities', ''),
        agent2_capabilities=state.get('agent2_capabilities', ''),
        lang_questions_answers=state.get('lang_questions_answers', ''),
        domain_questions_answers=state.get('domain_questions_answers', ''),
        iteration=state.get('discovery_agent1_iteration_count', 0) + state.get('discovery_agent2_iteration_count', 0) + 1
    )
    user_prompt = "Execute Task 3.1 (B) — Alternative Pattern Discovery."
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    
    output_content = response.choices[0].message.content
    log_interaction("agent3_discover_alternatives", system_prompt, user_prompt, output_content)
    
    data = extract_json_from_text(output_content)
    # Stage 2 now returns a consolidated compliance vector
    compliance_vector = data.get("potential_found", data.get("compliance_vector", []))
    
    # Still extract and store individual discoveries for tracker/logs
    discovered_dict = {}
    for item in compliance_vector:
        g_id = item.get("guideline_id", "Unknown")
        if "fragments" not in item and "evidence" in item:
            item["new_fragments"] = [item.get("evidence")]
            item["matched_via"] = "alternative"
            item["justification"] = item.get("notes", "")
            
        # If it was matched via alternative, or has new fragments, we treat it as a discovery
        if item.get("matched_via") == "alternative" or item.get("new_fragments"):
            # Normalize label
            if "label" not in item:
                item["label"] = item.get("compliance_status") or ("Satisfied" if item.get("new_fragments") else "Not-Satisfied")
            discovered_dict[g_id] = item
    
    # Extract questions if any
    lang_q_list = data.get("questions_to_language_advisor", data.get("language_questions", []))
    domain_q_list = data.get("questions_to_domain_advisor", data.get("domain_questions", []))
    
    current_lang_q = "\n".join(str(q) for q in lang_q_list) if lang_q_list else ""
    current_domain_q = "\n".join(str(q) for q in domain_q_list) if domain_q_list else ""
    
    if current_lang_q:
        print(f"\n[Router]: Agent 3 has Language Questions during discovery:\n{current_lang_q}")
    if current_domain_q:
        print(f"\n[Router]: Agent 3 has Domain Questions during discovery:\n{current_domain_q}")

    # Track changes in alternative_change_log if any new patterns found
    new_logs = []
    if discovered_dict:
        for g_id, item in discovered_dict.items():
            new_logs.append({
                "case_id": current_case.get('case_id', 'Unknown'),
                "guideline_id": g_id,
                "new_fragments": item.get("new_fragments"),
                "justification": item.get("justification"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    current_discovery_iter = state.get('discovery_agent1_iteration_count', 0) + state.get('discovery_agent2_iteration_count', 0)
    
    return {
        "discovered_alternatives": discovered_dict,
        "compliance_vector_draft": json.dumps({"compliance_vector": compliance_vector}, indent=2),
        "alternative_change_log": state.get('alternative_change_log', []) + new_logs,
        "current_language_question": current_lang_q,
        "current_domain_question": current_domain_q,
        "current_stage": 3,
        "current_language_answer": "", 
        "current_domain_answer": ""
    }

def consolidate_compliance(state: AgentState) -> dict:
    """
    Consolidates findings from Stage 1 (evidence) and Stage 2 (discovery) 
    into a final compliance vector without another LLM call.
    """
    print("\n[Node]: consolidate_compliance (Stage 3 - Unified)")
    
    evidence = state.get('intermediate_evidence', {})
    discovery = state.get('discovered_alternatives', {})
    
    # Start with evidence labels
    final_vector = []
    for g_id, item in evidence.items():
        # If discovery found a better alternative, use that
        if g_id in discovery:
            disc_item = discovery[g_id]
            # Merge information
            consolidated = {
                "guideline_id": g_id,
                "label": disc_item.get("label", item.get("label", "Not-Satisfied")),
                "fragments": item.get("fragments", []) + disc_item.get("new_fragments", []),
                "matched_via": disc_item.get("matched_via", item.get("matched_via", "none")),
                "notes": f"Primary Match: {item.get('notes', 'None')}. Alternative Match: {disc_item.get('justification', 'None')}."
            }
            final_vector.append(consolidated)
        else:
            final_vector.append(item)
            
    # Add any discovery items that might have missed the evidence list (shouldn't happen but safe)
    evidence_ids = set(evidence.keys())
    for g_id, disc_item in discovery.items():
        if g_id not in evidence_ids:
            final_vector.append({
                "guideline_id": g_id,
                "label": disc_item.get("label", "Not-Satisfied"),
                "fragments": disc_item.get("new_fragments", []),
                "matched_via": disc_item.get("matched_via", "none"),
                "notes": disc_item.get("justification", "None")
            })
            
    return {"compliance_vector_draft": json.dumps({"evidence": final_vector}, indent=2)}

def label_compliance(state: AgentState) -> dict:
    """
    Node function representing Stage 3 of Compliance Evaluation.
    Assigns final compliance labels based on evidence and discovery findings using an LLM.
    """
    from prompts import get_agent_3_label_compliance_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: label_compliance (Stage 3)")
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    import json
    system_prompt = get_agent_3_label_compliance_system_prompt(
        case_id=current_case.get('case_id', 'Unknown'),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        intermediate_evidence=json.dumps(state.get('intermediate_evidence', {})),
        discovered_alternatives=json.dumps(state.get('discovered_alternatives', {})),
        lang_questions_answers=state.get('lang_questions_answers', ''),
        domain_questions_answers=state.get('domain_questions_answers', '')
    )
    user_prompt = "Execute Task 3.1 (C) — Final Labeling."
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    
    output_content = response.choices[0].message.content
    log_interaction("agent3_label_compliance", system_prompt, user_prompt, output_content)
    
    data = extract_json_from_text(output_content)
    
    return {"compliance_vector_draft": json.dumps(data)}

def analyze_additional_elements(state: AgentState) -> dict:
    """
    Node function representing Stage 4 of Compliance Evaluation.
    Identifies and evaluates model elements not covered by guidelines.
    Can ask Agent 1 (Language) or Agent 2 (Domain) questions.
    """
    from prompts import get_agent_3_analyze_alien_elements_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print(f"\n[Node]: analyze_additional_elements (Stage 4, Iteration {state.get('additional_agent1_iteration_count', 0) + state.get('additional_agent2_iteration_count', 0)})")
    
    # Extract current case
    cases = state.get('cases', [])
    current_index = state.get('current_case_index', 0)
    current_case = cases[current_index] if cases and current_index < len(cases) else {"case_id": "Unknown", "case_model": ""}
    
    system_prompt = get_agent_3_analyze_alien_elements_system_prompt(
        case_id=current_case.get('case_id', 'Unknown'),
        case_model=current_case.get('case_model', ''),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        domain_description=state.get('domain_description', ''),
        language_guidelines=state.get('language_template', ''),
        compliance_vector=state.get('compliance_vector_draft', ''),
        agent1_capabilities=state.get('agent1_capabilities', ''),
        agent2_capabilities=state.get('agent2_capabilities', '')
    )
    user_prompt = "Execute Agent 3 Stage 4 — Analyze Additional Elements."
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    
    output_content = response.choices[0].message.content
    log_interaction("agent3_analyze_additional_elements", system_prompt, user_prompt, output_content)
    
    data = extract_json_from_text(output_content)
    # Support both new prompts_9.yaml terminology and older ones for compatibility
    eval_list = data.get("uncovered_fragment", data.get("additional_elements_evaluation", data.get("alien_elements_evaluation", [])))
    
    # NEW: also capture the compliance_vector if returned 
    compliance_vector = data.get("compliance_vector", [])
    
    # Extract questions
    lang_q_list = data.get("questions_to_language_advisor", data.get("language_questions", []))
    domain_q_list = data.get("questions_to_domain_advisor", data.get("domain_questions", []))
    
    current_lang_q = "\n".join(str(q) for q in lang_q_list) if lang_q_list else ""
    current_domain_q = "\n".join(str(q) for q in domain_q_list) if domain_q_list else ""
    
    if current_lang_q:
        print(f"\n[Router]: Agent 3 has Language Questions during additional elements analysis:\n{current_lang_q}")
    if current_domain_q:
        print(f"\n[Router]: Agent 3 has Domain Questions during additional elements analysis:\n{current_domain_q}")
    
    return {
        "additional_elements_evaluation": eval_list,
        "compliance_vector_draft": json.dumps({"compliance_vector": compliance_vector}, indent=2) if compliance_vector else state.get('compliance_vector_draft', ''),
        "current_language_question": current_lang_q,
        "current_domain_question": current_domain_q,
        "current_stage": 4
    }

def identify_deviation_patterns(state: AgentState) -> dict:
    """
    Node function representing Agent 4 executing A4-T1.
    """
    from prompts import get_agent_4_identify_deviation_patterns_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: identify_deviation_patterns (Stage 4)")
    
    cases_feedback = state.get('cases_feedback', [])
    
    compliance_vectors = []
    uncovered_fragments = []
    for c in cases_feedback:
        compliance_vectors.append({"case_id": c.get("case_id"), "compliance_vector": c.get("compliance_vector", [])})
        uncovered_fragments.append({"case_id": c.get("case_id"), "uncovered_fragment_classifications": c.get("additional_elements_evaluation", [])})
        
    system_prompt = get_agent_4_identify_deviation_patterns_system_prompt(
        compliance_vectors=json.dumps(compliance_vectors, indent=2),
        uncovered_fragment_classifications=json.dumps(uncovered_fragments, indent=2),
        reference_guidelines=state.get('reference_guidelines_draft', '')
    )
    user_prompt = "Identify deviation patterns across all case evaluations according to the system instructions."
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    output_content = response.choices[0].message.content
    print("✅ Deviation patterns identified.")
    
    log_interaction("agent4_identify_deviation_patterns", system_prompt, user_prompt, output_content)
    
    output_dir = state.get("output_dir", "")
    if output_dir:
        os.makedirs(os.path.join(output_dir, "stage4_agent4_variability"), exist_ok=True)
        file_path = os.path.join(output_dir, "stage4_agent4_variability", "deviation_patterns.json")
        with open(file_path, "w", encoding="utf-8") as f:
            data = extract_json_from_text(output_content)
            if data:
                json.dump(data, f, indent=2)
            else:
                f.write(output_content)
            
    return {"deviation_patterns": output_content}

def classify_variability(state: AgentState) -> dict:
    """
    Node function representing Agent 4 executing A4-T2.
    """
    from prompts import get_agent_4_classify_variability_system_prompt
    client = OpenAI(api_key=state['api_key'])
    model = state['model']
    
    print("\n[Node]: classify_variability (Stage 4)")
    
    system_prompt = get_agent_4_classify_variability_system_prompt(
        deviation_patterns=state.get('deviation_patterns', ''),
        reference_guidelines=state.get('reference_guidelines_draft', ''),
        domain_description=state.get('domain_description', ''),
        lang_questions_answers=state.get('lang_questions_answers', ''),
        domain_questions_answers=state.get('domain_questions_answers', '')
    )
    user_prompt = "Classify the identified variability and suggest updates based on the system instructions."
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    output_content = response.choices[0].message.content
    print("✅ Variability classified.")
    
    log_interaction("agent4_classify_variability", system_prompt, user_prompt, output_content)
    
    output_dir = state.get("output_dir", "")
    if output_dir:
        os.makedirs(os.path.join(output_dir, "stage4_agent4_variability"), exist_ok=True)
        file_path = os.path.join(output_dir, "stage4_agent4_variability", "variability_classifications.json")
        with open(file_path, "w", encoding="utf-8") as f:
            data = extract_json_from_text(output_content)
            if data:
                json.dump(data, f, indent=2)
            else:
                f.write(output_content)
            
    return {"variability_classifications": output_content}
