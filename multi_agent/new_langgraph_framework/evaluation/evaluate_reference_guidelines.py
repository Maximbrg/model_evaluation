import argparse
import glob
import json
import logging
import os
import re
import yaml
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def normalize_text(text: str) -> str:
    """Normalizes a string for clean comparisons."""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', '', text)
    return ' '.join(text.lower().split())

def jaccard_similarity(str1: str, str2: str) -> float:
    """Calculates Jaccard similarity of words in two strings."""
    set1 = set(normalize_text(str1).split())
    set2 = set(normalize_text(str2).split())
    
    if not set1 and not set2:
        return 1.0  # Both empty
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def load_config():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def llm_semantic_mapping(client, model, canonical_templates, new_templates):
    """Uses LLM to map a list of new guidelines to existing canonical guidelines."""
    
    canonical_formatted = []
    for c_id, c in canonical_templates.items():
        canonical_formatted.append(f"ID: {c_id}\nFragment Name: {c.get('fragment_name', '')}\nFragment Type: {c.get('fragment_type', '')}\nDescription: {c.get('description', '')}")
    
    new_formatted = []
    for n in new_templates:
        n_id = n.get('id', '')
        # If the LLM didn't return an ID, give it a temporary one for mapping
        if not n_id:
            n_id = f"TEMP_{hash(n.get('description', ''))}"
            n['id'] = n_id
            
        new_formatted.append(f"ID: {n_id}\nFragment Name: {n.get('fragment_name', '')}\nFragment Type: {n.get('fragment_type', '')}\nDescription: {n.get('description', '')}")
        
    system_prompt = """You are an expert mapping agent.
You are given a list of Canonical Domain Guidelines and a list of New Domain Guidelines.
Your task is to map each New Guideline to the corresponding Canonical Guideline ONLY if their semantic descriptions represent the exact same rule or concept, regardless of naming differences. Pay attention to both Fragment Name and Description.
If a New Guideline does not closely match any Canonical Guideline, map it to "NONE".

Return your answer strictly in valid JSON format:
{
  "mappings": {
     "new_guideline_id": "canonical_guideline_id_or_NONE"
  }
}
No other text.
"""
    
    user_prompt = f"""Canonical Guidelines:
{"---".join(canonical_formatted)}

New Guidelines:
{"---".join(new_formatted)}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    content = response.choices[0].message.content
    
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()
        
    try:
        data = json.loads(content)
        return data.get("mappings", {})
    except Exception as e:
        logging.error(f"Failed to parse LLM mapping response: {e}\nResponse was:\n{content}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Evaluate multiple Reference Guidelines Semantically.")
    parser.add_argument('guideline_files', metavar='F', type=str, nargs='*', help='Path(s) to reference_guidelines.json files')
    parser.add_argument('--output', '-o', type=str, default='semantic_guideline_agreement.json', help='Path to output JSON results.')
    parser.add_argument('--config', '-c', type=str, default='eval_config.yaml', help='Path to evaluation config file.')
    
    args = parser.parse_args()
    
    template_files = args.guideline_files
    output_path = args.output
    
    # Try loading from evaluation config if files are missing
    if not template_files:
        config_path = args.config
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), args.config)
            
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                eval_cfg = yaml.safe_load(f)
                if eval_cfg:
                    if 'template_dir' in eval_cfg and eval_cfg['template_dir']:
                        target_dir = eval_cfg['template_dir']
                        if os.path.isdir(target_dir):
                            template_files = glob.glob(os.path.join(target_dir, "*.json"))
                        else:
                            logging.error(f"Template directory not found: {target_dir}")
                    else:
                        template_files = eval_cfg.get('template_files', [])
                        
                    output_path = eval_cfg.get('output', output_path)
                    
    if len(template_files) < 2:
        logging.error("At least two files are required. Pass them via arguments or 'evaluation/eval_config.yaml'.")
        return
        
    config = load_config()
    api_key = os.getenv("OPENAI_API_KEY")
    ai_model = "gpt-4o-mini"
    
    if config and "openai" in config:
        api_key = config["openai"].get("api_key", api_key)
        ai_model = config["openai"].get("model", ai_model)
        
    if not api_key:
        logging.error("OpenAI API Key not found in config.yaml or environment variable OPENAI_API_KEY.")
        return
        
    client = OpenAI(api_key=api_key)
        
    # Read files
    templates_by_file = {}
    for fp in template_files:
        if not os.path.exists(fp):
            logging.error(f"File not found: {fp}")
            continue
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            try:
                data = json.loads(content)
                guidelines = data.get("reference_guidelines", [])
                if not guidelines:
                    logging.warning(f"No 'reference_guidelines' found in {fp}. Attempting to locate array if it is the root.")
                    if isinstance(data, list):
                        guidelines = data
                templates_by_file[fp] = {
                    "language_name": data.get("language_name", "Unknown"),
                    "domain_identifier": data.get("domain_identifier", "Unknown"),
                    "guidelines": guidelines
                }
            except Exception as e:
                logging.error(f"Failed to parse JSON for {fp}: {e}")
                
    # Filter files that did not actually load any guidelines
    templates_by_file = {k: v for k, v in templates_by_file.items() if len(v["guidelines"]) > 0}
                
    if len(templates_by_file) < 2:
        logging.error("Not enough valid files containing reference_guidelines found.")
        return

    # Semantic Processing
    file_path_keys = list(templates_by_file.keys())
    
    # dict mapping canonical_id -> dict of file -> template object
    global_guidelines_map = {}
    canonical_templates = {} # For prompt generation: canonical_id -> template object
    canonical_counter = 1
    
    # Process File 1 (Base Line)
    fp1 = file_path_keys[0]
    logging.info(f"Processing baseline file: {fp1}")
    for t in templates_by_file[fp1]["guidelines"]:
        c_id = f"G{canonical_counter}"
        canonical_counter += 1
        
        # Enforce ID
        if not t.get("id"):
            t["id"] = c_id
            
        canonical_templates[c_id] = t
        global_guidelines_map[c_id] = {fp1: t}
        
    # Process subsequent files
    for fp in file_path_keys[1:]:
        logging.info(f"Semantically mapping file: {fp} against existing canonical clusters...")
        new_guidelines = templates_by_file[fp]["guidelines"]
        
        # Call LLM
        mappings = llm_semantic_mapping(client, ai_model, canonical_templates, new_guidelines)
        
        # Integrate results
        for t in new_guidelines:
            n_id = t.get("id", "")
            mapped_c_id = mappings.get(n_id, "NONE")
            
            if mapped_c_id and mapped_c_id != "NONE" and mapped_c_id in canonical_templates:
                # Add to existing cluster
                global_guidelines_map[mapped_c_id][fp] = t
            else:
                # Becomes new canonical guideline
                c_id = f"G{canonical_counter}"
                canonical_counter += 1
                if not t.get("id"):
                    t["id"] = c_id
                canonical_templates[c_id] = t
                global_guidelines_map[c_id] = {fp: t}
                
    # Calculate overlaps precisely
    perfect_overlaps = []
    partial_overlaps = []
    
    # Map file paths to their 1-based index (1, 2, 3, 4)
    file_path_to_index = {fp: i+1 for i, fp in enumerate(file_path_keys)}
    
    disjoint_keys = {f"File {file_path_to_index[fp]}: {os.path.basename(fp)}": [] for fp in file_path_keys}
    detailed_matches = {}
    num_files = len(file_path_keys)
    
    similarity_scores = []
    
    for key, appearances in global_guidelines_map.items():
        present_in_indices = [file_path_to_index[fp] for fp in appearances.keys()]
        
        match_info = {
            "canonical_id": key,
            "canonical_name": canonical_templates[key].get("fragment_name", ""),
            "canonical_type": canonical_templates[key].get("fragment_type", ""),
            "canonical_description": canonical_templates[key].get("description", ""),
            "files_present_indices": present_in_indices,
            "files_present_paths": list(appearances.keys()),
            "original_descriptions_by_file_index": {
                file_path_to_index[fp]: template.get("description", "")
                for fp, template in appearances.items()
            }
        }
        
        if len(appearances) == num_files:
            perfect_overlaps.append(match_info)
        elif len(appearances) > 1:
            partial_overlaps.append(match_info)
        else:
            for fp in appearances.keys():
                disjoint_keys[f"File {file_path_to_index[fp]}: {os.path.basename(fp)}"].append(match_info)
                
        if len(appearances) > 1:
            t_list = list(appearances.values())
            # Basic average similarity for citations (since these guidelines have citations instead of involved_fragments)
            sim_score = jaccard_similarity(
                t_list[0].get("citation", ""), 
                t_list[1].get("citation", "")
            )
            similarity_scores.append(sim_score)
            
            detailed_matches[key] = match_info
            detailed_matches[key]["citation_similarity_score"] = sim_score

    average_citation_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
    total_unique_templates = len(global_guidelines_map)
    total_overlapping_templates = len(perfect_overlaps) + len(partial_overlaps)
    template_agreement_ratio = total_overlapping_templates / total_unique_templates if total_unique_templates > 0 else 0.0

    results = {
        "metrics": {
            "total_files_compared": num_files,
            "total_unique_semantic_guidelines": total_unique_templates,
            "semantic_guidelines_in_all_files": len(perfect_overlaps),
            "semantic_guidelines_in_multiple_but_not_all": len(partial_overlaps),
            "semantic_guideline_agreement_ratio": template_agreement_ratio,
            "average_citation_jaccard_similarity": average_citation_similarity
        },
        "file_mapping": {f"File {i}": fp for fp, i in file_path_to_index.items()},
        "overlaps": {
            "present_in_all": perfect_overlaps,
            "present_in_multiple": partial_overlaps
        },
        "disjoints_by_file": disjoint_keys,
        "detailed_overlap_metrics": detailed_matches
    }
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(results, out_f, indent=2)
        
    logging.info("============= SEMANTIC EVALUATION RESULTS =============")
    logging.info(f"Compared {num_files} reference guideline files using {ai_model}.")
    logging.info(f"Total Unique Domain Guidelines identified semantically: {total_unique_templates}")
    logging.info(f"Guidelines found in ALL files: {len(perfect_overlaps)}")
    logging.info(f"Overall Semantic Agreement Ratio: {template_agreement_ratio:.2%}")
    logging.info(f"Average Citation Jaccard Similarity (for overlaps): {average_citation_similarity:.2%}")
    logging.info(f"Details saved to {output_path}")

if __name__ == "__main__":
    main()
