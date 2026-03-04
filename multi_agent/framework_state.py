from typing import TypedDict

class AgentState(TypedDict, total=False):
    # Configurations
    api_key: str
    model_name: str
    output_dir: str
    model_type: str
    instructions_text: str
    domain_desc: str
    case_model: str
    
    # Process variables
    template: str
    needs_template: bool
    guidelines: str
    feedback: str
    is_satisfactory: bool
    needs_syntax_answer: bool
    syntax_question: str
    syntax_history: str
    iteration: int
