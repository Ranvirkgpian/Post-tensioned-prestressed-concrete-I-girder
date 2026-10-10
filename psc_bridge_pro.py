import sys
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, 
                               QStackedWidget, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar, QFileDialog, QScrollArea, QCheckBox, 
                               QGridLayout, QTextEdit, QDateEdit, QTabWidget, QSizePolicy)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

# =====================================================================
# STYLESHEET (Professional Engineering Theme)
# =====================================================================
QSS = """
QMainWindow {
    background-color: #F0F4F8;
    font-family: "Segoe UI", Arial, sans-serif;
}
/* --- Sidebar --- */
#sidebar {
    background-color: #0F2546;
}
#sidebar QPushButton {
    background-color: transparent;
    color: #A0AEC0;
    text-align: left;
    padding: 15px 25px;
    font-size: 13px;
    font-weight: bold;
    border: none;
}
#sidebar QPushButton:hover {
    color: #FFFFFF;
    background-color: #1A365D;
}
#sidebar QPushButton:checked {
    color: #FFFFFF;
    background-color: #1A365D;
    border-left: 4px solid #3182CE;
}
/* --- Headers --- */
QLabel#page_title { font-size: 24px; font-weight: 800; color: #1A202C; text-transform: uppercase;}
QLabel#page_subtitle { font-size: 13px; color: #718096; margin-bottom: 10px;}
QLabel#card_title { font-size: 16px; font-weight: bold; color: #123B63; }
QLabel#card_subtitle { font-size: 12px; color: #718096; }
QLabel#field_label { font-size: 12px; font-weight: 500; color: #4A5568; }
QLabel#req_star { color: #E53E3E; }
/* --- Cards --- */
.QFrame#card {
    background-color: #FFFFFF;
    border-radius: 6px;
    border: 1px solid #E2E8F0;
}
/* --- Inputs --- */
QLineEdit, QComboBox, QDateEdit {
    min-height: 36px;
    padding: 4px 12px;
    border: 1px solid #CBD5E0;
    border-radius: 4px;
    background-color: #FFFFFF;
    font-size: 13px;
    color: #2D3748;
}
QTextEdit {
    min-height: 60px;
    padding: 8px 12px;
    border: 1px solid #CBD5E0;
    border-radius: 4px;
    background-color: #FFFFFF;
    font-size: 13px;
    color: #2D3748;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus { 
    border: 1px solid #3182CE; 
}
QComboBox::drop-down { border: none; }
/* --- Tables --- */
QTableWidget {
    background-color: white;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    gridline-color: #EDF2F7;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #123B63;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    font-weight: bold;
    font-size: 12px;
}
/* --- Buttons --- */
QPushButton#primary_btn {
    background-color: #10B981;
    color: white;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 4px;
}
QPushButton#primary_btn:hover { background-color: #059669; }
QPushButton#nav_next {
    background-color: #123B63;
    color: white;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 4px;
}
QPushButton#nav_next:hover { background-color: #1A365D; }
QPushButton#nav_back {
    background-color: #F1F5F9;
    color: #A0AEC0;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 4px;
    border: 1px solid #E2E8F0;
}
/* --- Toolbar & Viewport Styling --- */
QPushButton#toolbar_btn {
    background: #FFFFFF; border: 1px solid #E2E8F0; color: #4A5568; font-weight: 600; padding: 8px 15px; border-radius: 4px;
}
QPushButton#toolbar_btn:hover { background: #F8FAFC; }
QPushButton#toolbar_btn_active {
    background: #3182CE; border: 1px solid #3182CE; color: #FFFFFF; font-weight: 600; padding: 8px 15px; border-radius: 4px;
}
QLabel#success_box {
    background: #DEF7EC; color: #03543F; padding: 15px; border-radius: 6px; border: 1px solid #84E1BC;
}
QLabel#prop_label { color: #4A5568; font-size: 13px; }
QLabel#prop_val { color: #1A202C; font-size: 13px; font-weight: bold; }
/* --- Tabs --- */
QTabWidget::pane { border: 1px solid #E2E8F0; border-radius: 4px; background: white;}
QTabBar::tab {
    background: white; border: 1px solid #E2E8F0; padding: 8px 20px; color: #123B63; font-weight: 600; font-size: 12px;
}
QTabBar::tab:selected {
    background: #F8FAFC; border-bottom-color: #F8FAFC; color: #3182CE;
}
QScrollArea { border: none; background-color: transparent; }
"""

