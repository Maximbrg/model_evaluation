import os
import sys
import json

def generate_visualization(student_filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    student_path = os.path.join(base_dir, "artifacts", "student_CD", student_filename)
    
    if not os.path.exists(student_path):
        print(f"❌ Error: File not found at {student_path}")
        return

    try:
        with open(student_path, 'r', encoding='utf-8') as f:
            student_txt = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualizing Case: {student_filename}</title>
    <script src="https://cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0b10;
            --card-bg: rgba(255, 255, 255, 0.03);
            --accent: #00d2ff;
            --accent-glow: rgba(0, 210, 255, 0.3);
            --text: #e0e6ed;
            --text-dim: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }}

        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 20% 20%, rgba(0, 210, 255, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 80% 80%, rgba(147, 51, 234, 0.05) 0%, transparent 40%);
            color: var(--text);
            margin: 0;
            padding: 40px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .container {{
            max-width: 1200px;
            width: 100%;
        }}

        header {{
            text-align: left;
            margin-bottom: 40px;
            animation: fadeIn 0.8s ease-out;
        }}

        h1 {{
            font-size: 2.5rem;
            margin: 0;
            background: linear-gradient(to right, #fff, var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 600;
        }}

        .filename {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 8px;
            display: block;
        }}

        .main-card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            animation: slideUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .main-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            opacity: 0.5;
        }}

        .viz-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
        }}

        .viz-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent);
        }}

        .img-wrapper {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 400px;
            position: relative;
        }}

        img {{
            max-width: 100%;
            height: auto;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3));
            transition: transform 0.3s ease;
        }}

        .loading-shimmer {{
            font-style: italic;
            color: var(--text-dim);
            animation: pulse 1.5s infinite;
        }}

        .raw-text-section {{
            margin-top: 40px;
        }}

        .raw-header {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-dim);
        }}

        pre {{
            background: rgba(0, 0, 0, 0.3);
            padding: 24px;
            border-radius: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            border: 1px solid var(--border);
            line-height: 1.6;
            color: #cbd5e1;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes pulse {{
            0% {{ opacity: 0.4; }}
            50% {{ opacity: 0.7; }}
            100% {{ opacity: 0.4; }}
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.2); }}

    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Case Visualization</h1>
            <span class="filename">{student_filename}</span>
        </header>

        <div class="main-card">
            <div class="viz-header">
                <div class="viz-title">
                    <div class="status-dot"></div>
                    Class Diagram Rendering
                </div>
            </div>

            <div class="img-wrapper" id="viz_container">
                <div class="loading-shimmer">Engine initialising...</div>
            </div>

            <div class="raw-text-section">
                <div class="raw-header">Source Code</div>
                <pre id="raw_code">{student_txt}</pre>
            </div>
        </div>
    </div>

    <script>
        function render() {{
            const code = document.getElementById('raw_code').textContent.trim();
            const container = document.getElementById('viz_container');
            
            if (code) {{
                try {{
                    const encoded = plantumlEncoder.encode(code);
                    const url = 'https://www.plantuml.com/plantuml/svg/' + encoded;
                    
                    const img = new Image();
                    img.src = url;
                    img.onload = () => {{
                        container.innerHTML = '';
                        container.appendChild(img);
                    }};
                    img.onerror = () => {{
                        container.innerHTML = '<div style="color: #ef4444;">Syntax Error: Unable to render diagram.</div>';
                    }};
                }} catch (e) {{
                    container.innerHTML = '<div style="color: #ef4444;">Error encoding diagram.</div>';
                }}
            }}
        }}
        window.onload = render;
    </script>
</body>
</html>"""

    output_path = os.path.join(base_dir, "student_viz.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"✅ Successfully generated premium visualization at: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 visualize_student.py <student_filename>")
    else:
        generate_visualization(sys.argv[1])
