import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import argparse
import zlib
import urllib.request
from io import BytesIO
try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class ComplianceVisualizer:
    def __init__(self, root, models_dir=None, guidelines_dir=None, model_path=None, guidelines_path=None, **kwargs):
        self.root = root
        self.root.title("VEGO-AI")
        self.root.geometry("1400x850")
        # Force light-mode appearance regardless of macOS dark mode
        style = ttk.Style()
        style.theme_use("clam")


        self.models_dir = models_dir
        self.guidelines_dir = guidelines_dir  # kept for legacy Browse mode
        self.aggregate_dir = kwargs.get('aggregate_dir', None)

        self.compliance_data = []    # list of display items for the tree
        self.uncovered_data = []     # uncovered fragments (alien elements)
        self.current_case_id = ""
        self.current_model_content = ""
        self.diagram_image = None
        self.original_pill_image = None
        self.zoom_level = 1.0
        self.raw_json_data = {}      # full JSON for metadata panel
        self.reference_guidelines_map = {} # map of guideline ID -> reference details

        self._load_all_reference_guidelines()

        self.setup_ui()
        self.refresh_file_lists()

        # initial selection (legacy CLI args)
        if model_path:
            self.model_combo.set(os.path.basename(model_path))
        if guidelines_path:
            # try to find it in the aggregate list instead
            base = os.path.basename(guidelines_path)
            if base in self.aggregate_combo['values']:
                self.aggregate_combo.set(base)
                self.on_aggregate_selected()

    def _load_all_reference_guidelines(self):
        """Pre-load all reference guidelines from guidelines_dir (or a specific file)."""
        self.reference_guidelines_map.clear()
        if not self.guidelines_dir or not os.path.exists(self.guidelines_dir):
            return

        def _load_file(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if "reference_guidelines" in data:
                        for rg in data["reference_guidelines"]:
                            gid = rg.get("id")
                            if gid:
                                self.reference_guidelines_map[gid] = rg
            except Exception:
                pass

        if os.path.isfile(self.guidelines_dir):
            if self.guidelines_dir.endswith('.json'):
                _load_file(self.guidelines_dir)
            return

        for root, _, files in os.walk(self.guidelines_dir):
            for f in files:
                if f.endswith('.json'):
                    _load_file(os.path.join(root, f))

    # ──────────────────────────────────────────────
    # UI CONSTRUCTION
    # ──────────────────────────────────────────────
    def setup_ui(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=(8, 0))
        ttk.Label(header_frame, text="VEGO-AI", font=("Arial", 20, "bold")).pack(side=tk.LEFT)

        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Model:", font=("Arial", 13)).pack(side=tk.LEFT, padx=(0, 5))
        self.model_combo = ttk.Combobox(top_frame, width=38, state="readonly", font=("Arial", 12))
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)

        ttk.Label(top_frame, text="Aggregate:", font=("Arial", 13)).pack(side=tk.LEFT, padx=(10, 5))
        self.aggregate_combo = ttk.Combobox(top_frame, width=38, state="readonly", font=("Arial", 12))
        self.aggregate_combo.pack(side=tk.LEFT, padx=5)
        self.aggregate_combo.bind("<<ComboboxSelected>>", self.on_aggregate_selected)

        ttk.Button(top_frame, text="Refresh",          command=self.refresh_file_lists).pack(side=tk.LEFT, padx=(10,2))
        ttk.Button(top_frame, text="Browse Models…",   command=self.browse_models).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Browse Vectors…",  command=self.browse_vectors).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Browse Guide(s)…", command=self.browse_guidelines_dir).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(top_frame, text="Ready.", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT, padx=10)

        # ── Main paned layout ──────────────────────
        self.main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pw.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Code + Diagram notebook
        left_pane = ttk.Frame(self.main_pw)
        self.main_pw.add(left_pane, weight=1)
        self.left_notebook = ttk.Notebook(left_pane)
        self.left_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Code
        self.code_tab = ttk.Frame(self.left_notebook)
        self.left_notebook.add(self.code_tab, text="Code")
        self.model_text = tk.Text(self.code_tab, wrap=tk.NONE, font=("Menlo", 13),
                                   background="white", foreground="black",
                                   insertbackground="black", padx=6, pady=4)
        vs = ttk.Scrollbar(self.code_tab, orient=tk.VERTICAL, command=self.model_text.yview)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        hs = ttk.Scrollbar(self.code_tab, orient=tk.HORIZONTAL, command=self.model_text.xview)
        hs.pack(side=tk.BOTTOM, fill=tk.X)
        self.model_text.config(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.model_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 2: Diagram
        self.diag_tab = ttk.Frame(self.left_notebook)
        self.left_notebook.add(self.diag_tab, text="Diagram")

        zoom_frame = ttk.Frame(self.diag_tab)
        zoom_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Button(zoom_frame, text="In",  command=self.zoom_in,    width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="Out", command=self.zoom_out,   width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="1x",  command=self.zoom_reset, width=3).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=10)

        self.diag_canvas = tk.Canvas(self.diag_tab, background="white")
        dvs = ttk.Scrollbar(self.diag_tab, orient=tk.VERTICAL,   command=self.diag_canvas.yview)
        dvs.pack(side=tk.RIGHT, fill=tk.Y)
        dhs = ttk.Scrollbar(self.diag_tab, orient=tk.HORIZONTAL, command=self.diag_canvas.xview)
        dhs.pack(side=tk.BOTTOM, fill=tk.X)
        self.diag_canvas.config(yscrollcommand=dvs.set, xscrollcommand=dhs.set)
        self.diag_canvas.pack(fill=tk.BOTH, expand=True)
        self.diag_label = ttk.Label(self.diag_canvas, background="white")
        self.diag_canvas.create_window((0, 0), window=self.diag_label, anchor="nw")

        self.diag_canvas.bind("<Control-MouseWheel>", self.on_mousewheel)
        self.root.bind("<Command-equal>", lambda e: self.zoom_in())
        self.root.bind("<Command-minus>", lambda e: self.zoom_out())
        self.root.bind("<Command-0>",     lambda e: self.zoom_reset())

        # Right: Compliance tree + Details
        right_pw = ttk.PanedWindow(self.main_pw, orient=tk.VERTICAL)
        self.main_pw.add(right_pw, weight=1)

        list_frame = ttk.LabelFrame(right_pw, text="Compliance Vector")
        right_pw.add(list_frame, weight=1)
        cols = ("id", "status", "guideline", "evidence")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", style="Custom.Treeview")
        style = ttk.Style()
        style.configure("Custom.Treeview", font=("Arial", 12), rowheight=26)
        style.configure("Custom.Treeview.Heading", font=("Arial", 13, "bold"))
        self.tree.heading("id",          text="ID")
        self.tree.heading("status",      text="Status")
        self.tree.heading("guideline",   text="Guideline Desc")
        self.tree.heading("evidence",    text="Evidence / Fragment")
        self.tree.column("id",        width=65,  stretch=False)
        self.tree.column("status",    width=150, stretch=False)
        self.tree.column("guideline", width=250, stretch=True)
        self.tree.column("evidence",  width=250, stretch=True)
        ts = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        ts.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=ts.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_item)

        details_frame = ttk.LabelFrame(right_pw, text="Details")
        right_pw.add(details_frame, weight=1)
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, font=("Arial", 13), state=tk.DISABLED,
                                    background="white", foreground="black",
                                    insertbackground="black", padx=8, pady=6,
                                    spacing1=2, spacing3=4)
        ds = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        ds.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=ds.set)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tree colour tags
        self.tree.tag_configure("Satisfied",         foreground="green")
        self.tree.tag_configure("Partially-Satisfied", foreground="orange")
        self.tree.tag_configure("Not-Satisfied",     foreground="red")
        self.tree.tag_configure("Alternative",       foreground="#2E7D32")
        self.tree.tag_configure("Domain Mistake",    foreground="#D32F2F")
        self.tree.tag_configure("Language Mistake",  foreground="#7B1FA2")
        self.tree.tag_configure("Header", font=("Arial", 10, "bold"), background="#EEEEEE")

    # ──────────────────────────────────────────────
    # FILE LIST MANAGEMENT
    # ──────────────────────────────────────────────
    def refresh_file_lists(self):
        models = (
            [f for f in os.listdir(self.models_dir) if f.endswith(('.txt', '.puml'))]
            if self.models_dir and os.path.exists(self.models_dir) else []
        )
        aggregates = (
            [f for f in os.listdir(self.aggregate_dir) if f.endswith('.json')]
            if self.aggregate_dir and os.path.exists(self.aggregate_dir) else []
        )
        self.model_combo['values']     = sorted(models)
        self.aggregate_combo['values'] = sorted(aggregates)
        msg = f"{len(models)} models, {len(aggregates)} aggregate files available."
        self.status_label.config(text=msg)

    # ──────────────────────────────────────────────
    # EVENT HANDLERS
    # ──────────────────────────────────────────────
    def on_model_selected(self, event=None):
        """User manually picks a model → load whatever aggregate is already selected."""
        agg = self.aggregate_combo.get()
        if agg and self.aggregate_dir:
            self._load_aggregate_file(
                os.path.join(self.aggregate_dir, agg),
                model_override=os.path.join(self.models_dir, self.model_combo.get())
            )

    def on_aggregate_selected(self, event=None):
        agg_file = self.aggregate_combo.get()
        if not agg_file or not self.aggregate_dir:
            return
        agg_path = os.path.join(self.aggregate_dir, agg_file)

        # peek at case_id to auto-select matching model
        try:
            with open(agg_path, 'r', encoding='utf-8') as f:
                peek = json.load(f)
            cid = str(peek.get("case_id", ""))
        except Exception:
            cid = ""

        model_path = None
        if cid and self.models_dir and os.path.exists(self.models_dir):
            for mf in os.listdir(self.models_dir):
                if cid in mf:
                    model_path = os.path.join(self.models_dir, mf)
                    self.model_combo.set(mf)
                    break

        self._load_aggregate_file(agg_path, model_override=model_path)

    def on_selection_change(self):
        """Legacy path when no aggregate is in play."""
        m = self.model_combo.get()
        agg = self.aggregate_combo.get()
        if agg and self.aggregate_dir:
            self.on_aggregate_selected()
        elif m and self.guidelines_dir:
            g_path = os.path.join(self.guidelines_dir, m)
            if os.path.exists(g_path):
                self._load_legacy_guidelines(
                    os.path.join(self.models_dir, m) if self.models_dir else None,
                    g_path
                )

    def browse_models(self):
        """Pick the folder that contains model .txt / .puml files."""
        folder = filedialog.askdirectory(title="Select Models Folder")
        if not folder:
            return
        self.models_dir = folder
        self.refresh_file_lists()

    def browse_vectors(self):
        """Pick the folder that contains compliance-vector JSON files."""
        folder = filedialog.askdirectory(title="Select Compliance Vectors Folder")
        if not folder:
            return
        self.aggregate_dir = folder
        self.refresh_file_lists()

    def browse_guidelines_dir(self):
        """Pick a JSON file or folder containing reference guidelines."""
        path = filedialog.askopenfilename(title="Select Reference Guidelines File (JSON)", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if not path:
            return
        self.guidelines_dir = path
        self._load_all_reference_guidelines()
        
        msg = f"Loaded {len(self.reference_guidelines_map)} guidelines from {os.path.basename(self.guidelines_dir)}."
        self.status_label.config(text=msg)
        
        # Refresh tree to display newly loaded guideline descriptions
        self._populate_tree()
        self.on_select_item()

    def open_files(self):
        """Legacy: pick individual files via file dialog."""
        m = filedialog.askopenfilename(title="Select Model (.txt / .puml)")
        if not m:
            return
        g = filedialog.askopenfilename(title="Select Aggregate / Guidelines (.json)")
        if not g:
            return
        self.models_dir = os.path.dirname(m)
        # decide whether this is an aggregate file
        try:
            with open(g, 'r', encoding='utf-8') as f:
                sample = json.load(f)
            is_aggregate = "existing_mapping" in sample or "compliance_contributions" in sample
        except Exception:
            is_aggregate = False

        if is_aggregate:
            self.aggregate_dir = os.path.dirname(g)
        else:
            self.guidelines_dir = os.path.dirname(g)
        self.refresh_file_lists()
        self.model_combo.set(os.path.basename(m))
        agg_name = os.path.basename(g)
        if agg_name in self.aggregate_combo['values']:
            self.aggregate_combo.set(agg_name)
            self._load_aggregate_file(g, model_override=m)
        else:
            self._load_legacy_guidelines(m, g)

    # ──────────────────────────────────────────────
    # AGGREGATE JSON LOADING  (new format)
    # ──────────────────────────────────────────────
    def _load_aggregate_file(self, agg_path, model_override=None):
        try:
            with open(agg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.raw_json_data = data
            cid = str(data.get("case_id", os.path.splitext(os.path.basename(agg_path))[0]))

            # ── load model text ──────────────────────
            m_content = ""
            if model_override and os.path.exists(model_override):
                with open(model_override, 'r', encoding='utf-8') as f:
                    m_content = f.read()

            self.current_model_content = m_content
            self.model_text.delete(1.0, tk.END)
            self.model_text.insert(tk.END, m_content)

            # ── build compliance_data from existing_mapping ──
            existing   = data.get("existing_mapping", [])
            potential  = data.get("potential_found", [])
            contrib    = {e["guideline_id"]: e for e in data.get("compliance_contributions", []) if "guideline_id" in e}

            # merge potential into existing by guideline_id (fill gaps)
            existing_ids = {e.get("guideline_id") for e in existing}
            for p in potential:
                if p.get("guideline_id") not in existing_ids:
                    existing.append(p)

            self.compliance_data = []
            for entry in existing:
                gid    = entry.get("guideline_id", "")
                status = entry.get("compliance_status", "")
                ev     = entry.get("evidence", entry.get("notes", ""))
                score  = contrib.get(gid, {}).get("score", "")
                self.compliance_data.append({
                    "guideline_id": gid,
                    "label":        status,          # drives tree colour tag
                    "evidence":     ev,
                    "notes":        entry.get("notes", ""),
                    "score":        score,
                    "description":  ev[:80] if ev else "",
                })

            # ── uncovered fragments (alien-like) ────
            self.uncovered_data = data.get("uncovered_fragments", [])

            self._populate_tree()
            n_g = len(self.compliance_data)
            n_u = len(self.uncovered_data)
            score_pct = data.get("score_pct", "")
            score_str = f" | Score: {score_pct}%" if score_pct != "" else ""
            self.status_label.config(text=f"Loaded case {cid} | {n_g} guidelines, {n_u} fragments{score_str}")
            self.update_diagram()

        except Exception as e:
            messagebox.showerror("Error loading aggregate file", str(e))

    # ──────────────────────────────────────────────
    # LEGACY GUIDELINES LOADING  (old compliance_vector format)
    # ──────────────────────────────────────────────
    def _load_legacy_guidelines(self, m_path, g_path):
        try:
            m_content = ""
            if m_path and os.path.exists(m_path):
                with open(m_path, 'r', encoding='utf-8') as f:
                    m_content = f.read()
            with open(g_path, 'r', encoding='utf-8') as f:
                g_json = json.load(f)
            self.raw_json_data = g_json

            cid = ""
            if m_path:
                cid = os.path.splitext(os.path.basename(m_path))[0].split('_')[0]
            elif isinstance(g_json, dict) and "case_id" in g_json:
                cid = str(g_json["case_id"])

            vector, aliens = None, []
            if isinstance(g_json, dict):
                vector = g_json.get("compliance_vector") or g_json.get(cid, {}).get("compliance_vector")
                aliens = g_json.get("alien_elements_evaluation") or g_json.get(cid, {}).get("alien_elements_evaluation", [])
            elif isinstance(g_json, list):
                for case in g_json:
                    if str(case.get("case_id")) == cid:
                        vector = case.get("compliance_vector")
                        aliens = case.get("alien_elements_evaluation", [])
                        self.raw_json_data = case
                        break

            self.current_model_content = m_content
            self.model_text.delete(1.0, tk.END)
            self.model_text.insert(tk.END, m_content)
            self.compliance_data = vector or []
            self.uncovered_data  = aliens or []
            self._populate_tree()
            self.status_label.config(text=f"Loaded {cid} | {len(self.compliance_data)} Gs, {len(self.uncovered_data)} Aliens")
            self.update_diagram()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────────
    # DIAGRAM
    # ──────────────────────────────────────────────
    def update_diagram(self):
        # clear previous image
        self.diag_label.config(image="", text="")
        if not self.current_model_content.strip():
            self.diag_label.config(text="No model loaded.")
            return
        try:
            url = self._plantuml_url(self.current_model_content)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
            if PILLOW_AVAILABLE:
                self.original_pill_image = Image.open(BytesIO(raw))
                self.apply_zoom()
            else:
                self.diagram_image = tk.PhotoImage(data=raw)
                self.diag_label.config(image=self.diagram_image)
                self.diag_canvas.config(
                    scrollregion=(0, 0, self.diagram_image.width(), self.diagram_image.height())
                )
        except Exception as e:
            self.diag_label.config(text=f"Diagram error: {e}", image="")

    def apply_zoom(self):
        if not PILLOW_AVAILABLE or not self.original_pill_image:
            return
        w, h = self.original_pill_image.size
        nw, nh = max(1, int(w * self.zoom_level)), max(1, int(h * self.zoom_level))
        res = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC
        self.diagram_image = ImageTk.PhotoImage(self.original_pill_image.resize((nw, nh), res))
        self.diag_label.config(image=self.diagram_image)
        self.diag_canvas.config(scrollregion=(0, 0, nw, nh))
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")

    def zoom_in(self):    self.zoom_level = min(5.0, self.zoom_level * 1.2);  self.apply_zoom()
    def zoom_out(self):   self.zoom_level = max(0.1, self.zoom_level / 1.2);  self.apply_zoom()
    def zoom_reset(self): self.zoom_level = 1.0;                               self.apply_zoom()
    def on_mousewheel(self, e): (self.zoom_in() if e.delta > 0 else self.zoom_out()); return "break"

    def _plantuml_url(self, text):
        c = zlib.compress(text.encode('utf-8'), 9)[2:-4]
        res = ""
        for i in range(0, len(c), 3):
            chunk = c[i:i+3]
            b1 = chunk[0]
            b2 = chunk[1] if len(chunk) > 1 else 0
            b3 = chunk[2] if len(chunk) > 2 else 0
            c1, c2, c3, c4 = b1 >> 2, ((b1 & 3) << 4) | (b2 >> 4), ((b2 & 15) << 2) | (b3 >> 6), b3 & 63
            for x in [c1, c2, c3, c4]:
                res += self._e(x & 63)
        return f"http://www.plantuml.com/plantuml/png/{res}"

    def _e(self, b):
        if b < 10: return chr(48 + b)
        b -= 10
        if b < 26: return chr(65 + b)
        b -= 26
        if b < 26: return chr(97 + b)
        b -= 26
        return '-' if b == 0 else ('_' if b == 1 else '?')

    # ──────────────────────────────────────────────
    # TREE POPULATION
    # ──────────────────────────────────────────────
    def _populate_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Section: guidelines / compliance
        self.tree.insert("", tk.END, iid="h_g",
                         values=("---", "COMPLIANCE", "GUIDELINES ---", ""), tags=("Header",))
        for idx, g in enumerate(self.compliance_data):
            gid    = g.get("guideline_id", "")
            status = g.get("label", g.get("compliance_status", ""))
            
            ref = self.reference_guidelines_map.get(gid, {})
            guide_desc = (ref.get("description") or ref.get("guideline_name") or "")[:120]
            ev = (g.get("evidence") or g.get("notes") or g.get("description", ""))[:90]
            
            self.tree.insert("", tk.END, iid=f"g_{idx}",
                             values=(gid, status, guide_desc, ev), tags=(status,))

        # Section: uncovered fragments (shown below guidelines)
        if self.uncovered_data:
            for idx, uf in enumerate(self.uncovered_data):
                lbl   = uf.get("label", "")
                snip  = uf.get("fragment", "")[:80]
                self.tree.insert("", tk.END, iid=f"u_{idx}",
                                 values=("Frag", lbl, "", snip), tags=(lbl,))

        # Summary row always at the very bottom
        self.tree.insert("", tk.END, iid="h_summary",
                         values=("📊", "SUMMARY", "Click to view case score & assessment", ""), tags=("Header",))

    # ──────────────────────────────────────────────
    # DETAILS PANEL
    # ──────────────────────────────────────────────
    def on_select_item(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]

        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)

        if iid == "h_summary" or iid.startswith("h_"):
            # show case summary: score + overall assessment first, then other meta
            d = "CASE SUMMARY\n============\n\n"
            priority = ["case_id", "skill_version", "total_score", "max_score", "score_pct", "overall_assessment"]
            shown = set()
            for k in priority:
                if k in self.raw_json_data:
                    v = self.raw_json_data[k]
                    d += f"{k.upper().replace('_',' ')}:\n{v}\n\n"
                    shown.add(k)
            skip = {"existing_mapping", "potential_found", "uncovered_fragments",
                    "compliance_contributions", "fragment_contributions",
                    "compliance_vector", "alien_elements_evaluation"}
            for k, v in self.raw_json_data.items():
                if k not in skip and k not in shown:
                    d += f"{k.upper().replace('_',' ')}:\n"
                    d += f"{json.dumps(v, indent=2) if isinstance(v, (dict, list)) else v}\n\n"
            self.details_text.insert(tk.END, d)

        elif iid.startswith("g_"):
            item = self.compliance_data[int(iid.split("_")[1])]
            gid  = item.get("guideline_id", "???")
            d = f"GUIDELINE {gid}\n{'=' * (12 + len(gid))}\n\n"
            
            if gid in self.reference_guidelines_map:
                ref = self.reference_guidelines_map[gid]
                if ref.get("guideline_name"):
                    d += f"NAME:\n{ref.get('guideline_name')}\n\n"
                if ref.get("description"):
                    d += f"DESCRIPTION:\n{ref.get('description')}\n\n"

            d += f"STATUS:\n{item.get('label', item.get('compliance_status', ''))}\n\n"
            ev = item.get("evidence", "")
            if ev:
                d += f"EVIDENCE:\n{ev}\n\n"
            notes = item.get("notes", "")
            if notes:
                d += f"NOTES:\n{notes}\n\n"
            score = item.get("score", "")
            if score != "":
                d += f"SCORE: {score}\n\n"
            # any remaining keys
            shown = {"guideline_id", "label", "compliance_status", "evidence", "notes", "score", "description"}
            for k, v in item.items():
                if k not in shown and v not in (None, "", []):
                    d += f"{k.upper().replace('_',' ')}:\n{json.dumps(v, indent=2) if isinstance(v, (dict, list)) else v}\n\n"
            self.details_text.insert(tk.END, d)

        elif iid.startswith("u_"):
            item = self.uncovered_data[int(iid.split("_")[1])]
            d = "UNCOVERED FRAGMENT\n==================\n\n"
            d += f"LABEL: {item.get('label', '')}\n"
            sev = item.get("severity", "")
            if sev:
                d += f"SEVERITY: {sev}\n"
            d += f"\nFRAGMENT:\n{item.get('fragment', '')}\n\n"
            reason = item.get("reason", "")
            if reason:
                d += f"REASON:\n{reason}\n"
            self.details_text.insert(tk.END, d)

        self.details_text.config(state=tk.DISABLED)


# ──────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="visualize_config.yaml")
    p.add_argument("--models_dir")
    p.add_argument("--guidelines_dir")
    p.add_argument("--aggregate_dir")
    args = p.parse_args()

    md, gd, ad = args.models_dir, args.guidelines_dir, args.aggregate_dir
    cp = args.config
    if not os.path.isabs(cp) and not os.path.exists(cp):
        sd = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(sd, cp)):
            cp = os.path.join(sd, cp)

    if os.path.exists(cp):
        with open(cp, 'r', encoding='utf-8') as f:
            for line in f:
                if ':' in line:
                    k, v = [x.strip().strip('"').strip("'") for x in line.split(':', 1)]
                    if k == 'models_dir'    and not md: md = v
                    elif k == 'guidelines_dir' and not gd: gd = v
                    elif k == 'aggregate_dir'  and not ad: ad = v

    tk_root = tk.Tk()
    ComplianceVisualizer(tk_root, models_dir=md, guidelines_dir=gd, aggregate_dir=ad)
    tk_root.mainloop()
