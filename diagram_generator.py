import re
import json
import sys
import os

def parse_puml(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    nodes = {}
    edges = []
    
    # 1. Classes and Enums
    block_pattern = re.compile(r'(class|enum)\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?\s*\{([^}]*)\}', re.MULTILINE)
    for match in block_pattern.finditer(content):
        type_, name, parent, body = match.groups()
        body_lines = [line.strip() for line in body.split('\n') if line.strip()]
        
        if type_ == "enum":
            label = f"&lt;&lt;enumeration&gt;&gt;\n<b>{name}</b>"
        else:
            label = f"<b>{name}</b>"
            
        if body_lines:
            label += "\n" + "-"*15 + "\n" + "\n".join(body_lines)
            
        nodes[name] = {
            "id": name,
            "label": label,
            "shape": "box",
            "font": {"multi": "html", "face": "monospace", "align": "left"}
        }
        
        if parent:
            if parent not in nodes:
                 nodes[parent] = {"id": parent, "label": f"<b>{parent}</b>", "shape": "box", "font": {"multi": "html", "face": "monospace"}}
            edges.append({
                "from": name,
                "to": parent,
                "arrows": "to",
                "dashes": False,
                "color": {"color": "gray"}
            })

    content_no_blocks = block_pattern.sub('', content)

    # 2. Associations and dependencies
    for line in content_no_blocks.split('\n'):
        line = line.strip()
        if not line or line.startswith("'") or line.startswith("@") or line.startswith("note ") or line == "end note" or line.startswith("skinparam"):
            continue
            
        # Class Association notes
        assoc_class_match = re.search(r'\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)\s*\.\.\s*([A-Za-z0-9_]+)', line)
        if assoc_class_match:
            a, b, c = assoc_class_match.groups()
            edges.append({"from": a, "to": c, "dashes": True, "color": {"color": "gray"}})
            edges.append({"from": b, "to": c, "dashes": True, "color": {"color": "gray"}})
            if c not in nodes:
                nodes[c] = {"id": c, "label": f"<b>{c}</b>", "shape": "box", "font": {"multi": "html", "face": "monospace"}}
            continue
            
        parts = line.split(':')
        rel_part = parts[0].strip()
        label_part = parts[1].strip().replace('"', '') if len(parts) > 1 else ""
        
        rel_part = rel_part.replace('"', '')
        line_types = r'--|\.\.>|<\.\.|\.\.|\*>|<*|>--|-->|<--|--<|\*--|--\*|o--|--o'
        rel_match = re.search(rf'([A-Za-z0-9_]+)\s*(.*?)({line_types})\s*(.*?)([A-Za-z0-9_]+)$', rel_part)
        
        if rel_match:
            left_node, left_card, line_type, right_card, right_node = rel_match.groups()
            
            dashes = ('..' in line_type)
            arrows = ""
            
            if '>' in line_type: arrows = "to"
            if '<' in line_type: arrows = "from"
            if '*' in line_type:
                if line_type.startswith('*'): arrows = "from"
                if line_type.endswith('*'): arrows = "to"
            if 'o' in line_type:
                if line_type.startswith('o'): arrows = "from"
                if line_type.endswith('o'): arrows = "to"
                
            lcard = left_card.strip()
            rcard = right_card.strip()
            
            edge_label = label_part
            if lcard or rcard:
                if edge_label:
                    edge_label += "\n"
                edge_label += f"{lcard} ... {rcard}"
                
            edges.append({
                "from": left_node,
                "to": right_node,
                "dashes": dashes,
                "label": edge_label,
                "arrows": arrows,
                "font": {"size": 12, "align": "middle", "multi": "html"},
                "color": {"color": "#666666"}
            })

            for n in (left_node, right_node):
                if n not in nodes:
                    nodes[n] = {"id": n, "label": f"<b>{n}</b>", "shape": "box", "font": {"multi": "html", "face": "monospace"}}

    return list(nodes.values()), edges

def generate_html(nodes, edges, output_file):
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Class Diagram</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        #mynetwork {{
            width: 100vw;
            height: 100vh;
            border: none;
        }}
        body, html {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            font-family: sans-serif;
            background-color: #f8f9fa;
        }}
        #header {{
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 10;
            background: white;
            padding: 10px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
<div id="header">
    <h3>Class Diagram</h3>
    <p>You can drag and move the nodes around.</p>
</div>
<div id="mynetwork"></div>

<script type="text/javascript">
    var nodes = new vis.DataSet({nodes_json});
    var edges = new vis.DataSet({edges_json});

    var container = document.getElementById('mynetwork');
    var data = {{
        nodes: nodes,
        edges: edges
    }};
    var options = {{
        physics: {{
            enabled: true,
            barnesHut: {{
                gravitationalConstant: -15000,
                centralGravity: 0.3,
                springLength: 200,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 0.2
            }}
        }},
        layout: {{
            randomSeed: 42
        }},
        nodes: {{
            color: {{
                background: '#ffffff',
                border: '#0056b3',
                highlight: {{
                    background: '#e6f2ff',
                    border: '#0056b3'
                }},
                hover: {{
                    background: '#e6f2ff',
                    border: '#0056b3'
                }}
            }},
            borderWidth: 2,
            shadow: true,
            fixed: false
        }},
        edges: {{
            font: {{
                align: 'middle',
                background: 'white'
            }},
            smooth: {{
                type: 'dynamic'
            }}
        }},
        interaction: {{
            hover: true,
            navigationButtons: true,
            keyboard: true,
            dragNodes: false
        }}
    }};
    var network = new vis.Network(container, data, options);
    
    // Stabilize and then disable physics to keep them completely static
    network.once("stabilizationIterationsDone", function() {{
        network.setOptions({{
            physics: false,
            nodes: {{ fixed: true }}
        }});
        network.fit();
    }});
</script>
</body>
</html>
"""
    with open(output_file, 'w') as f:
        f.write(html_template)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        input_file = "/Users/maximbragilovski/model_evalution/artifacts/Cheers-CD-final.txt"
        output_file = "/Users/maximbragilovski/model_evalution/output/class_diagram.html"
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        
    print(f"Reading from {{input_file}}...")
    nodes, edges = parse_puml(input_file)
    generate_html(nodes, edges, output_file)
    print(f"Generated successfully: {{output_file}}")
