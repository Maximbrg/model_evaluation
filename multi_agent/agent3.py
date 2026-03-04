import os
import json
from openai import OpenAI
from agent1 import Agent1
from agent2 import Agent2

class Agent3:
    """
    Agent 3: Case Understanding (Reasoner).
    Acts as the instance/case evaluator. It takes the specific, raw Case Model and evaluates it.
    """
    def __init__(self, api_key: str, model: str, agent1: Agent1, agent2: Agent2, student_diagram: str, output_dir: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.agent1 = agent1
        self.agent2 = agent2
        self.log_file = os.path.join(output_dir, "interactions.csv")
        
        self.student_diagram = student_diagram
        self.base_prompt = (
            "You are Agent 3: Case Understanding (Reasoner).\n\n"
            "As a Case Evaluator, your primary objective is to audit the student's solution against the rigorous guidelines established in the evaluation guide. "
            "You are responsible for acting as the final arbiter of correctness, ensuring that the student's solution logically satisfies every domain constraint.\n\n"
            "To ensure peak precision, follow these operational directives:\n"
            "- Systematic Mapping: Systematically align every fragment in the student's solution with the corresponding ID from the evaluation guide.\n"
            "- Semantic Verification: If the student's solution uses terminology that differs from the evaluation guide, consult Agent 2 (Analyzer) to determine if the meaning is preserved.\n"
            "- Syntactic Verification: Consult Agent 1 (Interpreter) if the student's solution falls within a \"Flexibility Clause\" defined in the language.\n"
            "- Logical Reasoning: For every discrepancy found, provide a clear, logical explanation of why the case model fails the constraint.\n\n"
            "Your final output must be delivered as a Feedback Evaluation Matrix formatted as a raw CSV string with appropriate headers (e.g., Guideline ID, Student Fragment, Status, Reasoning). Do not wrap the CSV in markdown code blocks.\n\n"
            "--- EVALUATION GUIDELINES/CONSTRAINTS ---\n"
            "{eval_guide}\n\n"
            f"--- CASE MODEL ---\n{self.student_diagram}\n---------------------------\n\n"
            "You must ALWAYS return your answer purely as a JSON object with these keys:\n"
            "- 'action': either 'ask_agent_1', 'ask_agent_2', or 'finalize'.\n"
            "- 'content': The question for the respective agent, OR your final Feedback Evaluation Matrix formatted as a raw CSV string."
        )
        self.system_prompt = self.base_prompt.replace("{eval_guide}", "Pending Phase 1 Baseline...")

    def update_eval_guide(self, eval_guide: str):
        self.system_prompt = self.base_prompt.replace("{eval_guide}", eval_guide)

    def print_agent(self, name, text, color_code="32"):
        """Simple helper to style output"""
        print(f"\033[{color_code}m\n[{name}]:\n{text}\n\033[0m")

    def generate_response(self, prompt: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": prompt})
        
        self.print_agent("Agent 4 (Classifier) -> Agent 3", prompt, "35")
        
        for iteration in range(5):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" }
            )
            
            raw_response = response.choices[0].message.content
            sanitized_response = raw_response
            try:
                dec = json.loads(raw_response)
                if dec.get("action") == "finalize":
                    sanitized_response = '{"action": "finalize", "content": "Reference: case_feedback.csv"}'
            except Exception:
                pass
                
            import csv
            with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                source = "Agent 4" if iteration == 0 else "System"
                writer.writerow([source, "Agent 3", messages[-1]["content"], sanitized_response])
            
            try:
                decision = json.loads(raw_response)
            except Exception:
                return response.choices[0].message.content
                
            action = decision.get("action")
            content = decision.get("content", "")
            
            if action == 'ask_agent_1':
                self.print_agent("Agent 3 -> Agent 1 (Interpreter)", content, "34")
                agent1_reply = self.agent1.generate_response(content)
                self.print_agent("Agent 1 (Interpreter)", agent1_reply, "32")
                
                import csv
                with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Agent 3", "Agent 1", content, agent1_reply])
                
                messages.append({"role": "assistant", "content": response.choices[0].message.content})
                messages.append({"role": "user", "content": f"Agent 1 replied: {agent1_reply}"})
                
            elif action == 'ask_agent_2':
                self.print_agent("Agent 3 -> Agent 2 (Analyzer)", content, "34")
                agent2_reply = self.agent2.generate_response(content)
                self.print_agent("Agent 2 (Analyzer)", agent2_reply, "33")
                
                import csv
                with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Agent 3", "Agent 2", content, agent2_reply])
                
                messages.append({"role": "assistant", "content": response.choices[0].message.content})
                messages.append({"role": "user", "content": f"Agent 2 replied: {agent2_reply}"})
            else:
                self.print_agent("Agent 3 -> Agent 4 (Classifier)", content, "34")
                return content
                
        self.print_agent("System", "Agent 3 reached max iterations.", "31")
        return "Max iterations reached. Partial analysis: " + content

