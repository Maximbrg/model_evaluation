import os
import json
from openai import OpenAI
from agent2 import Agent2
from agent3 import Agent3

class Agent4:
    """
    Agent 4: Variability Understanding (Classifier).
    Responsibility: Functions as the main agent, which synthesizes and categorizes variability, 
    taking into consideration the Analyzer and the Reasoner outcomes.
    """
    def __init__(self, api_key: str, model: str, agent2: Agent2, agent3: Agent3, output_dir: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.agent2 = agent2
        self.agent3 = agent3
        self.log_file = os.path.join(output_dir, "interactions.csv")
        
        self.system_prompt = (
            "You are Agent 4: Variability Understanding (Classifier) & Master Orchestrator.\n\n"
            "As a Master Orchestrator, your primary objective is to synthesize and categorize variability across the analyzed models. "
            "You are responsible for managing the main evaluation loop to identify patterns, commonalities, and differences.\n\n"
            "To ensure peak precision, follow these operational directives:\n"
            "- Phase 1 Orchestration (Domain Baseline): Exclusively query Agent 2 (Analyzer) to gather information regarding domain constraints, potential errors, incompleteness, and inconsistencies.\n"
            "- Phase 2 Orchestration (Case Evaluation): Exclusively query Agent 3 (Reasoner) to analyze the case similarities and differences with respect to the domain knowledge.\n"
            "- Synthesis: Aggregate the findings from Agent 2 and Agent 3 without introducing outside or unverified data.\n"
            "- Categorization: Distinguish between substantial variability (conceptually justified) and occasional variability (errors, unintended deviations).\n\n"
            "Your final output must be delivered as a detailed Variability Taxonomy formatted as a valid CSV string (with headers: Category, Sub-Category, Finding, Evidence). Do not wrap the CSV in markdown code blocks.\n\n"
            "You must ALWAYS return your answer purely as a JSON object with these keys:\n"
            "- 'action': either 'ask_agent_2', 'ask_agent_3', 'phase_1_done', or 'finalize'.\n"
            "- 'content': The question for the respected agent, OR if 'finalize', the final detailed Variability Taxonomy formatted as a raw CSV string."
        )

    def print_agent(self, name, text, color_code="35"):
        print(f"\033[{color_code}m\n[{name}]:\n{text}\n\033[0m")

    def process_task(self, max_iterations: int = 15) -> str:
        self.print_agent("System", "Agent 4 (Classifier) starting Phase 1: Domain Baseline.", "35")
        history = []
        
        # --- PHASE 1: Domain Baseline (Agent 4 -> Agent 2) ---
        for iteration in range(4): # Max 4 interactions with Agent 2
            messages = [{"role": "system", "content": self.system_prompt}]
            
            if not history:
                 messages.append({"role": "user", "content": "PHASE 1 START: You are building the Domain Baseline. Ask Agent 2 your first question about the domain. Output 'action': 'ask_agent_2'."})
            else:
                 messages.append({"role": "user", "content": f"PHASE 1: Dialogue history so far:\n{json.dumps(history, indent=2)}\n\nWhat is your next question? (If you have enough domain context, output 'action': 'phase_1_done')"})
                 
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" }
            )
            
            raw_response = response.choices[0].message.content
            import csv
            with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["System", "Agent 4", messages[-1]["content"], raw_response])
            
            try:
                decision = json.loads(raw_response)
            except Exception:
                decision = {"action": "ask_agent_2", "content": "What are the core domain constraints?"}
                
            action = decision.get("action")
            content = decision.get("content", "")
            
            if action == 'phase_1_done':
                eval_guide = history[-1]['message'] if history else "No evaluation guidelines were generated."
                self.agent3.update_eval_guide(eval_guide)
                self.print_agent("Agent 4 (Classifier)", "Phase 1 complete - collected domain baseline constraint data.", "35")
                with open(os.path.join(os.path.dirname(self.log_file), "guidelines.csv"), "w", encoding='utf-8') as f:
                    f.write(eval_guide)
                break
                
            elif action == 'ask_agent_2':
                self.print_agent("Agent 4 -> Agent 2 (Analyzer)", content, "35")
                agent2_reply = self.agent2.generate_response(content)
                self.print_agent("Agent 2 (Analyzer)", agent2_reply, "33")
                
                import csv
                with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Agent 4", "Agent 2", content, "Reference: guidelines.csv"])
                
                history.append({"from": "Orchestrator", "to": "Agent 2", "message": content})
                history.append({"from": "Agent 2", "to": "Orchestrator", "message": agent2_reply})
            else:
                self.print_agent("Agent 4 (Classifier)", f"Warning: Action {action} not allowed during Phase 1.", "31")

        # --- PHASE 2: Case Evaluation (Agent 4 -> Agent 3) ---
        self.print_agent("System", "Agent 4 (Classifier) starting Phase 2: Case Evaluation.", "35")
        
        for iteration in range(4): # Max 4 interactions with Agent 3
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.append({"role": "user", "content": f"PHASE 2: Dialogue history so far:\n{json.dumps(history, indent=2)}\n\nYou are now evaluating the Case. Ask Agent 3 about the student's diagram against the domain baseline. (If finished, output 'action': 'finalize' and your Taxonomy)."})
            
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
                    sanitized_response = '{"action": "finalize", "content": "Reference: taxonomy.csv"}'
            except Exception:
                pass
                
            import csv
            with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["System", "Agent 4", messages[-1]["content"], sanitized_response])
            
            try:
                decision = json.loads(raw_response)
            except Exception:
                decision = {"action": "ask_agent_3", "content": "What issues exist in the diagram against the domain constraints?"}
                
            action = decision.get("action")
            content = decision.get("content", "")
            
            if action == 'finalize':
                self.print_agent("Agent 4 (Classifier) - FINAL TAXONOMY", content, "36")
                
                case_feedback = history[-1]['message'] if history and history[-1]['from'] == 'Agent 3' else "No case feedback generated."
                with open(os.path.join(os.path.dirname(self.log_file), "case_feedback.csv"), "w", encoding='utf-8') as f:
                    f.write(case_feedback)
                    
                return content
                
            elif action == 'ask_agent_3':
                self.print_agent("Agent 4 -> Agent 3 (Reasoner)", content, "35")
                agent3_reply = self.agent3.generate_response(content)
                self.print_agent("Agent 3 (Reasoner)", agent3_reply, "34")
                
                import csv
                with open(self.log_file, "a", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Agent 4", "Agent 3", content, "Reference: case_feedback.csv"])
                
                history.append({"from": "Orchestrator", "to": "Agent 3", "message": content})
                history.append({"from": "Agent 3", "to": "Orchestrator", "message": agent3_reply})
            else:
                self.print_agent("Agent 4 (Classifier)", f"Warning: Action {action} not allowed during Phase 2.", "31")
                
        self.print_agent("System", "Max iterations reached for Agent 4 Phase 2.", "31")
        return self._force_finalize(history)

    def _force_finalize(self, history: list) -> str:
        case_feedback = history[-1]['message'] if history and history[-1]['from'] == 'Agent 3' else "No case feedback generated."
        with open(os.path.join(os.path.dirname(self.log_file), "case_feedback.csv"), "w", encoding='utf-8') as f:
            f.write(case_feedback)
            
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": f"Dialogue history:\n{json.dumps(history, indent=2)}\n\nYou have reached the limit. Output 'action': 'finalize' and your final Taxonomy."})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={ "type": "json_object" }
        )
        
        raw_response = response.choices[0].message.content
        sanitized_response = raw_response
        try:
            dec = json.loads(raw_response)
            sanitized_response = '{"action": "finalize", "content": "Reference: taxonomy.csv"}'
        except Exception:
            pass
            
        import csv
        with open(self.log_file, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["System", "Agent 4", messages[-1]["content"], sanitized_response])
            
        try:
            decision = json.loads(raw_response)
            content = decision.get("content", "Failed to generate.")
            self.print_agent("Agent 4 (Classifier) - FORCED TAXONOMY", content, "36")
            return content
        except Exception:
            return "Failed to generate final taxonomy."
