"""STRUCTURAL SUITE Pro | PSC Bridge Design  -  main window.
Every number shown anywhere comes from BridgeEngine.run(); this file only collects inputs."""
import sys
from PySide6.QtWidgets import (QFileDialog, QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QPushButton, QStackedWidget, QFrame, QFileDialog, QScrollArea, QGridLayout,
                               QTextEdit, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from bridge_engine import BridgeEngine, BridgeInputs, InputError, VEHICLES
from ui_analysis import AnalysisPage
from ui_results import ResultsPage
from ui_report import ReportPage
from ui_3d_model import Model3DPage

QSS = """
QMainWindow { background-color: #F0F4F8; font-family: "Segoe UI", Arial, sans-serif; }
#sidebar { background-color: #0F2546; }
#sidebar QPushButton { background: transparent; color: #A0AEC0; text-align: left; padding: 15px 25px; font-size: 13px; font-weight: bold; border: none; }
#sidebar QPushButton:hover { color: #FFFFFF; background-color: #1A365D; }
#sidebar QPushButton:checked { color: #FFFFFF; background-color: #1A365D; border-left: 4px solid #3182CE; }
QLabel#page_title { font-size: 24px; font-weight: 800; color: #1A202C; }
QLabel#page_subtitle { font-size: 13px; color: #718096; }
QLabel#card_title { font-size: 16px; font-weight: bold; color: #123B63; }
QLabel#card_subtitle { font-size: 12px; color: #718096; }
QLabel#field_label { font-size: 12px; color: #4A5568; }
QFrame#card { background-color: #FFFFFF; border-radius: 6px; border: 1px solid #E2E8F0; }
QLineEdit, QComboBox { min-height: 30px; padding: 2px 10px; border: 1px solid #CBD5E0; border-radius: 4px; background: #FFFFFF; font-size: 13px; color: #2D3748; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #3182CE; }
QTableWidget { background: white; border: 1px solid #E2E8F0; gridline-color: #EDF2F7; }
QHeaderView::section { background: #F8FAFC; color: #123B63; padding: 6px; border: none; border-bottom: 1px solid #E2E8F0; font-weight: bold; }
QPushButton#primary_btn { background-color: #10B981; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px; }
QPushButton#primary_btn:hover { background-color: #059669; }
QPushButton#nav_next { background-color: #123B63; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px; }
QPushButton#nav_back { background-color: #F1F5F9; color: #4A5568; font-weight: bold; padding: 8px 20px; border-radius: 4px; border: 1px solid #E2E8F0; }
QScrollArea { border: none; background: transparent; }
"""

# group -> [(key, label, unit, default)]   (0 / blank where noted means "derive automatically")
FIELDS = {
    "Span & deck": [
        ("L", "Effective span", "m", 33.0), ("n_girders", "Number of girders", "", 5),
        ("spacing", "Girder spacing (0 = derive from deck width)", "m", 0.0),
        ("n_lanes", "Number of traffic lanes", "", 3), ("lane_w", "Lane width", "m", 3.5),
        ("footpath_w", "Footpath width (each side)", "m", 1.5), ("barrier_w", "Crash barrier width (each side)", "m", 0.5),
        ("slab_t", "RCC deck slab thickness", "m", 0.25), ("haunch", "Haunch depth", "m", 0.05),
        ("n_diaphragms", "Number of diaphragms", "", 5), ("dia_t", "Diaphragm thickness", "m", 0.30)],
    "Girder section": [
        ("depth", "Overall girder depth", "m", 2.0), ("bt", "Top flange width", "m", 1.0),
        ("tf", "Top flange thickness", "m", 0.20), ("tw", "Web thickness", "m", 0.30),
        ("bb", "Bottom flange width", "m", 0.80), ("tb", "Bottom flange thickness", "m", 0.30)],
    "Materials": [
        ("fck", "Girder concrete fck", "MPa", 50.0), ("deck_fck", "Deck concrete fck", "MPa", 35.0),
        ("fy", "Reinforcement fy", "MPa", 500.0), ("fpk", "Strand fpk", "MPa", 1860.0),
        ("strand_area", "Area per strand", "mm²", 140.0)],
    "Prestressing": [
        ("n_cables", "Number of cables (0 = auto-size)", "", 0), ("strands_per_cable", "Max strands per cable", "", 19), ("flange_ducts", "Ducts in bottom flange (rest in web)", "", 2),
        ("duct_d", "Duct diameter", "m", 0.10), ("jack_ratio", "Jacking stress / fpk", "", 0.75),
        ("mu", "Friction coefficient μ", "", 0.17), ("k_wobble", "Wobble k", "/m", 0.0015),
        ("slip", "Anchorage draw-in", "m", 0.006), ("e_end", "Cable eccentricity at supports", "m", 0.0),
        ("creep_phi", "Creep coefficient φ", "", 1.8), ("shrinkage", "Shrinkage strain", "", 3.5e-4),
        ("relax1000", "Relaxation at 1000 h", "%", 2.5), ("transfer_ratio", "fci / fck at transfer", "", 0.75)],
    "Superimposed loads": [
        ("wc_t", "Wearing coat thickness", "m", 0.065), ("wc_gamma", "Wearing coat unit weight", "kN/m³", 22.0),
        ("barrier_wt", "Crash barrier weight (each)", "kN/m", 10.0), ("fp_ll", "Footpath live load", "kN/m²", 4.0)],
}
INT_KEYS = {"flange_ducts", "n_girders", "n_lanes", "n_diaphragms", "n_cables", "strands_per_cable"}
LOADS = ["Governing", "Class A", "Class B", "Class 70R Wheeled", "Class 70R Tracked"]


class PSCBridgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRUCTURAL SUITE Pro | PSC Bridge Design")
        self.resize(1400, 860); self.setMinimumSize(900, 600)
        self.setStyleSheet(QSS)
        self.engine = BridgeEngine()
        self.results = None
        self._cache_key = None
        self.edits = {}
        self.project = {}

        root = QWidget(); self.setCentralWidget(root)
        lay = QHBoxLayout(root); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        self.nav = []

        area = QWidget(); self.cl = QVBoxLayout(area); self.cl.setContentsMargins(25, 20, 25, 20)
        hd = QHBoxLayout(); tv = QVBoxLayout()
        self.title = QLabel(); self.title.setObjectName("page_title")
        self.sub = QLabel(); self.sub.setObjectName("page_subtitle")
        tv.addWidget(self.title); tv.addWidget(self.sub); hd.addLayout(tv); hd.addStretch()
        self.status = QLabel(""); self.status.setStyleSheet("color:#718096;font-size:12px;")
        hd.addWidget(self.status)
        self.cl.addLayout(hd)
        self.stack = QStackedWidget(); self.cl.addWidget(self.stack)
        ft = QHBoxLayout()
        self.back_btn = QPushButton("← Back"); self.back_btn.setObjectName("nav_back")
        self.next_btn = QPushButton("Next →"); self.next_btn.setObjectName("nav_next")
        self.back_btn.setMinimumWidth(230); self.next_btn.setMinimumWidth(230)
        self.back_btn.clicked.connect(lambda: self.switch_page(self.stack.currentIndex() - 1))
        self.next_btn.clicked.connect(lambda: self.switch_page(self.stack.currentIndex() + 1))
        self.save_btn = QPushButton("Save Project"); self.save_btn.setObjectName("nav_back"); self.save_btn.clicked.connect(self.save_project)
        ft.addWidget(self.back_btn); ft.addStretch(); ft.addWidget(self.save_btn); ft.addWidget(self.next_btn); self.cl.addLayout(ft)
        lay.addWidget(area)

        self.stack.addWidget(self._home_page())
        self.stack.addWidget(self._project_page())
        self.stack.addWidget(self._form_page(["Span & deck", "Girder section", "Materials", "Prestressing"], 2))
        self.stack.addWidget(self._loads_page())
        self.model_page = Model3DPage(self); self.stack.addWidget(self.model_page)
        self.analysis_page = AnalysisPage(self); self.stack.addWidget(self.analysis_page)
        self.results_page = ResultsPage(self); self.stack.addWidget(self.results_page)
        self.report_page = ReportPage(self); self.stack.addWidget(self.report_page)
        self.switch_page(0)

    # ---------- input handling ----------
    def _card(self, title, sub=""):
        c = QFrame(); c.setObjectName("card"); l = QVBoxLayout(c); l.setContentsMargins(18, 16, 18, 16)
        h = QLabel(title); h.setObjectName("card_title"); l.addWidget(h)
        if sub:
            s = QLabel(sub); s.setObjectName("card_subtitle"); l.addWidget(s)
        return c, l

    def _grid_group(self, group):
        c, l = self._card(group)
        g = QGridLayout(); g.setHorizontalSpacing(20); g.setVerticalSpacing(8)
        for i, (key, label, unit, default) in enumerate(FIELDS[group]):
            e = self.edits.get(key) or QLineEdit(f"{default:g}" if key not in INT_KEYS else str(default))
            self.edits[key] = e
            lb = QLabel(f"{label}" + (f" [{unit}]" if unit else "")); lb.setObjectName("field_label")
            box = QVBoxLayout(); box.setSpacing(2); box.addWidget(lb); box.addWidget(e)
            w = QWidget(); w.setLayout(box); box.setContentsMargins(0, 0, 0, 0)
            g.addWidget(w, i // 2, i % 2)
        l.addLayout(g); return c

    def _scroll(self, widgets):
        sc = QScrollArea(); sc.setWidgetResizable(True)
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 12, 0); l.setSpacing(14)
        for x in widgets: l.addWidget(x)
        l.addStretch(); sc.setWidget(w); return sc

    def _home_page(self):
        w = QWidget(); l = QVBoxLayout(w); l.setAlignment(Qt.AlignCenter)
        t = QLabel("STRUCTURAL SUITE Pro"); t.setStyleSheet("font-size:34px;font-weight:800;color:#123B63;"); t.setAlignment(Qt.AlignCenter)
        s2 = QLabel("PSC Bridge Design  |  IRC:6 loads  |  IRC:112 limit-state design"); s2.setStyleSheet("font-size:14px;color:#718096;"); s2.setAlignment(Qt.AlignCenter)
        new = QPushButton("＋  Start a New Project"); new.setObjectName("nav_next"); new.setMinimumSize(320, 56)
        new.setStyleSheet("font-size:16px;"); new.clicked.connect(self.new_project)
        opn = QPushButton("Open a Saved Project"); opn.setObjectName("nav_back"); opn.setMinimumSize(320, 48); opn.clicked.connect(self.open_project)
        for x in (t, s2): l.addWidget(x)
        l.addSpacing(30)
        for x in (new, opn): l.addWidget(x, alignment=Qt.AlignCenter)
        return w

    def new_project(self):
        for g in FIELDS.values():
            for key, _l, _u, df in g:
                self.edits[key].setText(str(df) if key in INT_KEYS else f"{df:g}")
        self.load_combo.setCurrentIndex(0); self.p_name.setText("New PSC Bridge Project")
        self.results = None; self._cache_key = None
        self.switch_page(1)

    def save_project(self):
        import json
        try: d = self.collect()
        except InputError as e: QMessageBox.warning(self, "Invalid input", str(e)); return
        d["_name"] = self.p_name.text(); d["_designer"] = self.p_des.text(); d["_desc"] = self.p_desc.toPlainText()
        path, _ = QFileDialog.getSaveFileName(self, "Save project", "bridge_project.json", "Project (*.json)")
        if path:
            with open(path, "w") as f: json.dump(d, f, indent=1)

    def open_project(self):
        import json
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "Project (*.json)")
        if not path: return
        try:
            d = json.load(open(path))
            for k, e in self.edits.items():
                if k in d: e.setText(str(d[k]))
            if d.get("load_class") in LOADS: self.load_combo.setCurrentText(d["load_class"])
            self.p_name.setText(d.get("_name", "")); self.p_des.setText(d.get("_designer", "")); self.p_desc.setPlainText(d.get("_desc", ""))
        except Exception as ex:
            QMessageBox.warning(self, "Cannot open", str(ex)); return
        self.results = None; self._cache_key = None
        self.switch_page(1)

    def _project_page(self):
        c, l = self._card("Project details")
        g = QGridLayout()
        self.p_name = QLineEdit("PSC I-Girder Bridge"); self.p_des = QLineEdit("Ranvir Kumar (23CE36016)")
        self.p_code = QComboBox(); self.p_code.addItems(["IRC:6-2017 / IRC:112-2011 (SP:71 as detailing reference)"])
        for i, (a, w) in enumerate([("Project name", self.p_name), ("Designer", self.p_des), ("Design code", self.p_code)]):
            g.addWidget(QLabel(a), i, 0); g.addWidget(w, i, 1)
        l.addLayout(g)
        note = QLabel("IRC:SP:71 covers pre-tensioned girders and is used here only for minimum dimensions "
                      "(top flange ≥100 mm, bottom flange ≥150 mm, web ≥150 mm). IRC:18 is withdrawn; "
                      "post-tensioned design follows IRC:112-2011. Clause references in the report are marked 'verify'.")
        note.setWordWrap(True); note.setObjectName("card_subtitle"); l.addWidget(note)
        self.p_desc = QTextEdit(); self.p_desc.setFixedHeight(80)
        self.p_desc.setPlaceholderText("Short description of the bridge / project (printed in the report)")
        self.p_desc.setPlainText("Design of a simply supported post-tensioned PSC I-girder bridge for CE60258.")
        l.addWidget(QLabel("Project description (appears in the report)")); l.addWidget(self.p_desc)
        c2 = self._grid_group("Span & deck")
        return self._scroll([c, c2])

    def _form_page(self, groups, _):
        return self._scroll([self._grid_group(g) for g in groups if g != "Span & deck"])

    def _loads_page(self):
        c, l = self._card("IRC:6 live load")
        self.load_combo = QComboBox(); self.load_combo.addItems(LOADS)
        l.addWidget(QLabel("Design vehicle ('Governing' envelopes all classes)")); l.addWidget(self.load_combo)
        c2 = self._grid_group("Superimposed loads")
        return self._scroll([c, c2])

    def meta(self):
        return dict(name=self.p_name.text(), designer=self.p_des.text(), code=self.p_code.currentText(), description=self.p_desc.toPlainText().strip())

    def collect(self):
        d = {}
        for g in FIELDS.values():
            for key, label, _u, _df in g:
                t = self.edits[key].text().strip()
                try: d[key] = int(float(t)) if key in INT_KEYS else float(t)
                except ValueError: raise InputError(f"'{label}' must be a number (got '{t}').")
        d["load_class"] = self.load_combo.currentText()
        return d

    def get_results(self, show_errors=True):
        try:
            d = self.collect()
            key = repr(sorted(d.items()))
            if key != self._cache_key or self.results is None:
                self.results = self.engine.run(d); self._cache_key = key
            self.status.setText("")
            return self.results
        except InputError as e:
            if show_errors: QMessageBox.warning(self, "Invalid input", str(e))
            self.results = None; self._cache_key = None
            self.status.setText("input error")
            return None

    def run_analysis(self):
        if self.get_results() is not None:
            for p in (self.model_page, self.analysis_page, self.results_page, self.report_page):
                p.refresh()
            self.switch_page(6)

    def switch_page(self, i):
        i = max(0, min(7, i))
        for k, b in enumerate(self.nav): b.setChecked(k == i)
        titles = ["HOME", "PROJECT", "GEOMETRY & MATERIALS", "LOADS", "3D MODEL", "ANALYSIS", "RESULTS", "REPORT"]
        subs = ["Start a new bridge project or open a saved one.", "Project information and deck layout.", "Girder section, materials and prestressing data.",
                "IRC:6 live load and superimposed loads.", "Views generated from the current inputs.",
                "Force envelopes, stresses and deflections.", "Design checks (all from the analysis engine).",
                "PDF / CSV / TXT export of the engine results."]
        self.title.setText(titles[i]); self.sub.setText(subs[i]); self.stack.setCurrentIndex(i)
        self.back_btn.setVisible(i > 0); self.save_btn.setVisible(i > 0); self.next_btn.setVisible(0 < i < len(titles) - 1)
        if i > 0: self.back_btn.setText(f"← Back: {titles[i-1].title()}")
        if i < len(titles) - 1: self.next_btn.setText(f"Next: {titles[i+1].title()} →")
        if i >= 4 and self.get_results() is not None:
            self.stack.currentWidget().refresh()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = PSCBridgeApp(); w.show()
    sys.exit(app.exec())
