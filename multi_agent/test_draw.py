import os
from new_framework import build_graph

def main():
    print("Building LangGraph...")
    graph = build_graph()
    g = graph.get_graph()
    try:
        g.print_ascii()
    except Exception as e:
        print("print_ascii failed:", e)

if __name__ == "__main__":
    main()
