import json
import csv
import os
from collections import Counter

def generate_summary_csv(json_path, output_csv_path):
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # All possible labels we might find
    all_labels = set()
    cases_summary = []

    for case in data:
        case_id = case.get('case_id', 'Unknown')
        counts = Counter()

        # Count labels in compliance_vector
        compliance_vector = case.get('compliance_vector', [])
        for item in compliance_vector:
            label = item.get('label')
            if label:
                counts[label] += 1
                all_labels.add(label)

        # Count labels in alien_elements_evaluation
        alien_elements = case.get('alien_elements_evaluation', [])
        for item in alien_elements:
            label = item.get('label')
            if label:
                counts[label] += 1
                all_labels.add(label)

        cases_summary.append({
            'case_id': case_id,
            'counts': counts
        })

    # Sort labels for consistent column order
    sorted_labels = sorted(list(all_labels))
    fieldnames = ['case_id'] + sorted_labels

    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for summary in cases_summary:
            row = {'case_id': summary['case_id']}
            for label in sorted_labels:
                row[label] = summary['counts'].get(label, 0)
            writer.writerow(row)

    print(f"Summary CSV generated at {output_csv_path}")

if __name__ == "__main__":
    json_file = "/Users/maximbragilovski/model_evalution/multi_agent/new_langgraph_framework/outputs/2026-03-18_14-32-35/stage3_agent3_compliance/final_compliance_vector.json"
    output_file = "/Users/maximbragilovski/model_evalution/multi_agent/new_langgraph_framework/outputs/summary_report.csv"
    generate_summary_csv(json_file, output_file)
