import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, 
                               QStackedWidget, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QScrollArea, QGridLayout, QTextEdit, QDateEdit, QSizePolicy)
from PySide6.QtCore import Qt, QDate
from bridge_engine import BridgeEngine
from ui_3d_model import Model3DPage

# =====================================================================
# STYLESHEET (Professional Engineering Theme)
# =====================================================================
QSS = """
QMainWindow { background-color: #F0F4F8; font-family: "Segoe UI", Arial, sans-serif; }
#sidebar { background-color: #0F2546; }
#sidebar QPushButton { background-color: transparent; color: #A0AEC0; text-align: left; padding: 15px 25px; font-size: 13px; font-weight: bold; border: none; }
#sidebar QPushButton:hover { color: #FFFFFF; background-color: #1A365D; }
#sidebar QPushButton:checked { color: #FFFFFF; background-color: #1A365D; border-left: 4px solid #3182CE; }
QLabel#page_title { font-size: 24px; font-weight: 800; color: #1A202C; text-transform: uppercase;}
QLabel#page_subtitle { font-size: 13px; color: #718096; margin-bottom: 10px;}
QLabel#card_title { font-size: 16px; font-weight: bold; color: #123B63; }
QLabel#card_subtitle { font-size: 12px; color: #718096; }
QLabel#field_label { font-size: 12px; font-weight: 500; color: #4A5568; }
QLabel#req_star { color: #E53E3E; }
.QFrame#card { background-color: #FFFFFF; border-radius: 6px; border: 1px solid #E2E8F0; }
QLineEdit, QComboBox, QDateEdit { min-height: 36px; padding: 4px 12px; border: 1px solid #CBD5E0; border-radius: 4px; background-color: #FFFFFF; font-size: 13px; color: #2D3748; }
QTextEdit { min-height: 60px; padding: 8px 12px; border: 1px solid #CBD5E0; border-radius: 4px; background-color: #FFFFFF; font-size: 13px; color: #2D3748; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus { border: 1px solid #3182CE; }
QComboBox::drop-down { border: none; }
QTableWidget { background-color: white; border: 1px solid #E2E8F0; border-radius: 4px; gridline-color: #EDF2F7; }
QHeaderView::section { background-color: #F8FAFC; color: #123B63; padding: 8px; border: none; border-bottom: 1px solid #E2E8F0; font-weight: bold; font-size: 12px; }
QPushButton#primary_btn { background-color: #10B981; color: white; font-weight: bold; font-size: 13px; padding: 8px 20px; border-radius: 4px; }
QPushButton#primary_btn:hover { background-color: #059669; }
QPushButton#nav_next { background-color: #123B63; color: white; font-weight: bold; font-size: 13px; padding: 8px 20px; border-radius: 4px; }
QPushButton#nav_next:hover { background-color: #1A365D; }
QPushButton#nav_back { background-color: #F1F5F9; color: #A0AEC0; font-weight: bold; font-size: 13px; padding: 8px 20px; border-radius: 4px; border: 1px solid #E2E8F0; }
QScrollArea { border: none; background-color: transparent; }
"""

class PSCBridgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRUCTURAL SUITE Pro | PSC Bridge Design")
        self.setGeometry(50, 50, 1400, 900)
        self.setStyleSheet(QSS)
        
        self.engine = BridgeEngine()
        self.sync_active = False # Prevents infinite loops during text sync
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar); sidebar_layout.setContentsMargins(0, 25, 0, 15); sidebar_layout.setSpacing(5)
        
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🧠"); logo_icon.setStyleSheet("font-size: 28px; background: #0A192F; padding: 10px; border-radius: 8px; margin-left: 15px;")
        logo_text = QLabel("STRUCTURAL\nSUITE Pro\nBridge Design"); logo_text.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        logo_layout.addWidget(logo_icon); logo_layout.addWidget(logo_text); logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout); sidebar_layout.addSpacing(30)

        self.nav_btns = []
        nav_items = [("📄", "01   PROJECT"), ("📐", "02   GEOMETRY"), ("⚖️", "03   LOADS"), 
                     ("🖥️", "04   3D MODEL"), ("📊", "05   ANALYSIS"), ("📋", "06   RESULTS"), ("📑", "07   REPORT")]
        
        for idx, (icon, text) in enumerate(nav_items):
            btn = QPushButton(f"{icon}    {text}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            self.nav_btns.append(btn)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # 2. MAIN CONTENT
        content_area = QWidget()
        self.content_layout = QVBoxLayout(content_area)
        self.content_layout.setContentsMargins(30, 25, 30, 25)
        
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        self.title_lbl = QLabel("PROJECT"); self.title_lbl.setObjectName("page_title")
        self.subtitle_lbl = QLabel("Define project information and general details."); self.subtitle_lbl.setObjectName("page_subtitle")
        title_vbox.addWidget(self.title_lbl); title_vbox.addWidget(self.subtitle_lbl)
        header_layout.addLayout(title_vbox); header_layout.addStretch()
        
        analyze_btn = QPushButton("▶ RUN ANALYSIS"); analyze_btn.setObjectName("primary_btn")
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

    # --- UI HELPERS ---
    def create_field(self, label_text, widget, is_required=False):
        container = QWidget(); layout = QVBoxLayout(container); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
        lbl_layout = QHBoxLayout(); lbl_layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text); lbl.setObjectName("field_label"); lbl_layout.addWidget(lbl)
        if is_required:
            star = QLabel("*"); star.setObjectName("req_star"); lbl_layout.addWidget(star)
        lbl_layout.addStretch(); layout.addLayout(lbl_layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(widget); return container

    def create_inline_field(self, label_text, widget, unit=""):
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text); lbl.setObjectName("field_label"); lbl.setFixedWidth(130); layout.addWidget(lbl)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); layout.addWidget(widget)
        if unit:
            u_lbl = QLabel(unit); u_lbl.setObjectName("field_label"); layout.addWidget(u_lbl)
        return container

    def trigger_live_sync(self):
        """Reactively updates 3D models and duped inputs across pages instantly"""
        if self.sync_active: return
        self.sync_active = True
        
        sender = self.sender()
        try:
            # Sync duped text fields
            if sender == self.in_span: self.in_span_geom.setText(self.in_span.text())
            elif sender == self.in_span_geom: self.in_span.setText(self.in_span_geom.text())
            
            if sender == self.in_girders: self.in_girders_geom.setText(self.in_girders.text())
            elif sender == self.in_girders_geom: self.in_girders.setText(self.in_girders_geom.text())

            # Push live update to 3D model
            L = float(self.in_span.text() or 0)
            num_g = int(self.in_girders.text() or 0)
            spacing = float(self.in_spacing_geom.text() or 0)
            depth = float(self.in_depth_geom.text() or 0)
            tw = float(self.in_tw.text() or 0)
            tf = float(self.in_tf.text() or 0)
            bf = float(self.in_bf.text() or 0)
            f_ck = self.in_fck.currentText()
            
            self.model_3d_page.update_properties(L, num_g, spacing, depth, tw, tf, bf, f_ck)
        except ValueError:
            pass # Ignore temporary empty strings while typing
        finally:
            self.sync_active = False

    def build_pages(self):
        # ------------------------------------------
        # PAGE 0: PROJECT
        # ------------------------------------------
        p0_scroll = QScrollArea(); p0_scroll.setWidgetResizable(True)
        p0 = QWidget(); l0 = QVBoxLayout(p0); l0.setContentsMargins(0, 0, 15, 0); l0.setSpacing(15)

        c1 = QFrame(); c1.setObjectName("card")
        cl1 = QVBoxLayout(c1); cl1.setContentsMargins(20, 20, 20, 20)
        
        header1 = QLabel("📄 Project Details"); header1.setObjectName("card_title"); cl1.addWidget(header1); cl1.addSpacing(10)
        
        grid = QGridLayout(); grid.setSpacing(20)
        name_in = QLineEdit("33 m PSC I-Girder Bridge")
        id_in = QLineEdit(); id_in.setPlaceholderText("e.g. BR-001")
        designer_in = QLineEdit("Structural Engineer")
        client_in = QLineEdit(); client_in.setPlaceholderText("e.g. NHAI / State PWD")
        code_in = QComboBox(); code_in.addItems(["IRC:6-2017, IRC:SP:71-2018", "AASHTO LRFD", "Eurocode 2"])
        date_in = QDateEdit(); date_in.setDate(QDate.currentDate()); date_in.setCalendarPopup(True)
        
        grid.addWidget(self.create_field("Project Name", name_in, True), 0, 0)
        grid.addWidget(self.create_field("Project ID (Optional)", id_in), 0, 1)
        grid.addWidget(self.create_field("Designer", designer_in, True), 1, 0)
        grid.addWidget(self.create_field("Client (Optional)", client_in), 1, 1)
        grid.addWidget(self.create_field("Design Code", code_in, True), 2, 0)
        grid.addWidget(self.create_field("Date", date_in), 2, 1)
        
        cl1.addLayout(grid); cl1.addSpacing(10)
        desc_in = QTextEdit("Design and analysis of a 33 m PSC I-Girder Bridge.")
        cl1.addWidget(self.create_field("Project Description (Optional)", desc_in))
        l0.addWidget(c1)

        split_layout = QHBoxLayout(); split_layout.setSpacing(15)
        
        c2 = QFrame(); c2.setObjectName("card")
        cl2 = QVBoxLayout(c2); cl2.setContentsMargins(20, 20, 20, 20); cl2.setSpacing(12)
        
        header2 = QLabel("🏢 Project Summary"); header2.setObjectName("card_title")
        sub2 = QLabel("Key parameters for the bridge model."); sub2.setObjectName("card_subtitle")
        cl2.addWidget(header2); cl2.addWidget(sub2); cl2.addSpacing(15)
        
        type_in = QComboBox(); type_in.addItems(["PSC I-Girder Bridge", "Box Girder", "T-Beam"])
        self.in_span = QLineEdit("33.00")
        self.in_girders = QLineEdit("4")
        self.in_fck = QComboBox(); self.in_fck.addItems(["M40", "M45", "M50", "M55", "M60"]); self.in_fck.setCurrentText("M50")
        self.in_load = QComboBox(); self.in_load.addItems(["Class 70R Wheeled", "Class 70R Tracked", "Class A", "Class B"])
        
        self.in_span.textChanged.connect(self.trigger_live_sync)
        self.in_girders.textChanged.connect(self.trigger_live_sync)
        self.in_fck.currentTextChanged.connect(self.trigger_live_sync)
        
        cl2.addWidget(self.create_inline_field("Bridge Type", type_in))
        cl2.addWidget(self.create_inline_field("Span Length", self.in_span, "m"))
        cl2.addWidget(self.create_inline_field("Number of Girders", self.in_girders))
        cl2.addWidget(self.create_inline_field("Concrete Grade", self.in_fck))
        cl2.addWidget(self.create_inline_field("Loading Class", self.in_load))
        
        split_layout.addWidget(c2) 
        split_layout.addStretch() 
        l0.addLayout(split_layout)

        footer0 = QHBoxLayout()
        back_btn0 = QPushButton("← Back"); back_btn0.setObjectName("nav_back"); back_btn0.setEnabled(False)
        next_btn0 = QPushButton("Next: Geometry →"); next_btn0.setObjectName("nav_next"); next_btn0.clicked.connect(lambda: self.switch_page(1))
        footer0.addWidget(back_btn0); footer0.addStretch(); footer0.addWidget(next_btn0)
        l0.addSpacing(10); l0.addLayout(footer0)

        p0_scroll.setWidget(p0)
        self.stack.addWidget(p0_scroll)

        # ------------------------------------------
        # PAGE 1: GEOMETRY & MATERIALS
        # ------------------------------------------
        p1_scroll = QScrollArea(); p1_scroll.setWidgetResizable(True)
        p1 = QWidget(); l1 = QVBoxLayout(p1); l1.setContentsMargins(0, 0, 15, 0); l1.setSpacing(15)

        cg1 = QFrame(); cg1.setObjectName("card")
        cl_g1 = QVBoxLayout(cg1); cl_g1.setContentsMargins(20, 20, 20, 20)
        hg1 = QLabel("📐 Global Geometry Specifications"); hg1.setObjectName("card_title"); cl_g1.addWidget(hg1); cl_g1.addSpacing(10)
        
        grid_g = QGridLayout(); grid_g.setSpacing(20)
        self.in_span_geom = QLineEdit("33.00")
        self.in_girders_geom = QLineEdit("4")
        self.in_spacing_geom = QLineEdit("2.75")
        self.in_depth_geom = QLineEdit("2.00")
        
        self.in_tw = QLineEdit("0.30")
        self.in_tf = QLineEdit("0.20")
        self.in_bf = QLineEdit("0.80")

        self.in_span_geom.textChanged.connect(self.trigger_live_sync)
        self.in_girders_geom.textChanged.connect(self.trigger_live_sync)
        self.in_spacing_geom.textChanged.connect(self.trigger_live_sync)
        self.in_depth_geom.textChanged.connect(self.trigger_live_sync)
        self.in_tw.textChanged.connect(self.trigger_live_sync)
        self.in_tf.textChanged.connect(self.trigger_live_sync)
        self.in_bf.textChanged.connect(self.trigger_live_sync)
        
        grid_g.addWidget(self.create_field("Effective Span Length (m)", self.in_span_geom), 0, 0)
        grid_g.addWidget(self.create_field("Number of Longitudinal Girders", self.in_girders_geom), 0, 1)
        grid_g.addWidget(self.create_field("Girder Spacing (m) [2.5m - 3m]", self.in_spacing_geom), 1, 0)
        grid_g.addWidget(self.create_field("Overall Girder Depth (m)", self.in_depth_geom), 1, 1)
        cl_g1.addLayout(grid_g); l1.addWidget(cg1)

        cg_sec = QFrame(); cg_sec.setObjectName("card")
        cl_gsec = QVBoxLayout(cg_sec); cl_gsec.setContentsMargins(20, 20, 20, 20)
        h_gsec = QLabel("📏 Girder Cross-Section Details"); h_gsec.setObjectName("card_title"); cl_gsec.addWidget(h_gsec)
        
        # IRC SP 71 minimum constraint text
        irc_warning = QLabel("<b>IRC:SP:71-2018 Minimums:</b> Top Flange = 100 mm, Bottom Flange = 150 mm, Web = 150 mm")
        irc_warning.setStyleSheet("color: #C53030; font-size: 11px; margin-bottom: 10px;")
        cl_gsec.addWidget(irc_warning)

        grid_sec = QGridLayout(); grid_sec.setSpacing(20)
        grid_sec.addWidget(self.create_field("Top Flange Thickness (m)", self.in_tf), 0, 0)
        grid_sec.addWidget(self.create_field("Bottom Flange Thickness (m)", self.in_bf), 0, 1)
        grid_sec.addWidget(self.create_field("Web Thickness (m)", self.in_tw), 1, 0)
        cl_gsec.addLayout(grid_sec); l1.addWidget(cg_sec)

        cg2 = QFrame(); cg2.setObjectName("card")
        cl_g2 = QVBoxLayout(cg2); cl_g2.setContentsMargins(20, 20, 20, 20)
        hg2 = QLabel("🧪 Detailed Material Grades"); hg2.setObjectName("card_title"); cl_g2.addWidget(hg2); cl_g2.addSpacing(10)
        
        grid_m = QGridLayout(); grid_m.setSpacing(20)
        self.in_steel = QComboBox(); self.in_steel.addItems(["Fe500 (TMT)", "Fe415", "Fe550"])
        self.in_tendon = QComboBox(); self.in_tendon.addItems(["Low Relaxation 1860 MPa Strands", "Stress Relieved Strands"])
        
        grid_m.addWidget(self.create_field("Reinforcement Steel Grade", self.in_steel), 0, 0)
        grid_m.addWidget(self.create_field("Prestressing Tendon Type", self.in_tendon), 0, 1)
        cl_g2.addLayout(grid_m); l1.addWidget(cg2)

        footer1 = QHBoxLayout()
        back_btn1 = QPushButton("← Back to Project"); back_btn1.setObjectName("nav_back"); back_btn1.clicked.connect(lambda: self.switch_page(0))
        next_btn1 = QPushButton("Next: Loads →"); next_btn1.setObjectName("nav_next"); next_btn1.clicked.connect(lambda: self.switch_page(2))
        footer1.addWidget(back_btn1); footer1.addStretch(); footer1.addWidget(next_btn1)
        l1.addSpacing(10); l1.addLayout(footer1)

        p1_scroll.setWidget(p1)
        self.stack.addWidget(p1_scroll)

        # ------------------------------------------
        # PAGE 2: LOADS
        # ------------------------------------------
        p2_scroll = QScrollArea(); p2_scroll.setWidgetResizable(True)
        p2 = QWidget(); l2 = QVBoxLayout(p2); l2.setContentsMargins(0, 0, 15, 0); l2.setSpacing(15)

        cload1 = QFrame(); cload1.setObjectName("card")
        cl_l1 = QVBoxLayout(cload1); cl_l1.setContentsMargins(20, 20, 20, 20)
        h_l1 = QLabel("🚚 IRC Live Load Specifications (IRC:6-2017)"); h_l1.setObjectName("card_title"); cl_l1.addWidget(h_l1); cl_l1.addSpacing(10)
        
        grid_l = QGridLayout(); grid_l.setSpacing(20)
        self.in_load_class_loads = QComboBox()
        self.in_load_class_loads.addItems(["Class 70R Wheeled", "Class 70R Tracked", "Class A", "Class B"])
        self.in_load_class_loads.setCurrentText("Class 70R Wheeled")
        self.in_lanes = QLineEdit("3")
        
        grid_l.addWidget(self.create_field("Design Vehicle / Loading Class", self.in_load_class_loads), 0, 0)
        grid_l.addWidget(self.create_field("Number of Design Lanes", self.in_lanes), 0, 1)
        cl_l1.addLayout(grid_l); l2.addWidget(cload1)

        cload2 = QFrame(); cload2.setObjectName("card")
        cl_l2 = QVBoxLayout(cload2); cl_l2.setContentsMargins(20, 20, 20, 20)
        h_l2 = QLabel("📋 Active Structural Load Cases"); h_l2.setObjectName("card_title")
        sub_l2 = QLabel("Summary of dead, live, and environmental actions applied to girders."); sub_l2.setObjectName("card_subtitle")
        cl_l2.addWidget(h_l2); cl_l2.addWidget(sub_l2); cl_l2.addSpacing(15)
        
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
                
        cl_l2.addWidget(load_table); l2.addWidget(cload2)

        footer2 = QHBoxLayout()
        back_btn2 = QPushButton("← Back to Geometry"); back_btn2.setObjectName("nav_back"); back_btn2.clicked.connect(lambda: self.switch_page(1))
        next_btn2 = QPushButton("Next: 3D Model →"); next_btn2.setObjectName("nav_next"); next_btn2.clicked.connect(lambda: self.switch_page(3))
        footer2.addWidget(back_btn2); footer2.addStretch(); footer2.addWidget(next_btn2)
        l2.addSpacing(10); l2.addLayout(footer2)

        p2_scroll.setWidget(p2)
        self.stack.addWidget(p2_scroll)

        # ------------------------------------------
        # PAGE 3: Import 3D / 2D model page
        # ------------------------------------------
        self.model_3d_page = Model3DPage(self)
        self.stack.addWidget(self.model_3d_page)

        # ------------------------------------------
        # PAGES 4, 5, 6
        # ------------------------------------------
        for i in range(4, 7):
            pg = QWidget(); ly = QVBoxLayout(pg)
            lbl = QLabel(f"Page {i+1} Content under construction..."); lbl.setAlignment(Qt.AlignCenter); lbl.setStyleSheet("font-size: 18px; color: #718096;")
            ly.addWidget(lbl)
            self.stack.addWidget(pg)

    def switch_page(self, index):
        if index == 2:
            self.in_load_class_loads.setCurrentText(self.in_load.currentText())

        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        
        titles = ["PROJECT", "GEOMETRY", "LOADS", "3D MODEL", "ANALYSIS", "RESULTS", "REPORT"]
        self.title_lbl.setText(titles[index])

    def run_analysis(self):
        try:
            L = float(self.in_span.text()); num_girders = int(self.in_girders.text())
            f_ck = float(self.in_fck.currentText()[1:]); load_class = self.in_load.currentText()
            res = self.engine.analyze(L, num_girders, f_ck, load_class)
            print(f"ANALYSIS SUCCESSFUL: Max ULS Moment = {res['m_uls']} kNm")
            self.switch_page(5)
        except ValueError:
            print("Input error.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PSCBridgeApp()
    window.show()
    sys.exit(app.exec())