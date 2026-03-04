import os
import datetime
from config_loader import load_config
from agent1 import Agent1
from agent2 import Agent2
from agent3 import Agent3
from agent4 import Agent4

def load_file_content(path):
    """Attempt to load a file, return a default string if not found."""
    if not path:
        return ""
    full_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), path))
    try:
        with open(full_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️ Warning: File not found: {full_path}")
        return f"[Missing File Data: {path} - Please populate this file]"

def main():
    print("Loading configuration...")
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(config_path)
    
    api_key = config.get('openai', {}).get('api_key')
    model = config.get('openai', {}).get('model', 'gpt-4o')
    paths = config.get('paths', {})
    eval_config = config.get('evaluation', {})
    domain_name = eval_config.get('domain_name', 'unknown_domain')
    use_optional_inputs = eval_config.get('use_optional_inputs', True)
    model_type = eval_config.get('model_type', 'class diagram')
    
    if not api_key or api_key == "your-openai-api-key-here":
        print("❌ Error: Please update 'config.yaml' with your actual OpenAI API key.")
        return
        
    # Generate Output Directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    opt_inputs_str = "optInputs-True" if use_optional_inputs else "optInputs-False"
    folder_name = f"{domain_name}_{model}_{opt_inputs_str}_{timestamp}"
    output_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", folder_name))
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Initializing Framework with model: {model}")
    print(f"Using Optional Inputs (Metamodel & Suggested Diagram): {use_optional_inputs}")
    print(f"Outputs will be saved to: {output_dir}")
    
    # Load Contexts
    instructions_text = load_file_content(paths.get('instructions', 'artifacts/metamodel.txt')) if use_optional_inputs else ""
    problem_desc = load_file_content(paths.get('problem_description', 'artifacts/problem_description.txt'))
    suggested_diag = load_file_content(paths.get('suggested_diagram', 'artifacts/suggested_diagram.txt')) if use_optional_inputs else ""
    student_diag = load_file_content(paths.get('student_diagram', 'artifacts/student_diagram.txt'))
    
    # Instantiate Agents
    instruction_expert = Agent1(api_key=api_key, model=model, instructions_text=instructions_text, model_type=model_type)
    domain_expert = Agent2(api_key=api_key, model=model, problem_desc=problem_desc, suggested_diagram=suggested_diag, output_dir=output_dir, agent1=instruction_expert, model_type=model_type)
    evaluator = Agent3(api_key=api_key, model=model, agent1=instruction_expert, agent2=domain_expert, student_diagram=student_diag, output_dir=output_dir)
    classifier = Agent4(api_key=api_key, model=model, agent2=domain_expert, agent3=evaluator, output_dir=output_dir)
    
    print("\nStarting Variability Classification Orchestration (Agent 4)...")
    
    import csv
    log_path = os.path.join(output_dir, "interactions.csv")
    with open(log_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["source agent", "target agent", "request", "response"])
        
    taxonomy = classifier.process_task(max_iterations=15)
    
    tax_path = os.path.join(output_dir, "taxonomy.csv")
    with open(tax_path, "w") as f:
        f.write(taxonomy)
    
    print(f"\n[Saved] Variability Taxonomy -> {tax_path}")

if __name__ == "__main__":
    main()
