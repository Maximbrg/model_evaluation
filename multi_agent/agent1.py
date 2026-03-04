from openai import OpenAI

class Agent1:
    """
    Agent 1: The Instruction Expert.
    Responsible for evaluating whether components of a class diagram 
    follow the specific formatting and diagramming instructions provided.
    """
    def __init__(self, api_key: str, model: str, instructions_text: str, model_type: str = "class diagram"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        if instructions_text.strip():
            rules_context = f"--- LANGUAGE DEFINITION (Metamodel/Grammar) ---\n{instructions_text}\n-----------------\n"
        else:
            rules_context = f"--- LANGUAGE DEFINITION ---\nNo formal metamodel provided. You MUST apply standard, universally accepted theoretical rules for a '{model_type}'.\n-----------------\n"
            
        self.system_prompt = (
            "You are Agent 1: Language Understanding (Interpreter)\n\n"
            "Responsibility: Acts as the syntactic engine of the system. Ingests formal rules, grammars, or metamodels that dictate how information is structured. Provides templates and answers queries regarding syntactic rules.\n\n"
            f"As a Syntactic Engine, your primary objective is to prepare a template for evaluating specifications in {model_type}. "
            "You are responsible for identifying mandatory primary elements (e.g., entities/nodes), defining their mandatory properties (including types) and behaviors, identifying relationships, and realizing abstractions using the language's specific mechanisms. "
            "Prioritize the guidelines in the LANGUAGE DEFINITION, if provided.\n\n"
            "To ensure peak precision, follow these operational directives:\n"
            f"- Template Generation: When queried by Agent 2, generate and provide a precise, structured template for Evaluation Guidelines and Constraints specifically tailored to the syntax and capabilities of the {model_type}, formatted strictly as a raw CSV string with appropriate headers.\n"
            "- Strict Enforcement: Base all syntactic and structural validations strictly on the provided language definition or universally accepted theoretical rules.\n"
            "- Query Resolution: Answer questions from Agents 2 and 3 regarding naming conventions, required notations, and diagram syntax definitively.\n"
            "- Boundary Maintenance: Strictly confine your analysis to structural validity. Do not evaluate or comment on domain accuracy or semantic meaning.\n\n"
            "Your final output must be delivered as clear, definitive answers or structural templates formatted as a raw CSV string (without markdown code blocks) to the querying agents.\n\n"
            f"{rules_context}"
        )

    def generate_response(self, prompt: str, history: list = None) -> str:
        if history is None:
            history = []
            
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content
