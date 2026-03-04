import os

def generate_html():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # File Paths
    student_path = os.path.join(base_dir, "artifacts", "student_diagram.txt")
    suggested_path = os.path.join(base_dir, "artifacts", "suggested_diagram.txt")
    log_path = os.path.join(base_dir, "multi_agent", "error_log.txt")
    
    # Read contents
    def read_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found at {path}"
            
    student_txt = read_file(student_path)
    suggested_txt = read_file(suggested_path)
    log_txt = read_file(log_path)
    
    # Parse log_txt into an HTML list for better organization
    log_html_lines = []
    in_list = False
    for line in log_txt.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('- '):
            if not in_list:
                log_html_lines.append('<ul style="line-height: 1.6; font-size: 16px; list-style-type: none; padding-left: 0;">')
                in_list = True
            
            # Bold the prefix before the colon for readability
            content = line[2:]
            if ':' in content:
                parts = content.split(':', 1)
                content = f"<strong style='color: #2b6cb0;'>{parts[0]}:</strong>{parts[1]}"
            
            log_html_lines.append(f'<li style="margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-left: 5px solid #3182ce; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">{content}</li>')
        else:
            if in_list:
                log_html_lines.append('</ul>')
                in_list = False
            log_html_lines.append(f'<p style="font-size: 18px; margin-top: 25px; color: #2c3e50;"><strong>{line}</strong></p>')
    if in_list:
        log_html_lines.append('</ul>')
    
    log_formatted = '\n'.join(log_html_lines)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PlantUML Visualizations</title>
    <!-- Include plantuml-encoder to convert raw text to PlantUML server URLs -->
    <script src="https://cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f0f2f5; color: #333; }}
        h1, h2 {{ text-align: center; color: #2c3e50; }}
        .section {{ margin-bottom: 40px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .img-container {{ display: flex; justify-content: center; overflow-x: auto; padding: 20px 0; min-height: 200px; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #e1e4e8; border-radius: 4px; padding: 10px; background: #fff; }}
        .loading {{ color: #6c757d; font-style: italic; text-align: center; width: 100%; }}
    </style>
</head>
<body>
    <h1>Class Diagrams & Agent Feedback (PlantUML)</h1>
    
    <div class="section">
        <h2>1. Student Diagram</h2>
        <!-- Store raw text securely without browser re-formatting -->
        <script type="text/plain" id="student_raw">{student_txt}</script>
        <div class="img-container" id="student_container">
            <div class="loading">Rendering Student Diagram...</div>
        </div>
    </div>

    <div class="section">
        <h2>2. Gold Standard (Suggested Diagram)</h2>
        <script type="text/plain" id="suggested_raw">{suggested_txt}</script>
        <div class="img-container" id="suggested_container">
            <div class="loading">Rendering Suggested Diagram...</div>
        </div>
    </div>

    <div class="section">
        <h2>3. Agent Actionable Feedback & Suggestions</h2>
        {log_formatted}
    </div>

    <script>
        function renderPlantUML(rawId, containerId) {{
            const rawElement = document.getElementById(rawId);
            const container = document.getElementById(containerId);
            
            if (rawElement && rawElement.textContent.trim().length > 0) {{
                // Encode the plantuml text
                const encoded = plantumlEncoder.encode(rawElement.textContent);
                // Use the official PlantUML SVG generation server
                const url = 'https://www.plantuml.com/plantuml/svg/' + encoded;
                
                // Create and insert image
                const img = document.createElement('img');
                img.src = url;
                img.alt = "PlantUML Diagram";
                
                // Handle graphic loading event
                img.onload = function() {{
                    container.innerHTML = '';
                    container.appendChild(img);
                }};
                img.onerror = function() {{
                    container.innerHTML = '<div style="color:red;">Error loading diagram from PlantUML server. The syntax might be too large or invalid.</div>';
                }};
            }} else {{
                container.innerHTML = '<div style="color:red;">No diagram text found.</div>';
            }}
        }}

        // Render both diagrams immediately upon load
        window.onload = function() {{
            renderPlantUML('student_raw', 'student_container');
            renderPlantUML('suggested_raw', 'suggested_container');
        }};
    </script>
</body>
</html>"""

    out_path = os.path.join(base_dir, "visualizations_plantuml.html")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Success! Generated PlantUML visualization at: {out_path}")

if __name__ == "__main__":
    generate_html()
