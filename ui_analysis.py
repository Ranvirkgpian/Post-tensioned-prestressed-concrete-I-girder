"""Analysis page: every curve is an engine array (no scaled shapes)."""
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QFrame
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QPushButton
from ui_common import attach_interaction, FullScreenDialog

PLOTS = ["Bending moment", "Shear force", "Deflection", "Concrete stresses", "Prestress force & eccentricity"]


def draw_plot(fig, name, r):
    fig.clear(); f = r["forces"]; x = f["xs"]; ps = r["prestress"]; st = r["stresses"]
    if name == PLOTS[0]:
        ax = fig.add_subplot(111)
        ax.plot(x, f["M_g"], label="Girder self weight"); ax.plot(x, f["M_g"] + f["M_sidl"] + f["M_wc"], label="Dead + SIDL")
        ax.plot(x, f["M_rare"], label="Rare (service) total", color="#DD6B20"); ax.plot(x, f["M_uls"], "r--", label="ULS design")
        ax.set_ylabel("Bending moment per girder (kNm)")
    elif name == PLOTS[1]:
        ax = fig.add_subplot(111)
        ax.plot(x, f["V_g"], label="Self weight"); ax.plot(x, f["V_uls"], "r--", label="ULS design")
        ax.plot(x, f["Ved"], label="Design shear Ved (after prestress)", color="#2F855A")
        ax.plot(x, f["V_cap"], label="Capacity min(VRd,s, VRd,max)", color="#1A365D")
        ax.set_ylabel("Shear force per girder (kN)")
    elif name == PLOTS[2]:
        ax = fig.add_subplot(111)
        for k, lab in [("d_g", "Girder weight"), ("d_pe", "Prestress (camber)"), ("d_ll", "Live load"),
                       ("d_sust", "Sustained incl. creep"), ("d_total", "Total long-term")]:
            ax.plot(x, f[k], label=lab)
        ax.set_ylabel("Deflection (mm, downward +)")
    elif name == PLOTS[3]:
        ax = fig.add_subplot(111)
        for k, lab in [("top_T", "Top @ transfer"), ("bot_T", "Bottom @ transfer"), ("top_rare", "Top @ rare"),
                       ("bot_rare", "Bottom @ rare"), ("bot_qp", "Bottom @ QP")]:
            ax.plot(x, st[k], label=lab)
        ax.axhline(0, color="k", lw=.8); ax.set_ylabel("Stress (MPa, compression +)")
    else:
        ax = fig.add_subplot(111)
        ax.plot(x, ps["Pi"], label="Pi (after transfer)"); ax.plot(x, ps["Pe"], label="Pe (long-term)")
        ax.axhline(ps["P0"], color="r", ls="--", label="P0 (jacking)"); ax.set_ylabel("Force (kN)")
        a2 = ax.twinx(); a2.plot(x, ps["e_x"], "g:", label="Eccentricity e(x)"); a2.set_ylabel("e (m)")
        a2.legend(loc="lower right", fontsize=8)
    ax.set_xlim(0, r["geom"]["L"]); ax.set_xlabel("Distance from support (m)"); ax.grid(alpha=.3)
    ax.legend(fontsize=8, loc="best"); ax.set_title(name)
    fig.tight_layout()


class AnalysisPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        lay = QVBoxLayout(self)
        top = QHBoxLayout(); self.combo = QComboBox(); self.combo.addItems(PLOTS)
        self.combo.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel("Diagram:")); top.addWidget(self.combo); top.addWidget(QLabel("<i>wheel = zoom</i>")); top.addStretch()
        fb = QPushButton("⛶ Full screen"); fb.clicked.connect(self.full_screen); top.addWidget(fb); lay.addLayout(top)
        self.fig = Figure(figsize=(9, 5)); self.canvas = Canvas(self.fig); attach_interaction(self.canvas); lay.addWidget(self.canvas, 1)
        self.info = QLabel(); self.info.setWordWrap(True)
        self.info.setStyleSheet("background:white;border:1px solid #E2E8F0;padding:10px;font-size:12px;")
        lay.addWidget(self.info)

    def full_screen(self):
        r = self.main.results
        if r is None: return
        name = self.combo.currentText()
        dlg = FullScreenDialog(self.main, name, lambda fig: draw_plot(fig, name, r))
        dlg.setStyleSheet(self.main.styleSheet()); dlg.showFullScreen(); dlg.exec()

    def refresh(self):
        r = self.main.results
        if r is None: return
        draw_plot(self.fig, self.combo.currentText(), r); self.canvas.draw_idle()
        g, l, p, k = r["geom"], r["loads"], r["prestress"], r["kpi"]
        self.info.setText(
            f"<b>Model:</b> L = {g['L']:.2f} m, {g['n_girders']} girders @ {g['spacing']:.2f} m, deck width {g['W']:.2f} m "
            f"(carriageway {g['Wc']:.2f} m) | governing vehicle: {l['gov_vehicle']}, DF = {l['df']:.3f}, impact = {l['impact']:.3f} | "
            f"w(girder+slab) = {l['w_g_total']:.2f} kN/m, SIDL = {l['w_sidl']+l['w_wc']:.2f} kN/m | "
            f"cables: {p['nc']} × {p['strands_per_cable']} strands{' (auto)' if p['auto'] else ''}, P0 = {p['P0']:.0f} kN, "
            f"Pe,mid = {p['Pe_mid']:.0f} kN, total loss {p['total_loss_pct']:.1f}% | "
            f"Mu = {k['m_uls']:.0f} kNm at x = {k['x_m']:.2f} m, Vu(support) = {k['v_uls']:.0f} kN")
