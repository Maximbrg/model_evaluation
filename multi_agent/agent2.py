from openai import OpenAI
import os
import json

class Agent2:
    """
    Agent 2: The Information/Domain Expert.
    Understands the problem description and the suggested solution.
    """
    def __init__(self, api_key: str, model: str, problem_desc: str, suggested_diagram: str, output_dir: str, agent1=None, model_type: str = "class diagram"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.output_dir = output_dir
        self.agent1 = agent1
        
        if suggested_diagram.strip():
            reference_context = f"--- REFERENCE MODEL (Suggested Diagram) ---\n{suggested_diagram}\n---------------------------\n"
            behavior_context = (
                "When queried, focus strictly on whether the provided concepts, relationships, "
                "or structures make sense for the problem domain and align with the reference model's intent."
            )
        else:
            reference_context = "--- REFERENCE MODEL (Suggested Diagram) ---\nNo reference model was provided.\n---------------------------\n"
            behavior_context = (
                "When queried, focus strictly on whether the provided concepts make sense for the domain description.\n"
                f"Evaluate and extract all expected {model_type} elements independently based purely on the domain description."
            )
            
        self.system_prompt = (
            "You are Agent 2: Domain Understanding (Analyzer).\n\n"
            f"As a Domain Expert, your primary objective is to establish and uphold the \"ground truth\" for the specified domain. "
            f"You are responsible for creating rigorous Evaluation Guidelines and Constraints for {model_type} that mirror the exact requirements of the domain, as specified in the problem description.\n\n"
            "To ensure peak precision, follow these operational directives:\n"
            f"- Template Acquisition: Before drafting any guidelines, proactively consult Agent 1 to retrieve a structural template for the {model_type} constraints.\n"
            "- Standardization: Root all guidelines, strictly formatting them according to the template provided by Agent 1.\n"
            "- Collaboration: Consult Agent 1 to resolve any linguistic ambiguities or complex semantic mappings.\n"
            "- Objectivity: Strictly adhere to the provided domain description. Do not introduce outside assumptions or speculative data.\n"
            "- Flexibility: Where the domain allows for multiple valid interpretations, clearly list all acceptable alternatives.\n"
            "- Quality Control: Execute a mandatory Plan -> Review -> Finalize workflow for every constraint before delivery.\n\n"
            "Your final output must be delivered as a valid CSV string with the following headers: ID, Guideline/Constraint, Evidence. Do not wrap the CSV in markdown code blocks.\n\n"
            f"--- DOMAIN DESCRIPTION ---\n{problem_desc}\n---------------------------\n\n"
            f"{reference_context}\n"
            "You must ALWAYS return your answer purely as a JSON object with these keys:\n"
            "- 'action': either 'ask_agent_1' or 'finalize'.\n"
            "- 'content': The question for Agent 1, OR your final answer formatted as the required raw CSV string to the querier."
        )

    def generate_response(self, prompt: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": prompt})
        
        for iteration in range(3):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" }
            )
            
            try:
                decision = json.loads(response.choices[0].message.content)
            except Exception:
                return response.choices[0].message.content
                
            action = decision.get("action")
            content = decision.get("content", "")
            
            if action == 'ask_agent_1' and self.agent1:
                print("\033[33m[Agent 2] -> Asking Agent 1 (Interpreter)...\033[0m")
                agent1_reply = self.agent1.generate_response(content)
                print(f"\033[32m[Agent 1] -> {agent1_reply}\033[0m")
                
                import csv
                with open(os.path.join(self.output_dir, "interactions.csv"), "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Agent 2", "Agent 1", content, "Reference: template.csv"])
                    
                with open(os.path.join(self.output_dir, "template.csv"), "w", encoding='utf-8') as f:
                    f.write(agent1_reply)
                
                messages.append({"role": "assistant", "content": response.choices[0].message.content})
                messages.append({"role": "user", "content": f"Agent 1 replied: {agent1_reply}"})
            else:
                return content
                
        return content
