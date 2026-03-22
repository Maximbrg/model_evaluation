import os
from graph2 import build_graph

def generate_graph_visualization():
    print("Building Graph Architecture...")
    compiled_graph = build_graph()
    
    # Define output path
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "langgraph_visualization.png"))
    
    print(f"Generating Visualization...")
    # Get the graph layout in Mermaid PNG format
    image_bytes = compiled_graph.get_graph().draw_mermaid_png()
    
    with open(output_path, "wb") as f:
        f.write(image_bytes)
        
    print(f"✅ Success! Graph Visualization saved to: {output_path}")

if __name__ == "__main__":
    generate_graph_visualization()
