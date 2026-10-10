import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QCheckBox, QFileDialog, QDialog, QSizePolicy)
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.figure import Figure

class Model3DPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window 
        
        # Default Bridge Parameters
        self.L = 33.0
        self.num_g = 4
        self.spacing = 2.75
        self.depth = 2.0
        self.tw = 0.30
        self.tf = 0.20
        self.bf = 0.80
        self.f_ck = "M50"
        
        self.show_grid = False
        self.show_dims = False
        self.current_view_mode = "3D" 
        self.current_elev = 20
        self.current_azim = -55
        self.zoom_factor = 1.0  
        
        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 15, 0)
        main_layout.setSpacing(15)

        cad_split = QHBoxLayout()
        cad_split.setSpacing(15)

        # --- LEFT PANEL (Viewport & Toolbars) ---
        self.viewport_layout = QVBoxLayout()
        self.viewport_layout.setSpacing(10)
        
        # Top Toolbar (Views)
        v_toolbar_top = QHBoxLayout()
        v_toolbar_top.setSpacing(8)
        
        self.view_btns = {}
        b_3d = QPushButton("3D VIEW")
        b_top = QPushButton("⌖ TOP")
        b_front = QPushButton("⚄ FRONT")
        b_side = QPushButton("⧉ SIDE")
        b_bridge_sec = QPushButton("◩ BRIDGE SECTION")
        b_girder_sec = QPushButton("⌶ GIRDER SECTION")
        
        self.view_btns['3D'] = b_3d; self.view_btns['TOP'] = b_top
        self.view_btns['FRONT'] = b_front; self.view_btns['SIDE'] = b_side
        self.view_btns['BRIDGE_SEC'] = b_bridge_sec; self.view_btns['GIRDER_SEC'] = b_girder_sec
        
        for btn in self.view_btns.values():
            btn.setObjectName("toolbar_btn")
        b_3d.setObjectName("toolbar_btn_active")
        
        b_3d.clicked.connect(lambda: self.set_view("3D", 20, -55))
        b_top.clicked.connect(lambda: self.set_view("TOP", 90, -90))
        b_front.clicked.connect(lambda: self.set_view("FRONT", 0, -90))
        b_side.clicked.connect(lambda: self.set_view("SIDE", 0, 0))
        b_bridge_sec.clicked.connect(lambda: self.set_view("BRIDGE_SEC", 0, 0))
        b_girder_sec.clicked.connect(lambda: self.set_view("GIRDER_SEC", 0, 0))

        v_toolbar_top.addWidget(b_3d); v_toolbar_top.addWidget(b_top)
        v_toolbar_top.addWidget(b_front); v_toolbar_top.addWidget(b_side)
        v_toolbar_top.addWidget(b_bridge_sec); v_toolbar_top.addWidget(b_girder_sec)
        v_toolbar_top.addStretch()
        
        # Bottom Toolbar (Tools & Navigation)
        v_toolbar_bot = QHBoxLayout()
        v_toolbar_bot.setSpacing(8)
        
        self.b_dim = QPushButton("↔ SHOW DIMENSIONS"); self.b_dim.setCheckable(True)
        self.b_grid = QPushButton("▦ GRID"); self.b_grid.setCheckable(True)
        
        b_pan = QPushButton("✋ PAN")
        b_zoom_rect = QPushButton("🔎 ZOOM BOX")
        b_zoom_in = QPushButton("🔍 ZOOM IN")
        b_zoom_out = QPushButton("🔍 ZOOM OUT")
        b_fs = QPushButton("🖵 FULL SCREEN")
        b_export = QPushButton("📷 EXPORT IMAGE")
        
        for btn in [self.b_dim, self.b_grid, b_pan, b_zoom_rect, b_zoom_in, b_zoom_out, b_fs, b_export]:
            btn.setObjectName("toolbar_btn")
        
        self.b_dim.clicked.connect(self.toggle_dims)
        self.b_grid.clicked.connect(self.toggle_grid)
        b_zoom_in.clicked.connect(self.zoom_in)
        b_zoom_out.clicked.connect(self.zoom_out)
        b_fs.clicked.connect(self.toggle_fullscreen)
        b_export.clicked.connect(self.export_image)
        
        v_toolbar_bot.addWidget(self.b_dim); v_toolbar_bot.addWidget(self.b_grid)
        v_toolbar_bot.addSpacing(10)
        v_toolbar_bot.addWidget(b_pan); v_toolbar_bot.addWidget(b_zoom_rect)
        v_toolbar_bot.addSpacing(10)
        v_toolbar_bot.addWidget(b_zoom_in); v_toolbar_bot.addWidget(b_zoom_out)
        v_toolbar_bot.addStretch()
        v_toolbar_bot.addWidget(b_fs); v_toolbar_bot.addWidget(b_export)

        self.viewport_layout.addLayout(v_toolbar_top)
        self.viewport_layout.addLayout(v_toolbar_bot)
        
        # Matplotlib Canvas Frame
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("card")
        self.canvas_frame.setStyleSheet("background-color: #F8FAFC;") 
        self.canvas_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        cl_canvas = QVBoxLayout(self.canvas_frame)
        cl_canvas.setContentsMargins(0, 0, 0, 0)
        cl_canvas.setSpacing(0)
        
        self.fig3d = Figure(figsize=(8, 5), facecolor='#F8FAFC')
        self.canvas3d = FigureCanvas(self.fig3d)
        self.canvas3d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.fig3d.canvas.mpl_connect('scroll_event', self.on_scroll)
        
        self.mpl_toolbar = NavigationToolbar2QT(self.canvas3d, self)
        self.mpl_toolbar.hide() 
        b_pan.clicked.connect(self.mpl_toolbar.pan)
        b_zoom_rect.clicked.connect(self.mpl_toolbar.zoom)
        
        cl_canvas.addWidget(self.canvas3d)
        
        status_bar = QLabel("  ✅  Live Geometry Sync Active   |   Use mouse wheel to zoom to cursor.")
        status_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        status_bar.setStyleSheet("background-color: #DEF7EC; color: #03543F; font-size: 12px; font-weight: bold; padding: 10px; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;")
        cl_canvas.addWidget(status_bar)
        
        self.viewport_layout.addWidget(self.canvas_frame)

        # --- RIGHT PANEL (Sidebar Properties) ---
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)
        
        c_prop = QFrame(); c_prop.setObjectName("card"); c_prop.setFixedWidth(280)
        cl_prop = QVBoxLayout(c_prop)
        h_prop = QLabel("📋 MODEL PROPERTIES"); h_prop.setObjectName("card_title"); h_prop.setStyleSheet("font-size: 13px;")
        cl_prop.addWidget(h_prop); cl_prop.addSpacing(10)
        
        self.lbl_v_span = QLabel(f"{self.L:.2f} m")
        self.lbl_v_gird = QLabel(f"{self.num_g}")
        self.lbl_v_spac = QLabel(f"{self.spacing:.2f} m")
        self.lbl_v_dep = QLabel(f"{self.depth:.2f} m")
        self.lbl_v_wid = QLabel("10.25 m")
        self.lbl_v_conc = QLabel(f"{self.f_ck}")
        
        cl_prop.addLayout(self.create_prop_row("Span Length, L", self.lbl_v_span))
        cl_prop.addLayout(self.create_prop_row("Longitudinal Girders", self.lbl_v_gird))
        cl_prop.addLayout(self.create_prop_row("Girder Spacing", self.lbl_v_spac))
        cl_prop.addLayout(self.create_prop_row("Overall Girder Depth", self.lbl_v_dep))
        cl_prop.addLayout(self.create_prop_row("Deck Width", self.lbl_v_wid))
        cl_prop.addLayout(self.create_prop_row("Concrete Grade", self.lbl_v_conc))
        sidebar_layout.addWidget(c_prop)
        
        c_comp = QFrame(); c_comp.setObjectName("card"); c_comp.setFixedWidth(280)
        cl_comp = QVBoxLayout(c_comp)
        h_comp = QLabel("🏗️ MODEL COMPONENTS"); h_comp.setObjectName("card_title"); h_comp.setStyleSheet("font-size: 13px;")
        cl_comp.addWidget(h_comp); cl_comp.addSpacing(10)
        
        self.cb_deck = QCheckBox("Deck Slab"); self.cb_deck.setChecked(True)
        self.cb_gird = QCheckBox("PSC I-Girders"); self.cb_gird.setChecked(True)
        self.cb_abut = QCheckBox("Piers & Pile Foundations"); self.cb_abut.setChecked(True)
        
        self.cb_deck.stateChanged.connect(lambda: self.render_model())
        self.cb_gird.stateChanged.connect(lambda: self.render_model())
        self.cb_abut.stateChanged.connect(lambda: self.render_model())
        
        cl_comp.addWidget(self.cb_deck); cl_comp.addWidget(self.cb_gird)
        cl_comp.addWidget(self.cb_abut)
        sidebar_layout.addWidget(c_comp)
        sidebar_layout.addStretch()
        
        cad_split.addLayout(self.viewport_layout, 7)
        cad_split.addLayout(sidebar_layout, 3)
        main_layout.addLayout(cad_split)

        footer = QHBoxLayout()
        back_btn = QPushButton("← Back to Loads"); back_btn.setObjectName("nav_back")
        back_btn.clicked.connect(lambda: self.main_window.switch_page(2))
        next_btn = QPushButton("Next: Analysis →"); next_btn.setObjectName("nav_next")
        next_btn.clicked.connect(lambda: self.main_window.switch_page(4))
        footer.addWidget(back_btn); footer.addStretch(); footer.addWidget(next_btn)
        main_layout.addSpacing(10); main_layout.addLayout(footer)

    def create_prop_row(self, label, value):
        row = QHBoxLayout(); row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label); lbl.setStyleSheet("color: #4A5568; font-size: 13px;")
        value.setStyleSheet("color: #1A202C; font-size: 13px; font-weight: bold;")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(lbl); row.addWidget(value)
        return row

    def update_properties(self, L, num_g, spacing, depth, tw, tf, bf, f_ck):
        self.L = L; self.num_g = num_g; self.spacing = spacing; self.depth = depth
        self.tw = tw; self.tf = tf; self.bf = bf; self.f_ck = f_ck
        
        width = self.spacing * (self.num_g - 1) + 2.0
        self.lbl_v_span.setText(f"{self.L:.2f} m")
        self.lbl_v_gird.setText(f"{self.num_g}")
        self.lbl_v_spac.setText(f"{self.spacing:.2f} m")
        self.lbl_v_dep.setText(f"{self.depth:.2f} m")
        self.lbl_v_wid.setText(f"{width:.2f} m")
        self.lbl_v_conc.setText(f"{self.f_ck}")
        self.render_model()

    # ================= EVENT HANDLERS & FULLSCREEN =================

    def toggle_fullscreen(self):
        self.fs_dialog = QDialog(self.main_window)
        self.fs_dialog.setWindowTitle("3D Model - Full Screen View")
        self.fs_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.fs_dialog.showFullScreen() # True full screen across all monitors bounds
        
        layout = QVBoxLayout(self.fs_dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        top_bar = QHBoxLayout()
        lbl = QLabel("STRUCTURAL SUITE Pro - Full Screen Mode")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #123B63;")
        
        close_btn = QPushButton("❌ EXIT FULL SCREEN")
        close_btn.setObjectName("primary_btn")
        close_btn.setStyleSheet("background-color: #E53E3E; color: white;")
        close_btn.clicked.connect(self.fs_dialog.accept)
        
        top_bar.addWidget(lbl); top_bar.addStretch(); top_bar.addWidget(close_btn)
        layout.addLayout(top_bar)
        
        layout.addWidget(self.canvas_frame) 
        
        self.fs_dialog.finished.connect(self.exit_fullscreen)
        self.fs_dialog.exec()
        
    def exit_fullscreen(self):
        self.viewport_layout.addWidget(self.canvas_frame)

    def on_scroll(self, event):
        if event.inaxes is None: return
        scale = 0.8 if event.button == 'up' else 1.25
        
        if self.current_view_mode in ["BRIDGE_SEC", "GIRDER_SEC"]:
            ax = event.inaxes
            xdata, ydata = event.xdata, event.ydata
            if xdata is None or ydata is None: return
            
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            
            new_width = (xlim[1] - xlim[0]) * scale
            new_height = (ylim[1] - ylim[0]) * scale
            
            rel_x = (xdata - xlim[0]) / (xlim[1] - xlim[0])
            rel_y = (ydata - ylim[0]) / (ylim[1] - ylim[0])
            
            ax.set_xlim([xdata - new_width * rel_x, xdata + new_width * (1 - rel_x)])
            ax.set_ylim([ydata - new_height * rel_y, ydata + new_height * (1 - rel_y)])
            self.canvas3d.draw_idle()
        else:
            self.zoom_factor *= scale
            self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
            self.render_model()

    # ================= VIEW & RENDERING LOGIC =================

    def set_view(self, active_key, elev, azim):
        self.current_view_mode = active_key
        self.current_elev = elev
        self.current_azim = azim
        self.zoom_factor = 1.0  
        for key, btn in self.view_btns.items():
            btn.setObjectName("toolbar_btn_active" if key == active_key else "toolbar_btn")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self.render_model()

    def toggle_grid(self):
        self.show_grid = self.b_grid.isChecked()
        self.b_grid.setObjectName("toolbar_btn_active" if self.show_grid else "toolbar_btn")
        self.b_grid.style().unpolish(self.b_grid); self.b_grid.style().polish(self.b_grid)
        self.render_model()

    def toggle_dims(self):
        self.show_dims = self.b_dim.isChecked()
        self.b_dim.setObjectName("toolbar_btn_active" if self.show_dims else "toolbar_btn")
        self.b_dim.style().unpolish(self.b_dim); self.b_dim.style().polish(self.b_dim)
        self.render_model()

    def zoom_in(self):
        self.zoom_factor *= 0.8  
        self.render_model()

    def zoom_out(self):
        self.zoom_factor *= 1.25 
        self.render_model()

    def export_image(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Model Image", "", "PNG Image (*.png);;JPEG Image (*.jpg)")
        if file_path:
            self.fig3d.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='#F8FAFC')

    def create_girder_polygon(self, x_offset, y_offset):
        tf = self.tf; bf = self.bf; tw = self.tw; d = self.depth
        pts = [
            (x_offset - bf/2, y_offset), (x_offset + bf/2, y_offset),
            (x_offset + bf/2, y_offset + 0.15), (x_offset + tw/2, y_offset + 0.35),
            (x_offset + tw/2, y_offset + d - 0.35), (x_offset + bf/2, y_offset + d - 0.15),
            (x_offset + bf/2, y_offset + d), (x_offset - bf/2, y_offset + d),
            (x_offset - bf/2, y_offset + d - 0.15), (x_offset - tw/2, y_offset + d - 0.35),
            (x_offset - tw/2, y_offset + 0.35), (x_offset - bf/2, y_offset + 0.15)
        ]
        return patches.Polygon(pts, closed=True, facecolor='#D9E2EC', edgecolor='#123B63', linewidth=1.5, zorder=3)

    def draw_cylinder_3d(self, ax, x, y, z, h, r, color):
        z_vals = np.linspace(z, z + h, 2)
        theta = np.linspace(0, 2 * np.pi, 16)
        theta_grid, z_grid = np.meshgrid(theta, z_vals)
        x_grid = r * np.cos(theta_grid) + x
        y_grid = r * np.sin(theta_grid) + y
        ax.plot_surface(x_grid, y_grid, z_grid, color=color, alpha=1.0, shade=True, edgecolor='none')

    def draw_bridge_section_2d(self, ax):
        width = self.spacing * (self.num_g - 1) + 2.0
        mid_x = 0
        total_foundation_depth = 15.85
        mid_y = (self.depth - total_foundation_depth) / 2 if self.cb_abut.isChecked() else self.depth / 2
        max_range_x = (width / 2 + 3) * self.zoom_factor
        max_range_y = (total_foundation_depth + self.depth + 4) / 2 * self.zoom_factor if self.cb_abut.isChecked() else (self.depth / 2 + 3) * self.zoom_factor
        
        ax.set_xlim(mid_x - max_range_x, mid_x + max_range_x)
        ax.set_ylim(mid_y - max_range_y, mid_y + max_range_y)

        if self.cb_abut.isChecked():
            cap_h = 1.2; col_h = 5.0; pcap_h = 1.5; pile_h = 8.0; z_bear = -0.15
            for i in range(self.num_g):
                y_center = -width/2 + 1.0 + (i * self.spacing)
                ax.add_patch(patches.Rectangle((y_center - 0.2, z_bear), 0.4, 0.15, facecolor='#38A169', edgecolor='black', zorder=2))

            ax.add_patch(patches.Rectangle((-width/2 - 0.5, z_bear - cap_h), width + 1, cap_h, facecolor='#CBD5E0', edgecolor='#A0AEC0', lw=1.5, zorder=1))
            ax.add_patch(patches.Rectangle((-1.2, z_bear - cap_h - col_h), 2.4, col_h, facecolor='#A0AEC0', edgecolor='grey', lw=1.5, zorder=1))
            
            pw = width * 0.6
            z_pcap_top = z_bear - cap_h - col_h
            ax.add_patch(patches.Rectangle((-pw/2, z_pcap_top - pcap_h), pw, pcap_h, facecolor='#94A3B8', edgecolor='grey', lw=1.5, zorder=1))
            
            ny = 4; space_y = (pw - 1.0) / (ny - 1); z_pile_top = z_pcap_top - pcap_h
            for j in range(ny):
                pile_y = -pw/2 + 0.5 + j * space_y
                ax.add_patch(patches.Rectangle((pile_y - 0.3, z_pile_top - pile_h), 0.6, pile_h, facecolor='#718096', edgecolor='black', zorder=1))

        if self.cb_deck.isChecked():
            ax.add_patch(patches.Rectangle((-width/2, self.depth), width, 0.25, facecolor='#CBD5E0', edgecolor='#4A5568', linewidth=1.5, zorder=3))
            ax.add_patch(patches.Rectangle((-width/2, self.depth + 0.25), 0.5, 0.8, facecolor='#A0AEC0', edgecolor='#4A5568', zorder=3))
            ax.add_patch(patches.Rectangle((width/2 - 0.5, self.depth + 0.25), 0.5, 0.8, facecolor='#A0AEC0', edgecolor='#4A5568', zorder=3))

        if self.cb_gird.isChecked():
            for i in range(self.num_g):
                x_center = -width/2 + 1.0 + (i * self.spacing)
                ax.add_patch(self.create_girder_polygon(x_center, 0))
                ax.text(x_center, self.depth / 2, f"G{i+1}", ha='center', va='center', weight='bold', color='white', zorder=4)

        if self.show_dims:
            ax.annotate(f"Overall Deck Width = {width:.2f} m", xy=(-width/2, self.depth + 1.8), xytext=(width/2, self.depth + 1.8),
                        arrowprops=dict(arrowstyle="<|-|>", color='#3182CE', lw=1.5), ha='center', va='bottom', color='#3182CE', weight='bold')
            for i in range(self.num_g - 1):
                x1 = -width/2 + 1.0 + (i * self.spacing)
                x2 = x1 + self.spacing
                ax.annotate(f"{self.spacing:.2f} m", xy=(x1, self.depth + 0.5), xytext=(x2, self.depth + 0.5),
                            arrowprops=dict(arrowstyle="<|-|>", color='#E53E3E', lw=1.5), ha='center', va='bottom', color='#E53E3E', weight='bold')

    def draw_girder_section_2d(self, ax):
        mid_x = 0; mid_y = self.depth / 2
        max_range_x = 2 * self.zoom_factor
        max_range_y = (self.depth / 2 + 1) * self.zoom_factor
        ax.set_xlim(mid_x - max_range_x, mid_x + max_range_x)
        ax.set_ylim(mid_y - max_range_y, mid_y + max_range_y)

        ax.add_patch(self.create_girder_polygon(0, 0))
        
        tendon_y = [0.1, 0.1, 0.4, 0.8, 1.2, self.depth - 0.1]
        tendon_x = [0.2, -0.2, 0, 0, 0, 0]
        tendon_labels = ["O1", "O2", "O3", "O4", "O5", "O6"]
        
        for tx, ty, lbl in zip(tendon_x, tendon_y, tendon_labels):
            ax.add_patch(patches.Circle((tx, ty), 0.04, facecolor='white', edgecolor='#E53E3E', linewidth=1.5, zorder=3))
            x_shift = -0.15 if tx < 0 else 0.15
            ax.text(tx + x_shift, ty, lbl, va='center', ha='center', fontsize=10, color='#1A202C', weight='bold', zorder=4)

        if self.show_dims:
            ax.annotate(f"Overall Depth, D = {self.depth:.2f} m", xy=(-self.bf/2 - 0.3, 0), xytext=(-self.bf/2 - 0.3, self.depth),
                        arrowprops=dict(arrowstyle="<|-|>", color='#3182CE', lw=1.5), ha='right', va='center', color='#3182CE', weight='bold')
            ax.annotate(f"Top Flange ({self.tf*1000:.0f} mm)", xy=(self.bf/2 - 0.1, self.depth - 0.1), xytext=(self.bf/2 + 0.4, self.depth - 0.1),
                        arrowprops=dict(arrowstyle="->", color='black', lw=1.5), va='center', weight='bold')
            ax.annotate(f"Web ({self.tw*1000:.0f} mm)", xy=(self.tw/2, self.depth / 2), xytext=(self.bf/2 + 0.4, self.depth / 2),
                        arrowprops=dict(arrowstyle="->", color='black', lw=1.5), va='center', weight='bold')
            ax.annotate(f"Bottom Flange ({self.bf*1000:.0f} mm)", xy=(self.bf/2 - 0.1, 0.1), xytext=(self.bf/2 + 0.4, 0.1),
                        arrowprops=dict(arrowstyle="->", color='black', lw=1.5), va='center', weight='bold')

    def render_model(self):
        self.fig3d.clear()
        
        if self.current_view_mode in ["BRIDGE_SEC", "GIRDER_SEC"]:
            ax = self.fig3d.add_subplot(111)
            ax.set_facecolor('#F8FAFC')
            ax.set_aspect('equal', adjustable='datalim')
            
            if not self.show_grid:
                ax.axis('off')
            else:
                ax.grid(True, linestyle=':', alpha=0.6)
                
            if self.current_view_mode == "BRIDGE_SEC":
                self.draw_bridge_section_2d(ax)
            else:
                self.draw_girder_section_2d(ax)
            
            self.fig3d.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
            self.canvas3d.draw()
            return

        ax = self.fig3d.add_subplot(111, projection='3d')
        ax.set_facecolor('#F8FAFC')
        ax.view_init(elev=self.current_elev, azim=self.current_azim)
        
        width = self.spacing * (self.num_g - 1) + 2.0
        
        # Calculate true data bounding box
        x_range = self.L + 4
        y_range = width + 4
        mid_x = self.L / 2
        mid_y = 0
        
        if self.cb_abut.isChecked():
            total_foundation_depth = 15.85
            mid_z = (self.depth - total_foundation_depth) / 2
            z_range = self.depth + total_foundation_depth + 4
        else:
            mid_z = self.depth / 2
            z_range = self.depth + 4
            
        # 1. Apply true limits scaled identically by zoom_factor
        ax.set_xlim(mid_x - (x_range/2 * self.zoom_factor), mid_x + (x_range/2 * self.zoom_factor))
        ax.set_ylim(mid_y - (y_range/2 * self.zoom_factor), mid_y + (y_range/2 * self.zoom_factor))
        ax.set_zlim(mid_z - (z_range/2 * self.zoom_factor), mid_z + (z_range/2 * self.zoom_factor))
        
        # 2. Force 1:1 Aspect Ratio to actual dimensions (Prevents Axis Distortion & Stretching)
        ax.set_box_aspect((x_range, y_range, z_range))
        
        if self.show_grid:
            ax.set_axis_on()
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
        else:
            ax.set_axis_off()
        
        if self.cb_abut.isChecked():
            cap_h = 1.2; col_h = 5.0; pcap_h = 1.5; pile_h = 8.0; z_bear = -0.15
            
            # Place piers 1.0m inwards so they sit undeniably underneath the girders
            bearing_offset = 1.0 
            for px in [bearing_offset, self.L - bearing_offset]:
                for i in range(self.num_g):
                    y_center = -width/2 + 1.0 + (i * self.spacing)
                    self.draw_cylinder_3d(ax, px, y_center, z_bear, 0.15, 0.2, '#38A169')
                
                ax.bar3d(px - 1.0, -width/2 - 0.5, z_bear - cap_h, 2.0, width + 1, cap_h, color='#CBD5E0', edgecolor='grey', shade=True)
                self.draw_cylinder_3d(ax, px, 0, z_bear - cap_h - col_h, col_h, 1.2, '#A0AEC0')
                
                pw = width * 0.6; pl = 4.0; z_pcap_top = z_bear - cap_h - col_h
                ax.bar3d(px - pl/2, -pw/2, z_pcap_top - pcap_h, pl, pw, pcap_h, color='#94A3B8', edgecolor='grey', shade=True)
                
                nx, ny = 4, 4; space_x = (pl - 1.0) / (nx - 1); space_y = (pw - 1.0) / (ny - 1); z_pile_top = z_pcap_top - pcap_h
                for i in range(nx):
                    for j in range(ny):
                        pile_x = px - pl/2 + 0.5 + i * space_x
                        pile_y = -pw/2 + 0.5 + j * space_y
                        self.draw_cylinder_3d(ax, pile_x, pile_y, z_pile_top - pile_h, pile_h, 0.3, '#718096')

        # 3. Segment the Girders and Deck (Fixes Matplotlib Z-Order Sorting Bug)
        segments = max(1, int(self.L / 3.0)) 
        seg_L = self.L / segments
        
        for s in range(segments):
            seg_x = s * seg_L
            
            if self.cb_gird.isChecked():
                tf = self.tf; bf = self.bf; tw = self.tw
                hw = self.depth - (2 * tf)
                for i in range(self.num_g):
                    y_center = -width/2 + 1.0 + (i * self.spacing)
                    ax.bar3d(seg_x, y_center - bf/2, 0, seg_L, bf, tf, color='#1E5A8A', alpha=1.0, edgecolor='#123B63', linewidth=0.3)
                    ax.bar3d(seg_x, y_center - tw/2, tf, seg_L, tw, hw, color='#2C7BB6', alpha=1.0, edgecolor='#123B63', linewidth=0.3)
                    ax.bar3d(seg_x, y_center - bf/2, tf + hw, seg_L, bf, tf, color='#1E5A8A', alpha=1.0, edgecolor='#123B63', linewidth=0.3)

            if self.cb_deck.isChecked():
                deck_thickness = 0.25
                ax.bar3d(seg_x, -width/2, self.depth, seg_L, width, deck_thickness, color='#CBD5E0', alpha=0.9, edgecolor='grey')

        if self.show_dims:
            z_dim = self.depth + 3.0
            y_offset = width/2 + 2.0
            x_offset = -3.0

            ax.plot([0, self.L], [y_offset, y_offset], [z_dim, z_dim], color='#E53E3E', linestyle='-', marker='|', markersize=12, linewidth=2)
            ax.text(self.L/2, y_offset + 0.5, z_dim, f"Span = {self.L} m", color='#E53E3E', ha='center', weight='bold', fontsize=11)
            
            ax.plot([x_offset, x_offset], [-width/2, width/2], [z_dim, z_dim], color='#3182CE', linestyle='-', marker='|', markersize=12, linewidth=2)
            ax.text(x_offset - 1.0, 0, z_dim, f"Deck Width = {width} m", color='#3182CE', ha='center', weight='bold', fontsize=11)

        self.fig3d.subplots_adjust(left=0, right=1, bottom=0, top=1)
        self.canvas3d.draw()