# =====================================================================
# CORE ENGINEERING ENGINE (Preserved Logic)
# =====================================================================
class BridgeEngine:
    def __init__(self):
        self.results = {}

    def analyze(self, L, num_girders, f_ck, load_class):
        girder_spacing = (3 * 3.5 + 3.0 + 1.0) / num_girders
        area_girder, h, y_b, I_val, e, b_w = 0.85, 2.0, 1.0, 0.35, 0.85, 0.30
        Z_b = I_val / y_b
        
        w_total_dl = (area_girder * 25) + (0.250 * girder_spacing * 25) + (0.065 * girder_spacing * 22)
        max_moment_dl = (w_total_dl * (L ** 2)) / 8
        v_dl = (w_total_dl * L) / 2

        if load_class in ["Class A", "Class B"]: impact = round(min(4.5 / (6.0 + L), 0.50), 4)
        elif load_class == "Class 70R Tracked": impact = 0.25 if L <= 40.0 else 0.10
        elif load_class == "Class 70R Wheeled": impact = 0.25 if L <= 12.0 else 0.154
        else: impact = 0.15

        axle_loads = np.array([27, 27, 114, 114, 68, 68, 68, 68])
        axle_positions = np.array([0, 1.1, 4.3, 5.5, 9.8, 12.8, 15.8, 18.8])
        max_moment, max_shear = 0.0, 0.0
        
        for pos in np.arange(0, L + axle_positions[-1], 0.1):
            curr_pos = pos - axle_positions
            on_bridge = (curr_pos >= 0) & (curr_pos <= L)
            act_loads, act_pos = axle_loads[on_bridge], curr_pos[on_bridge]
            if len(act_loads) == 0: continue
            
            m_sum = sum([p * (0.5 * x if x <= L / 2 else 0.5 * (L - x)) for p, x in zip(act_loads, act_pos)])
            s_sum = sum([p * (L - x) / L for p, x in zip(act_loads, act_pos)])
            max_moment, max_shear = max(max_moment, m_sum), max(max_shear, s_sum)
                
        exact_ll_moment = round((max_moment * 0.65), 2)
        exact_ll_shear = round((max_shear * 0.65), 2)
        
        ll_moment_impact = exact_ll_moment * (1 + impact)
        v_ll_impact = exact_ll_shear * (1 + impact)
        uls_moment = (1.35 * max_moment_dl) + (1.5 * ll_moment_impact)
        v_uls = (1.35 * v_dl) + (1.5 * v_ll_impact)

        p_jack_initial = ((max_moment_dl + ll_moment_impact) / Z_b) / ((1 / area_girder) + (e / Z_b)) / 0.80
        f_c = max((p_jack_initial / area_girder) + (p_jack_initial * (e ** 2) / I_val) - (max_moment_dl * e / I_val), 0)
        A_s = p_jack_initial / 1.2e6
        
        loss_es = (0.5 * (200e6/35e6) * f_c) * A_s
        loss_creep = (1.6 * (200e6/35e6) * f_c) * A_s
        loss_shrink = (2.0e-4 * 200e6) * A_s
        loss_relax, loss_frict = 0.025 * p_jack_initial, 0.03 * p_jack_initial
        total_loss = loss_es + loss_creep + loss_shrink + loss_relax + loss_frict
        p_eff = p_jack_initial - total_loss

        f_t, f_cp = 0.24 * np.sqrt(f_ck) * 1000, p_eff / area_girder
        v_co = 0.67 * b_w * h * np.sqrt((f_t ** 2) + (0.8 * f_cp * f_t))
        v_req = max(0, v_uls - v_co)
        s_v = (0.87 * 500 * 157.08 * ((h*1000)-100)) / (v_req * 1000) if v_req > 0 else 999
        practical_spacing = int(min(s_v, (0.87 * 500 * 157.08) / (0.4 * b_w * 1000), 0.75 * ((h*1000)-100), 300) // 25 * 25)

        self.results = {
            "L": L, "num_girders": num_girders, "spacing": girder_spacing, "f_ck": f_ck, "load_class": load_class,
            "w_dl": w_total_dl, "m_dl": max_moment_dl, "v_dl": v_dl,
            "m_ll": exact_ll_moment, "v_ll": exact_ll_shear, "impact": impact,
            "m_ll_imp": ll_moment_impact, "v_ll_imp": v_ll_impact,
            "m_uls": uls_moment, "v_uls": v_uls,
            "p_jack": p_jack_initial, "total_loss": total_loss, "loss_pct": (total_loss/p_jack_initial)*100, "p_eff": p_eff,
            "v_co": v_co, "v_req": v_req, "stirrup_spacing": practical_spacing
        }
        return self.results

# =====================================================================
# MAIN GUI APPLICATION
# =====================================================================
class PSCBridgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRUCTURAL SUITE Pro | PSC Bridge Design")
        self.setGeometry(50, 50, 1400, 900)
        self.setStyleSheet(QSS)
        
        self.engine = BridgeEngine()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. SIDEBAR
        # ==========================================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 25, 0, 15)
        sidebar_layout.setSpacing(5)
        
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🧠") 
        logo_icon.setStyleSheet("font-size: 28px; background: #0A192F; padding: 10px; border-radius: 8px; margin-left: 15px;")
        
        logo_text = QLabel("STRUCTURAL\nSUITE Pro\nBridge Design")
        logo_text.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)
        sidebar_layout.addSpacing(30)

        self.nav_btns = []
        nav_items = [
            ("📄", "01   PROJECT"), 
            ("📐", "02   GEOMETRY"), 
            ("⚖️", "03   LOADS"), 
            ("🖥️", "04   3D MODEL"), 
            ("📊", "05   ANALYSIS"), 
            ("📋", "06   RESULTS"), 
            ("📑", "07   REPORT")
        ]
        
        for idx, (icon, text) in enumerate(nav_items):
            btn = QPushButton(f"{icon}    {text}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            self.nav_btns.append(btn)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # ==========================================
        # 2. MAIN CONTENT AREA
        # ==========================================
        content_area = QWidget()
        self.content_layout = QVBoxLayout(content_area)
        self.content_layout.setContentsMargins(30, 25, 30, 25)
        
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        self.title_lbl = QLabel("PROJECT")
        self.title_lbl.setObjectName("page_title")
        self.subtitle_lbl = QLabel("Define project information and general details.")
        self.subtitle_lbl.setObjectName("page_subtitle")
        
        title_vbox.addWidget(self.title_lbl)
        title_vbox.addWidget(self.subtitle_lbl)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        
        analyze_btn = QPushButton("▶ RUN ANALYSIS")
        analyze_btn.setObjectName("primary_btn")
        analyze_btn.clicked.connect(self.run_analysis)
        header_layout.addWidget(analyze_btn)
        
        self.content_layout.addLayout(header_layout)
        self.content_layout.addSpacing(10)
        
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)
        
        self.build_pages()
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)
        self.switch_page(0)

    # --- BULLETPROOF UI HELPERS ---
    def create_field(self, label_text, widget, is_required=False):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        lbl_layout = QHBoxLayout()
        lbl_layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        lbl.setObjectName("field_label")
        lbl_layout.addWidget(lbl)
        
        if is_required:
            star = QLabel("*")
            star.setObjectName("req_star")
            lbl_layout.addWidget(star)
        lbl_layout.addStretch()
        
        layout.addLayout(lbl_layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(widget)
        return container

    def create_inline_field(self, label_text, widget, unit=""):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label_text)
        lbl.setObjectName("field_label")
        lbl.setFixedWidth(130)
        layout.addWidget(lbl)
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(widget)
        
        if unit:
            u_lbl = QLabel(unit)
            u_lbl.setObjectName("field_label")
            layout.addWidget(u_lbl)
        return container

    def create_prop_row(self, label, value):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setObjectName("prop_label")
        val = QLabel(value)
        val.setObjectName("prop_val")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(lbl)
        row.addWidget(val)
        return row

    # ==========================================
    # BUILD PAGES
    # ==========================================
    def build_pages(self):
        # ------------------------------------------
        # PAGE 0: PROJECT
        # ------------------------------------------
        p0_scroll = QScrollArea()
        p0_scroll.setWidgetResizable(True)
        p0 = QWidget()
        l0 = QVBoxLayout(p0)
        l0.setContentsMargins(0, 0, 15, 0)
        l0.setSpacing(15)

        c1 = QFrame(); c1.setObjectName("card")
        cl1 = QVBoxLayout(c1)
        cl1.setContentsMargins(20, 20, 20, 20)
        
        header1 = QLabel("📄 Project Details")
        header1.setObjectName("card_title")
        cl1.addWidget(header1)
        cl1.addSpacing(10)
        
        grid = QGridLayout()
        grid.setSpacing(20)
        
        name_in = QLineEdit("33 m PSC I-Girder Bridge")
        id_in = QLineEdit(); id_in.setPlaceholderText("e.g. BR-001")
        grid.addWidget(self.create_field("Project Name", name_in, True), 0, 0)
        grid.addWidget(self.create_field("Project ID (Optional)", id_in), 0, 1)
        
        designer_in = QLineEdit("Structural Engineer")
        client_in = QLineEdit(); client_in.setPlaceholderText("e.g. NHAI / State PWD")
        grid.addWidget(self.create_field("Designer", designer_in, True), 1, 0)
        grid.addWidget(self.create_field("Client (Optional)", client_in), 1, 1)
        
        code_in = QComboBox()
        code_in.addItems(["IRC:6-2017, IRC:18-2000", "AASHTO LRFD", "Eurocode 2"])
        date_in = QDateEdit()
        date_in.setDate(QDate.currentDate())
        date_in.setCalendarPopup(True)
        
        grid.addWidget(self.create_field("Design Code", code_in, True), 2, 0)
        grid.addWidget(self.create_field("Date", date_in), 2, 1)
        
        cl1.addLayout(grid)
        cl1.addSpacing(10)
        
        desc_in = QTextEdit("Design and analysis of a 33 m PSC I-Girder Bridge.")
        cl1.addWidget(self.create_field("Project Description (Optional)", desc_in))
        l0.addWidget(c1)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)
        
        c2 = QFrame(); c2.setObjectName("card")
        cl2 = QVBoxLayout(c2)
        cl2.setContentsMargins(20, 20, 20, 20)
        cl2.setSpacing(12)
        
        header2 = QLabel("🏢 Project Summary")
        header2.setObjectName("card_title")
        sub2 = QLabel("Key parameters for the bridge model.")
        sub2.setObjectName("card_subtitle")
        cl2.addWidget(header2)
        cl2.addWidget(sub2)
        cl2.addSpacing(15)
        
        type_in = QComboBox(); type_in.addItems(["PSC I-Girder Bridge", "Box Girder", "T-Beam"])
        self.in_span = QLineEdit("33.00")
        self.in_girders = QLineEdit("4")
        self.in_fck = QComboBox(); self.in_fck.addItems(["M40", "M45", "M50", "M55", "M60"])
        self.in_fck.setCurrentText("M50")
        self.in_load = QComboBox(); self.in_load.addItems(["Class 70R Wheeled", "Class 70R Tracked", "Class A", "Class B"])
        
        cl2.addWidget(self.create_inline_field("Bridge Type", type_in))
        cl2.addWidget(self.create_inline_field("Span Length", self.in_span, "m"))
        cl2.addWidget(self.create_inline_field("Number of Girders", self.in_girders))
        cl2.addWidget(self.create_inline_field("Concrete Grade", self.in_fck))
        cl2.addWidget(self.create_inline_field("Loading Class", self.in_load))
        cl2.addStretch()
        
        c3 = QFrame(); c3.setObjectName("card")
        cl3 = QVBoxLayout(c3)
        cl3.setContentsMargins(10, 10, 10, 10)
        
        tabs = QTabWidget()
        tab1 = QLabel("Schematic Side Elevation\n(Placeholder Graphic)")
        tab1.setAlignment(Qt.AlignCenter)
        tab1.setStyleSheet("background: #F8FAFC; color: #A0AEC0; font-size: 16px; border: 1px dashed #CBD5E0;")
        tab2 = QLabel("Schematic Cross Section")
        tab2.setAlignment(Qt.AlignCenter)
        tab2.setStyleSheet("background: #F8FAFC; color: #A0AEC0; font-size: 16px; border: 1px dashed #CBD5E0;")
        
        tabs.addTab(tab1, "Side Elevation")
        tabs.addTab(tab2, "Cross Section")
        cl3.addWidget(tabs)
        
        split_layout.addWidget(c2, 1) 
        split_layout.addWidget(c3, 2) 
        l0.addLayout(split_layout)

        footer0 = QHBoxLayout()
        back_btn0 = QPushButton("← Back"); back_btn0.setObjectName("nav_back"); back_btn0.setEnabled(False)
        next_btn0 = QPushButton("Next: Geometry →"); next_btn0.setObjectName("nav_next")
        next_btn0.clicked.connect(lambda: self.switch_page(1))
        footer0.addWidget(back_btn0); footer0.addStretch(); footer0.addWidget(next_btn0)
        l0.addSpacing(10); l0.addLayout(footer0)

        p0_scroll.setWidget(p0)
        self.stack.addWidget(p0_scroll)

        # ------------------------------------------
        # PAGE 1: GEOMETRY & MATERIALS
        # ------------------------------------------
        p1_scroll = QScrollArea()
        p1_scroll.setWidgetResizable(True)
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        l1.setContentsMargins(0, 0, 15, 0)
        l1.setSpacing(15)

        cg1 = QFrame(); cg1.setObjectName("card")
        cl_g1 = QVBoxLayout(cg1)
        cl_g1.setContentsMargins(20, 20, 20, 20)
        
        hg1 = QLabel("📐 Global Geometry Specifications")
        hg1.setObjectName("card_title")
        cl_g1.addWidget(hg1)
        cl_g1.addSpacing(10)
        
        grid_g = QGridLayout()
        grid_g.setSpacing(20)
        
        self.in_span_geom = QLineEdit("33.00")
        self.in_girders_geom = QLineEdit("4")
        self.in_spacing_geom = QLineEdit("3.62")
        self.in_depth_geom = QLineEdit("2.00")
        
        grid_g.addWidget(self.create_field("Effective Span Length (m)", self.in_span_geom), 0, 0)
        grid_g.addWidget(self.create_field("Number of Longitudinal Girders", self.in_girders_geom), 0, 1)
        grid_g.addWidget(self.create_field("Girder Spacing (m)", self.in_spacing_geom), 1, 0)
        grid_g.addWidget(self.create_field("Overall Girder Depth (m)", self.in_depth_geom), 1, 1)
        
        cl_g1.addLayout(grid_g)
        l1.addWidget(cg1)

        cg2 = QFrame(); cg2.setObjectName("card")
        cl_g2 = QVBoxLayout(cg2)
        cl_g2.setContentsMargins(20, 20, 20, 20)
        
        hg2 = QLabel("🧪 Detailed Material Grades")
        hg2.setObjectName("card_title")
        cl_g2.addWidget(hg2)
        cl_g2.addSpacing(10)
        
        grid_m = QGridLayout()
        grid_m.setSpacing(20)
        
        self.in_fck_geom = QComboBox(); self.in_fck_geom.addItems(["M40", "M45", "M50", "M55", "M60"]); self.in_fck_geom.setCurrentText("M50")
        self.in_steel = QComboBox(); self.in_steel.addItems(["Fe500 (TMT)", "Fe415", "Fe550"])
        self.in_tendon = QComboBox(); self.in_tendon.addItems(["Low Relaxation 1860 MPa Strands", "Stress Relieved Strands"])
        
        grid_m.addWidget(self.create_field("Concrete Characteristic Strength (fck)", self.in_fck_geom), 0, 0)
        grid_m.addWidget(self.create_field("Reinforcement Steel Grade", self.in_steel), 0, 1)
        grid_m.addWidget(self.create_field("Prestressing Tendon Type", self.in_tendon), 1, 0)
        
        cl_g2.addLayout(grid_m)
        l1.addWidget(cg2)

        footer1 = QHBoxLayout()
        back_btn1 = QPushButton("← Back to Project"); back_btn1.setObjectName("nav_back")
        back_btn1.clicked.connect(lambda: self.switch_page(0))
        next_btn1 = QPushButton("Next: Loads →"); next_btn1.setObjectName("nav_next")
        next_btn1.clicked.connect(lambda: self.switch_page(2))
        footer1.addWidget(back_btn1); footer1.addStretch(); footer1.addWidget(next_btn1)
        l1.addSpacing(10); l1.addLayout(footer1)

        p1_scroll.setWidget(p1)
        self.stack.addWidget(p1_scroll)

        # ------------------------------------------
        # PAGE 2: LOADS
        # ------------------------------------------
        p2_scroll = QScrollArea()
        p2_scroll.setWidgetResizable(True)
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        l2.setContentsMargins(0, 0, 15, 0)
        l2.setSpacing(15)

        cload1 = QFrame(); cload1.setObjectName("card")
        cl_l1 = QVBoxLayout(cload1)
        cl_l1.setContentsMargins(20, 20, 20, 20)
        
        h_l1 = QLabel("🚚 IRC Live Load Specifications (IRC:6-2017)")
        h_l1.setObjectName("card_title")
        cl_l1.addWidget(h_l1)
        cl_l1.addSpacing(10)
        
        grid_l = QGridLayout()
        grid_l.setSpacing(20)
        
        self.in_load_class_loads = QComboBox()
        self.in_load_class_loads.addItems(["Class 70R Wheeled", "Class 70R Tracked", "Class A", "Class B"])
        self.in_load_class_loads.setCurrentText("Class 70R Wheeled")
        self.in_lanes = QLineEdit("3")
        
        grid_l.addWidget(self.create_field("Design Vehicle / Loading Class", self.in_load_class_loads), 0, 0)
        grid_l.addWidget(self.create_field("Number of Design Lanes", self.in_lanes), 0, 1)
        
        cl_l1.addLayout(grid_l)
        l2.addWidget(cload1)

        cload2 = QFrame(); cload2.setObjectName("card")
        cl_l2 = QVBoxLayout(cload2)
        cl_l2.setContentsMargins(20, 20, 20, 20)
        
        h_l2 = QLabel("📋 Active Structural Load Cases")
        h_l2.setObjectName("card_title")
        sub_l2 = QLabel("Summary of dead, live, and environmental actions applied to girders.")
        sub_l2.setObjectName("card_subtitle")
        cl_l2.addWidget(h_l2)
        cl_l2.addWidget(sub_l2)
        cl_l2.addSpacing(15)
        
        load_table = QTableWidget(4, 5)
        load_table.setHorizontalHeaderLabels(["Case ID", "Description", "Category", "Magnitude / Type", "Status"])
        load_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        load_table.setFixedHeight(180)
        
        loads_data = [
            ("DL-01", "Girder Self Weight + Deck Slab", "Permanent (Dead)", "Calculated (Auto)", "Active ✓"),
            ("SIDL-02", "Wearing Coat & Crash Barriers", "Permanent (SIDL)", "22.0 kN/m³", "Active ✓"),
            ("LL-03", "IRC Moving Vehicular Train", "Transient (Live)", "Per IRC:6 Specification", "Active ✓"),
            ("IMP-04", "Dynamic Impact Allowance", "Transient (Impact)", "Calculated via Span L", "Active ✓")
        ]
        
        for row_idx, row_data in enumerate(loads_data):
            for col_idx, text in enumerate(row_data):
                load_table.setItem(row_idx, col_idx, QTableWidgetItem(text))
                
        cl_l2.addWidget(load_table)
        l2.addWidget(cload2)

        footer2 = QHBoxLayout()
        back_btn2 = QPushButton("← Back to Geometry"); back_btn2.setObjectName("nav_back")
        back_btn2.clicked.connect(lambda: self.switch_page(1))
        next_btn2 = QPushButton("Next: 3D Model →"); next_btn2.setObjectName("nav_next")
        next_btn2.clicked.connect(lambda: self.switch_page(3))
        footer2.addWidget(back_btn2); footer2.addStretch(); footer2.addWidget(next_btn2)
        l2.addSpacing(10); l2.addLayout(footer2)

        p2_scroll.setWidget(p2)
        self.stack.addWidget(p2_scroll)

        # ------------------------------------------
        # PAGE 3: 3D MODEL (Mockup Replication)
        # ------------------------------------------
        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        l3.setContentsMargins(0, 0, 15, 0)
        l3.setSpacing(15)

        # Main CAD Viewport Split
        cad_split = QHBoxLayout()
        cad_split.setSpacing(15)

        # --- LEFT PANEL (Viewport) ---
        viewport_layout = QVBoxLayout()
        viewport_layout.setSpacing(10)
        
        # Toolbar
        v_toolbar = QHBoxLayout()
        v_toolbar.setSpacing(10)
        
        # We store these buttons in a dictionary so we can highlight the active one
        self.view_btns = {}
        
        b_3d = QPushButton("3D VIEW"); b_3d.setObjectName("toolbar_btn_active")
        b_top = QPushButton("⌖ TOP"); b_top.setObjectName("toolbar_btn")
        b_front = QPushButton("⚄ FRONT"); b_front.setObjectName("toolbar_btn")
        b_side = QPushButton("⧉ SIDE"); b_side.setObjectName("toolbar_btn")
        b_cross = QPushButton("◩ CROSS SECTION"); b_cross.setObjectName("toolbar_btn")
        
        self.view_btns['3D'] = b_3d
        self.view_btns['TOP'] = b_top
        self.view_btns['FRONT'] = b_front
        self.view_btns['SIDE'] = b_side
        
        b_3d.clicked.connect(lambda: self.set_view("3D", 30, 45))
        b_top.clicked.connect(lambda: self.set_view("TOP", 90, -90))
        b_front.clicked.connect(lambda: self.set_view("FRONT", 0, -90))
        b_side.clicked.connect(lambda: self.set_view("SIDE", 0, 0))
        b_cross.clicked.connect(lambda: self.set_view("FRONT", 0, -90)) # Same as front for wireframe

        v_toolbar.addWidget(b_3d); v_toolbar.addWidget(b_top); v_toolbar.addWidget(b_front)
        v_toolbar.addWidget(b_side); v_toolbar.addWidget(b_cross)
        
        v_toolbar.addStretch()
        
        b_fit = QPushButton("⛶ FIT MODEL"); b_fit.setObjectName("toolbar_btn")
        v_toolbar.addWidget(b_fit)

        viewport_layout.addLayout(v_toolbar)
        
        # Matplotlib Canvas Frame
        canvas_frame = QFrame()
        canvas_frame.setObjectName("card")
        canvas_frame.setStyleSheet("background-color: #F8FAFC;") # Blend with plot
        cl_canvas = QVBoxLayout(canvas_frame)
        cl_canvas.setContentsMargins(0, 0, 0, 0)
        
        self.fig3d = Figure(figsize=(8, 5), facecolor='#F8FAFC')
        self.canvas3d = FigureCanvas(self.fig3d)
        cl_canvas.addWidget(self.canvas3d)
        
        # Status Bar inside canvas
        status_bar = QLabel("  ✅  Model generated   |   Ready for analysis")
        status_bar.setStyleSheet("background-color: #DEF7EC; color: #03543F; font-size: 12px; font-weight: bold; padding: 10px; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;")
        cl_canvas.addWidget(status_bar)
        
        viewport_layout.addWidget(canvas_frame)

        # --- RIGHT PANEL (Sidebar Cards) ---
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)
        
        # 1. Properties
        c_prop = QFrame(); c_prop.setObjectName("card"); c_prop.setFixedWidth(280)
        cl_prop = QVBoxLayout(c_prop)
        h_prop = QLabel("📋 MODEL PROPERTIES"); h_prop.setObjectName("card_title"); h_prop.setStyleSheet("font-size: 13px;")
        cl_prop.addWidget(h_prop)
        cl_prop.addSpacing(10)
        
        self.lbl_v_span = QLabel("33.00 m")
        self.lbl_v_gird = QLabel("4")
        self.lbl_v_spac = QLabel("3.62 m")
        self.lbl_v_dep = QLabel("2.00 m")
        self.lbl_v_wid = QLabel("12.00 m")
        self.lbl_v_conc = QLabel("M50")
        
        cl_prop.addLayout(self.create_prop_row("Span Length, L", self.lbl_v_span))
        cl_prop.addLayout(self.create_prop_row("Longitudinal Girders", self.lbl_v_gird))
        cl_prop.addLayout(self.create_prop_row("Girder Spacing", self.lbl_v_spac))
        cl_prop.addLayout(self.create_prop_row("Overall Girder Depth", self.lbl_v_dep))
        cl_prop.addLayout(self.create_prop_row("Deck Width", self.lbl_v_wid))
        cl_prop.addLayout(self.create_prop_row("Concrete Grade", self.lbl_v_conc))
        sidebar_layout.addWidget(c_prop)
        
        # 2. Components
        c_comp = QFrame(); c_comp.setObjectName("card"); c_comp.setFixedWidth(280)
        cl_comp = QVBoxLayout(c_comp)
        h_comp = QLabel("🏗️ MODEL COMPONENTS"); h_comp.setObjectName("card_title"); h_comp.setStyleSheet("font-size: 13px;")
        cl_comp.addWidget(h_comp)
        cl_comp.addSpacing(10)
        
        cb_deck = QCheckBox("Deck Slab"); cb_deck.setChecked(True)
        cb_gird = QCheckBox("PSC I-Girders (G1 - G4)"); cb_gird.setChecked(True)
        cb_diap = QCheckBox("Cross Diaphragms"); cb_diap.setChecked(True)
        cb_bear = QCheckBox("Bearings"); cb_bear.setChecked(True)
        cb_abut = QCheckBox("Abutments / Supports"); cb_abut.setChecked(True)
        
        cl_comp.addWidget(cb_deck); cl_comp.addWidget(cb_gird); cl_comp.addWidget(cb_diap)
        cl_comp.addWidget(cb_bear); cl_comp.addWidget(cb_abut)
        sidebar_layout.addWidget(c_comp)
        
        # 3. Status
        c_stat = QFrame(); c_stat.setObjectName("card"); c_stat.setFixedWidth(280)
        cl_stat = QVBoxLayout(c_stat)
        h_stat = QLabel("🛡️ MODEL STATUS"); h_stat.setObjectName("card_title"); h_stat.setStyleSheet("font-size: 13px;")
        cl_stat.addWidget(h_stat)
        cl_stat.addSpacing(5)
        
        status_box = QLabel("✅ Geometry generated\n3D model is ready for analysis.")
        status_box.setObjectName("success_box")
        cl_stat.addWidget(status_box)
        sidebar_layout.addWidget(c_stat)
        
        sidebar_layout.addStretch()
        
        # Combine Left & Right
        cad_split.addLayout(viewport_layout, 7) # 70% width
        cad_split.addLayout(sidebar_layout, 3) # 30% width
        
        l3.addLayout(cad_split)

        # Footer Navigation
        footer3 = QHBoxLayout()
        back_btn3 = QPushButton("← Back to Loads"); back_btn3.setObjectName("nav_back")
        back_btn3.clicked.connect(lambda: self.switch_page(2))
        next_btn3 = QPushButton("Next: Analysis →"); next_btn3.setObjectName("nav_next")
        next_btn3.clicked.connect(lambda: self.switch_page(4))
        footer3.addWidget(back_btn3); footer3.addStretch(); footer3.addWidget(next_btn3)
        l3.addSpacing(10); l3.addLayout(footer3)

        self.stack.addWidget(p3)

        # ------------------------------------------
        # Placeholder Pages for the rest (Pages 4 to 6)
        # ------------------------------------------
        for i in range(4, 7):
            page = QWidget()
            layout = QVBoxLayout(page)
            lbl = QLabel(f"Page {i+1} Content under construction...")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 18px; color: #718096;")
            layout.addWidget(lbl)
            self.stack.addWidget(page)

    # --- LOGIC & SYNCHRONIZATION ---
    def set_view(self, active_key, elev, azim):
        # Update CSS for active button
        for key, btn in self.view_btns.items():
            if key == active_key:
                btn.setObjectName("toolbar_btn_active")
            else:
                btn.setObjectName("toolbar_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Re-render 3D Plot
        self.draw_3d_model(elev, azim)

    def switch_page(self, index):
        if index == 1:
            self.in_span_geom.setText(self.in_span.text())
            self.in_girders_geom.setText(self.in_girders.text())
        elif index == 0:
            self.in_span.setText(self.in_span_geom.text())
            self.in_girders.setText(self.in_girders_geom.text())
        elif index == 2:
            self.in_load_class_loads.setCurrentText(self.in_load.currentText())
        elif index == 3:
            # Sync right sidebar properties based on inputs
            try:
                L = float(self.in_span.text())
                num_g = int(self.in_girders.text())
                f_ck = self.in_fck.currentText()
                spacing = 3.62 # Hardcoded fallback or dynamic
                depth = 2.0
                width = spacing * (num_g - 1) + 2.0
                
                self.lbl_v_span.setText(f"{L:.2f} m")
                self.lbl_v_gird.setText(f"{num_g}")
                self.lbl_v_spac.setText(f"{spacing:.2f} m")
                self.lbl_v_dep.setText(f"{depth:.2f} m")
                self.lbl_v_wid.setText(f"{width:.2f} m")
                self.lbl_v_conc.setText(f"{f_ck}")
                
            except ValueError:
                pass
                
            self.set_view("3D", 30, 45) # Render 3D model on page entry

        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        
        titles = ["PROJECT", "GEOMETRY", "LOADS", "3D MODEL", "ANALYSIS", "RESULTS", "REPORT"]
        subtitles = [
            "Define project information and general details for your bridge design.",
            "Configure span length, girder arrangements, and material grades.",
            "Define dead, live, and impact load conditions conforming to IRC:6-2017.",
            "Review and inspect the generated PSC bridge model.",
            "Execute structural calculation engine.",
            "Review design checks, bending moments, and shear utilizations.",
            "Generate professional calculation report."
        ]
        self.title_lbl.setText(titles[index])
        self.subtitle_lbl.setText(subtitles[index])

    def draw_3d_model(self, elev=30, azim=45):
        try:
            L = float(self.in_span.text())
            num_g = int(self.in_girders.text())
            spacing = 3.62
        except ValueError:
            L, num_g, spacing = 33.0, 4, 3.62

        self.fig3d.clear()
        
        # Configure Matplotlib axes to be completely invisible and blend with background
        ax = self.fig3d.add_subplot(111, projection='3d')
        ax.set_facecolor('#F8FAFC') 
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        
        width = spacing * (num_g - 1) + 2.0
        
        # Deck Slab Surface (Light grey)
        X_deck = np.array([[0, L], [0, L]])
        Y_deck = np.array([[-width/2, -width/2], [width/2, width/2]])
        Z_deck = np.array([[2, 2], [2, 2]])
        ax.plot_surface(X_deck, Y_deck, Z_deck, color='#CBD5E0', alpha=0.9, shade=True)
        
        # Girders (Navy blue)
        for i in range(num_g):
            y_pos = -width/2 + 1.0 + (i * spacing)
            
            # Flanges
            ax.plot([0, L], [y_pos, y_pos], [0, 0], color='#0F2546', linewidth=4)
            ax.plot([0, L], [y_pos, y_pos], [2, 2], color='#0F2546', linewidth=2)
            
            # Web
            X_web = np.array([[0, L], [0, L]])
            Y_web = np.array([[y_pos, y_pos], [y_pos, y_pos]])
            Z_web = np.array([[0, 0], [2, 2]])
            ax.plot_surface(X_web, Y_web, Z_web, color='#3182CE', alpha=0.8, shade=True)

        ax.set_box_aspect((3, 1, 0.3))
        self.fig3d.subplots_adjust(left=0, right=1, bottom=0, top=1) # Remove padding
        self.canvas3d.draw()

    def run_analysis(self):
        try:
            L = float(self.in_span.text())
            num_girders = int(self.in_girders.text())
            f_ck = float(self.in_fck.currentText()[1:])
            load_class = self.in_load.currentText()
            
            res = self.engine.analyze(L, num_girders, f_ck, load_class)
            print(f"ANALYSIS SUCCESSFUL: Max ULS Moment = {res['m_uls']} kNm")
            self.switch_page(5)
        except ValueError:
            print("Input error. Please check parameters.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PSCBridgeApp()
    window.show()
    sys.exit(app.exec())