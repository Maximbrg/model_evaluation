import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import argparse
import zlib
import base64
import urllib.request
from io import BytesIO
try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

class ComplianceVisualizer:
    def __init__(self, root, models_dir=None, guidelines_dir=None, model_path=None, guidelines_path=None):
        self.root = root
        self.root.title("VEGO-AI")
        self.root.geometry("1400x850")
        
        self.models_dir = models_dir
        self.guidelines_dir = guidelines_dir
        
        self.compliance_data = []
        self.alien_data = [] # Store alien elements separately
        self.current_case_id = ""
        self.current_model_content = ""
        self.diagram_image = None
        self.original_pill_image = None
        self.zoom_level = 1.0
        self.raw_json_data = {} # Full JSON for metadata
        
        self.setup_ui()
        
        self.refresh_file_lists()
        
        # Initial selection
        if model_path:
            self.model_combo.set(os.path.basename(model_path))
        if guidelines_path:
            self.guideline_combo.set(os.path.basename(guidelines_path))
            
        if model_path or guidelines_path:
            self.on_selection_change()

    def setup_ui(self):
        # Header with Name
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        ttk.Label(header_frame, text="VEGO-AI", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        # Top bar
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(top_frame, text="Model:").pack(side=tk.LEFT, padx=(0,5))
        self.model_combo = ttk.Combobox(top_frame, width=40, state="readonly")
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)
        
        ttk.Label(top_frame, text="Guidelines:").pack(side=tk.LEFT, padx=(10,5))
        self.guideline_combo = ttk.Combobox(top_frame, width=40, state="readonly")
        self.guideline_combo.pack(side=tk.LEFT, padx=5)
        self.guideline_combo.bind("<<ComboboxSelected>>", self.on_guideline_selected)
        
        ttk.Button(top_frame, text="Refresh", command=self.refresh_file_lists).pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="Browse...", command=self.open_files).pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(top_frame, text="Ready.")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Main Layout
        self.main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pw.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left Side (Model & Diagram)
        self.left_pane = ttk.Frame(self.main_pw)
        self.main_pw.add(self.left_pane, weight=1)
        self.left_notebook = ttk.Notebook(self.left_pane)
        self.left_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Code
        self.code_tab = ttk.Frame(self.left_notebook)
        self.left_notebook.add(self.code_tab, text="Code")
        self.model_text = tk.Text(self.code_tab, wrap=tk.NONE, font=("Consolas", 11))
        vs = ttk.Scrollbar(self.code_tab, orient=tk.VERTICAL, command=self.model_text.yview)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        hs = ttk.Scrollbar(self.code_tab, orient=tk.HORIZONTAL, command=self.model_text.xview)
        hs.pack(side=tk.BOTTOM, fill=tk.X)
        self.model_text.config(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.model_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 2: Diagram
        self.diag_tab = ttk.Frame(self.left_notebook)
        self.left_notebook.add(self.diag_tab, text="Diagram")
        
        self.zoom_frame = ttk.Frame(self.diag_tab)
        self.zoom_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Button(self.zoom_frame, text="In", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.zoom_frame, text="Out", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.zoom_frame, text="1x", command=self.zoom_reset, width=3).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(self.zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=10)
        
        self.diag_canvas = tk.Canvas(self.diag_tab, background="white")
        dvs = ttk.Scrollbar(self.diag_tab, orient=tk.VERTICAL, command=self.diag_canvas.yview)
        dvs.pack(side=tk.RIGHT, fill=tk.Y)
        dhs = ttk.Scrollbar(self.diag_tab, orient=tk.HORIZONTAL, command=self.diag_canvas.xview)
        dhs.pack(side=tk.BOTTOM, fill=tk.X)
        self.diag_canvas.config(yscrollcommand=dvs.set, xscrollcommand=dhs.set)
        self.diag_canvas.pack(fill=tk.BOTH, expand=True)
        self.diag_label = ttk.Label(self.diag_canvas, background="white")
        self.diag_canvas.create_window((0,0), window=self.diag_label, anchor="nw")
        
        self.diag_canvas.bind("<Control-MouseWheel>", self.on_mousewheel)
        self.root.bind("<Command-equal>", lambda e: self.zoom_in())
        self.root.bind("<Command-minus>", lambda e: self.zoom_out())
        self.root.bind("<Command-0>", lambda e: self.zoom_reset())

        # Right Side (Guidelines)
        self.right_pw = ttk.PanedWindow(self.main_pw, orient=tk.VERTICAL)
        self.main_pw.add(self.right_pw, weight=1)
        
        # Tree
        self.list_frame = ttk.LabelFrame(self.right_pw, text="Compliance Vector")
        self.right_pw.add(self.list_frame, weight=1)
        cols = ("id", "label", "description")
        self.tree = ttk.Treeview(self.list_frame, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("label", text="Status")
        self.tree.heading("description", text="Description")
        self.tree.column("id", width=50, stretch=False)
        self.tree.column("label", width=120, stretch=False)
        ts = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        ts.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=ts.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_guideline)
        
        # Details
        self.details_frame = ttk.LabelFrame(self.right_pw, text="Details")
        self.right_pw.add(self.details_frame, weight=1)
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, font=("Arial", 11), state=tk.DISABLED)
        ds = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        ds.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=ds.set)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree.tag_configure("Satisfied", foreground="green")
        self.tree.tag_configure("Partially-Satisfied", foreground="orange")
        self.tree.tag_configure("Not-Satisfied", foreground="red")
        
        # Alien tags
        self.tree.tag_configure("Alternative", foreground="#2E7D32") # Dark green
        self.tree.tag_configure("Domain Mistake", foreground="#D32F2F") # Red
        self.tree.tag_configure("Language Mistake", foreground="#7B1FA2") # Purple
        self.tree.tag_configure("Header", font=("Arial", 10, "bold"), background="#EEEEEE")

    def refresh_file_lists(self):
        models = [f for f in os.listdir(self.models_dir) if f.endswith(('.txt', '.puml'))] if self.models_dir and os.path.exists(self.models_dir) else []
        guidelines = [f for f in os.listdir(self.guidelines_dir) if f.endswith('.json')] if self.guidelines_dir and os.path.exists(self.guidelines_dir) else []
        self.model_combo['values'] = sorted(models)
        self.guideline_combo['values'] = sorted(guidelines)
        self.status_label.config(text=f"{len(models)} models, {len(guidelines)} guidelines available.")

    def on_model_selected(self, event=None):
        m_file = self.model_combo.get()
        cid = m_file.split('_')[0]
        if f"{cid}.json" in self.guideline_combo['values']:
            self.guideline_combo.set(f"{cid}.json")
        self.on_selection_change()

    def on_guideline_selected(self, event=None):
        g_file = self.guideline_combo.get()
        cid = os.path.splitext(g_file)[0]
        for m in self.model_combo['values']:
            if m.startswith(cid):
                self.model_combo.set(m)
                break
        self.on_selection_change()

    def on_selection_change(self):
        m, g = self.model_combo.get(), self.guideline_combo.get()
        if m and g:
            self.load_data(os.path.join(self.models_dir, m), os.path.join(self.guidelines_dir, g))

    def open_files(self):
        m = filedialog.askopenfilename(title="Model")
        if not m: return
        g = filedialog.askopenfilename(title="Guidelines")
        if not g: return
        self.models_dir, self.guidelines_dir = os.path.dirname(m), os.path.dirname(g)
        self.refresh_file_lists()
        self.model_combo.set(os.path.basename(m))
        self.guideline_combo.set(os.path.basename(g))
        self.on_selection_change()

    def load_data(self, m_path, g_path):
        try:
            with open(m_path, 'r', encoding='utf-8') as f: m_content = f.read()
            with open(g_path, 'r', encoding='utf-8') as f: g_json = json.load(f)
            
            cid = os.path.splitext(os.path.basename(m_path))[0].split('_')[0]
            vector, aliens = None, []
            
            # Save raw data for global metadata viewing
            self.raw_json_data = g_json
            
            if isinstance(g_json, dict):
                vector = g_json.get("compliance_vector") or g_json.get(cid, {}).get("compliance_vector")
                aliens = g_json.get("alien_elements_evaluation") or g_json.get(cid, {}).get("alien_elements_evaluation", [])
                
                # Fallback if not nested under case_id
                if not vector and "compliance_vector" in g_json:
                    vector = g_json["compliance_vector"]
                if not aliens and "alien_elements_evaluation" in g_json:
                    aliens = g_json["alien_elements_evaluation"]
            elif isinstance(g_json, list):
                for case in g_json:
                    if str(case.get("case_id")) == cid:
                        vector = case.get("compliance_vector")
                        aliens = case.get("alien_elements_evaluation", [])
                        self.raw_json_data = case
                        break
            
            self.current_model_content = m_content
            self.model_text.delete(1.0, tk.END); self.model_text.insert(tk.END, m_content)
            self.compliance_data = vector or []
            self.alien_data = aliens or []
            self.populate_tree()
            self.status_label.config(text=f"Loaded {cid} | {len(self.compliance_data)} Gs, {len(self.alien_data)} Aliens")
            self.update_diagram()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_diagram(self):
        if not self.current_model_content.strip(): return
        try:
            url = self.get_plantuml_url(self.current_model_content)
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})) as resp:
                data = resp.read()
            if PILLOW_AVAILABLE:
                self.original_pill_image = Image.open(BytesIO(data))
                self.apply_zoom()
            else:
                self.diagram_image = tk.PhotoImage(data=data)
                self.diag_label.config(image=self.diagram_image)
                self.diag_canvas.config(scrollregion=(0, 0, self.diagram_image.width(), self.diagram_image.height()))
        except Exception as e: self.diag_label.config(text=f"Error: {e}", image="")

    def apply_zoom(self):
        if not PILLOW_AVAILABLE or not self.original_pill_image: return
        w, h = self.original_pill_image.size
        ns = (max(1, int(w*self.zoom_level)), max(1, int(h*self.zoom_level)))
        res = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC
        self.diagram_image = ImageTk.PhotoImage(self.original_pill_image.resize(ns, res))
        self.diag_label.config(image=self.diagram_image)
        self.diag_canvas.config(scrollregion=(0, 0, ns[0], ns[1]))
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def zoom_in(self): self.zoom_level = min(5.0, self.zoom_level*1.2); self.apply_zoom()
    def zoom_out(self): self.zoom_level = max(0.1, self.zoom_level/1.2); self.apply_zoom()
    def zoom_reset(self): self.zoom_level = 1.0; self.apply_zoom()
    def on_mousewheel(self, e): (self.zoom_in() if e.delta > 0 else self.zoom_out()); return "break"

    def get_plantuml_url(self, text):
        c = zlib.compress(text.encode('utf-8'), 9)[2:-4]
        res = ""
        for i in range(0, len(c), 3):
            chunk = c[i:i+3]
            b1 = chunk[0]
            b2 = chunk[1] if len(chunk) > 1 else 0
            b3 = chunk[2] if len(chunk) > 2 else 0
            c1, c2, c3, c4 = b1>>2, ((b1&3)<<4)|(b2>>4), ((b2&15)<<2)|(b3>>6), b3&63
            for x in [c1, c2, c3, c4]: res += self._e(x & 63)
        return f"http://www.plantuml.com/plantuml/png/{res}"

    def _e(self, b):
        if b < 10: return chr(48+b)
        b -= 10
        if b < 26: return chr(65+b)
        b -= 26
        if b < 26: return chr(97+b)
        b -= 26
        return '-' if b == 0 else ('_' if b == 1 else '?')

    def populate_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        # Section: Guidelines
        self.tree.insert("", tk.END, iid="h_g", values=("---", "COMPLIANCE", "GUIDELINES ---"), tags=("Header",))
        for idx, g in enumerate(self.compliance_data):
            self.tree.insert("", tk.END, iid=f"g_{idx}", values=(g.get("guideline_id",""), g.get("label",""), g.get("description","")), tags=(g.get("label",""),))
            
        # Section: Alien Elements
        if self.alien_data:
            self.tree.insert("", tk.END, iid="h_a", values=("---", "ALIEN", "ELEMENTS ---"), tags=("Header",))
            for idx, ae in enumerate(self.alien_data):
                # Use element snippet as ID for display if possible, or just index
                element_name = ae.get("element", "").split('\n')[0][:30] + "..."
                self.tree.insert("", tk.END, iid=f"a_{idx}", values=("Alien", ae.get("label",""), element_name), tags=(ae.get("label",""),))

    def on_select_guideline(self, e):
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        if iid.startswith("h_"):
            d = "GLOBAL CASE METADATA\n====================\n\n"
            for k, v in self.raw_json_data.items():
                if k not in ["compliance_vector", "alien_elements_evaluation"]:
                    d += f"{k.upper()}:\n{json.dumps(v, indent=2) if isinstance(v, (dict, list)) else v}\n\n"
            self.details_text.insert(tk.END, d)
            self.details_text.config(state=tk.DISABLED)
            return

        if iid.startswith("g_"):
            item = self.compliance_data[int(iid.split("_")[1])]
            title = f"GUIDELINE {item.get('guideline_id', '???')}"
        elif iid.startswith("a_"):
            item = self.alien_data[int(iid.split("_")[1])]
            title = "ALIEN ELEMENT EVALUATION"
        else:
            return

        d = f"{title}\n{'='*len(title)}\n\n"
        
        # Display main fields first if they exist
        priority_fields = ["label", "compliance_status", "description", "reason", "justification", "notes", "matched_via", "matched_as"]
        seen_keys = set()
        
        for k in priority_fields:
            if k in item and item[k]:
                label = k.replace('_', ' ').upper()
                d += f"{label}:\n{item[k]}\n\n"
                seen_keys.add(k)
        
        # Display everything else except fragments which we handle specially
        skip_keys = seen_keys | {"guideline_id", "id", "case_id", "fragments", "new_fragments", "candidate_fragments", "suggested_alternatives", "element"}
        
        for k, v in item.items():
            if k not in skip_keys and v is not None and v != "":
                label = k.replace('_', ' ').upper()
                d += f"{label}:\n{json.dumps(v, indent=2) if isinstance(v, (dict, list)) else v}\n\n"
        
        # Handle fragments and lists specially
        list_fields = [("FRAGMENTS", "fragments"), ("NEW FRAGMENTS", "new_fragments"), 
                       ("CANDIDATE FRAGMENTS", "candidate_fragments"), ("SUGGESTED ALTERNATIVES", "suggested_alternatives")]
        
        for label, k in list_fields:
            if k in item and item[k]:
                d += f"{label}:\n"
                for entry in item[k]:
                    d += f"  • {entry}\n"
                d += "\n"
        
        # For Aliens, ensure element is shown
        if "element" in item:
            d += f"ELEMENT:\n{item['element']}\n\n"

        self.details_text.insert(tk.END, d)
        self.details_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="visualize_config.yaml")
    p.add_argument("--models_dir")
    p.add_argument("--guidelines_dir")
    args = p.parse_args()
    md, gd = args.models_dir, args.guidelines_dir
    cp = args.config
    if not os.path.isabs(cp):
        if not os.path.exists(cp):
            sd = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(os.path.join(sd, cp)): cp = os.path.join(sd, cp)
    if os.path.exists(cp):
        with open(cp, 'r', encoding='utf-8') as f:
            for l in f:
                if ':' in l:
                    k, v = [x.strip().strip('"').strip("'") for x in l.split(':', 1)]
                    if k == 'models_dir' and not md: md = v
                    elif k == 'guidelines_dir' and not gd: gd = v
    tk_root = tk.Tk()
    ComplianceVisualizer(tk_root, models_dir=md, guidelines_dir=gd)
    tk_root.mainloop()
