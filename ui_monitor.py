"""Monitoring & AI page: inspection, NDT, sensors, vibration, synthetic data, ML, maintenance."""
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from ui_common import attach_interaction, FullScreenDialog
import bridge_monitor as bm

PLOTS = ["Healthy baseline", "Visual inspection scheme", "NDT results", "Sensor layout", "Acceleration & FFT",
         "Frequency shift", "Feature trends", "AI/ML assessment", "Feature distributions & anomaly scores", "Health monitoring timeline", "Maintenance decision"]
COL = {"Healthy": "#2F855A", "Minor": "#D69E2E", "Moderate": "#DD6B20", "Severe": "#C53030"}


def get_monitor(r):
    if r.get("_monitor") is None: r["_monitor"] = bm.run_monitoring(r)
    return r["_monitor"]


def _table(ax, rows, header, widths=None, fs=8.5, fill=False):
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=header, cellLoc="left", colWidths=widths, bbox=[0, 0, 1, 1]) if fill else ax.table(cellText=rows, colLabels=header, loc="upper center", cellLoc="left", colWidths=widths)
    t.auto_set_font_size(False); t.set_fontsize(fs)
    if not fill: t.scale(1, 1.55)
    for (i, j), c in t.get_celld().items():
        c.set_edgecolor("#CBD5E0")
        if i == 0: c.set_facecolor("#1A365D"); c.set_text_props(color="white", weight="bold")
        elif i % 2 == 0: c.set_facecolor("#F1F5F9")


def draw_monitor(fig, name, r, state="Moderate"):
    fig.clear(); m = get_monitor(r); b = m["b"]; L = b["L"]
    if name == PLOTS[0]:
        ax = fig.add_subplot(111); ax.set_title("Healthy baseline (design condition) - reference for all later comparisons", fontsize=10)
        rows = [("Effective prestress Pe (midspan)", f"{b['Pe']:,.0f} kN"), ("Soffit stress, rare combination", f"{b['sig_bot']:.2f} MPa (compression)"),
                ("Midspan deflection (long-term)", f"{b['delta']:.1f} mm"), ("Prestress camber at midspan", f"{b['camber']:.1f} mm"),
                ("Natural frequency f1 / f2 / f3", f"{b['f'][0]:.2f} / {b['f'][1]:.2f} / {b['f'][2]:.2f} Hz"),
                ("Flexural stiffness EI (composite)", f"{b['EI']/1e9:,.1f} GN·m²"), ("Dead mass per girder", f"{b['mass']:,.0f} kg/m"),
                ("Rebound number / UPV (assumed healthy)", f"{b['rebound']:.0f} / {b['upv']:.2f} km/s"), ("Crack width / condition score", "0 mm / 10 of 10")]
        _table(ax, rows, ["Quantity", "Baseline value"], [0.5, 0.5], fs=9.5)
    elif name == PLOTS[1]:
        ax = fig.add_subplot(111); ax.set_title("Inspection record: Bridge → Span → Component → Location → Observation", fontsize=10)
        _table(ax, [(a, c_, d) for a, c_, d in m["inspection"]], ["Component", "Typical observations", "Interval"], [0.27, 0.5, 0.23], fs=8)
    elif name == PLOTS[2]:
        ax = fig.add_subplot(121); ax2 = fig.add_subplot(122); w = 0.2; x = np.arange(len(m["ndt"]))
        for k, st in enumerate(bm.STATES):
            ax.bar(x + (k - 1.5) * w, [row[st][0] for row in m["ndt"]], w, color=COL[st], label=st)
            ax2.bar(x + (k - 1.5) * w, [row[st][1] for row in m["ndt"]], w, color=COL[st], label=st)
        for a_, t_, u in ((ax, "Rebound number", "R"), (ax2, "UPV", "km/s")):
            a_.set_xticks(x); a_.set_xticklabels([f"{row['loc']}\nx={row['x']:.1f} m" for row in m["ndt"]], fontsize=8); a_.set_title(t_); a_.set_ylabel(u); a_.grid(axis="y", alpha=.3)
        ax2.set_ylim(2.5, 4.6); ax.set_ylim(15, 40); ax.legend(fontsize=8, ncol=2); fig.suptitle("Synthetic NDT data along girder G1 (damage concentrated near midspan)", fontsize=10)
    elif name == PLOTS[3]:
        ax = fig.add_subplot(111); ax.plot([0, L], [0, 0], "k-", lw=6, alpha=.35); ax.plot([0, L], [-.15, -.15], "k^", ms=10)
        mk = {"A": ("o", "#2B6CB0"), "D": ("s", "#2F855A"), "S": ("D", "#DD6B20"), "P": ("v", "#6B46C1")}
        seen = {}
        for i, (sid, nm, x, wh, fsm) in enumerate(m["sensors"]):
            mm, cc = mk[sid[0]]; ax.plot(x, 0.0, mm, color=cc, ms=11); k = seen.get(round(x, 2), 0); seen[round(x, 2)] = k + 1
            ax.annotate(sid, (x, 0), (x + 0.0, 0.25 + 0.22 * k), ha="center", fontsize=9, arrowprops=dict(arrowstyle="-", color="#718096"))
        ax.set_ylim(-.5, 1.1); ax.set_xlim(-1, L + 1); ax.set_yticks([]); ax.set_xlabel("Distance along span (m)"); ax.set_title("Instrumentation layout (girder elevation)", fontsize=10)
        rows = [(sid, nm, f"{x:.1f}", wh, fsm) for sid, nm, x, wh, fsm in m["sensors"]]
        ax.set_position([0.06, 0.60, 0.88, 0.32]); tax = fig.add_axes([0.06, 0.03, 0.88, 0.48]); _table(tax, rows, ["ID", "Sensor", "x (m)", "Location", "Sampling"], [.07, .33, .1, .33, .17], fs=8, fill=True)
    elif name == PLOTS[4]:
        t, a, fr, A = m["rec"][state]; h = m["rec"]["Healthy"]
        ax1 = fig.add_subplot(211); ax1.plot(t, a, lw=.6, color=COL[state]); ax1.set_xlabel("Time (s)"); ax1.set_ylabel("a(t) (m/s²)")
        ax1.set_title(f"Synthetic midspan acceleration - {state} state, a_RMS = {np.sqrt(np.mean(a**2)):.4f} m/s²", fontsize=10); ax1.grid(alpha=.3)
        ax2 = fig.add_subplot(212); ax2.plot(h[2], h[3], color=COL["Healthy"], lw=1, label="Healthy"); ax2.plot(fr, A, color=COL[state], lw=1, label=state)
        for k, fk in enumerate(b["f"]): ax2.axvline(fk, color="#2F855A", ls=":", lw=.8)
        ax2.set_xlim(0, 40); ax2.set_xlabel("Frequency (Hz)"); ax2.set_ylabel("|A(f)|"); ax2.set_title("FFT spectrum (dotted = healthy f1, f2, f3)", fontsize=10); fig.subplots_adjust(hspace=.55); ax2.legend(fontsize=8); ax2.grid(alpha=.3)
    elif name == PLOTS[5]:
        ax = fig.add_subplot(111); x = np.arange(3); w = .2
        for k, st in enumerate(bm.STATES):
            ax.bar(x + (k - 1.5) * w, [m["rep"][st]["f"][i] for i in range(3)], w, color=COL[st], label=st)
            for i in range(3): ax.text(x[i] + (k - 1.5) * w, m["rep"][st]["f"][i] + .2, f"{m['rep'][st]['f'][i]:.2f}", ha="center", fontsize=7)
        ax.set_xticks(x); ax.set_xticklabels(["f1", "f2", "f3"]); ax.set_ylabel("Natural frequency (Hz)"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3)
        ax.set_title("Natural frequencies fall as stiffness and prestress are lost (f ∝ √EI)", fontsize=10)
    elif name == PLOTS[6]:
        ks = [("δ_max (mm)", lambda s: m["rep"][s]["delta"]), ("ε_soffit (µε)", lambda s: m["rep"][s]["eps"]), ("Pe (kN)", lambda s: m["rep"][s]["Pe"]),
              ("UPV (km/s)", lambda s: m["rep"][s]["upv"]), ("Rebound no.", lambda s: m["rep"][s]["rebound"]), ("Condition score", lambda s: m["rep"][s]["score"])]
        for i, (t_, fn) in enumerate(ks):
            ax = fig.add_subplot(2, 3, i + 1); v = [fn(s) for s in bm.STATES]; ax.plot(bm.STATES, v, "o-", color="#1A365D")
            for s_, y_ in zip(bm.STATES, v): ax.plot(s_, y_, "o", color=COL[s_], ms=8)
            ax.set_title(t_, fontsize=9); ax.tick_params(labelsize=7); ax.grid(alpha=.3)
        fig.suptitle("Response and measurement features versus condition state", fontsize=10)
    elif name == PLOTS[7]:
        ax = fig.add_subplot(131); cm = m["cm"]; ax.imshow(cm, cmap="Blues")
        for i in range(4):
            for j in range(4): ax.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=9)
        ax.set_xticks(range(4)); ax.set_yticks(range(4)); ax.set_xticklabels([s[:4] for s in bm.STATES], fontsize=7); ax.set_yticklabels([s[:4] for s in bm.STATES], fontsize=7)
        ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(f"Classifier, test acc. {m['acc']*100:.0f} %", fontsize=9)
        ax = fig.add_subplot(132)
        for ci, st in enumerate(bm.STATES): ax.scatter(m["pcs"][m["y"] == ci, 0], m["pcs"][m["y"] == ci, 1], s=10, color=COL[st], label=st, alpha=.7)
        ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.set_title("Feature space (PCA)", fontsize=9); ax.legend(fontsize=7)
        ax = fig.add_subplot(133); o = np.argsort(m["imp"]); ax.barh([bm.FEATURES[i] for i in o], m["imp"][o], color="#2B6CB0"); ax.tick_params(labelsize=7); ax.set_title("Feature importance", fontsize=9)
        fig.suptitle(f"Anomaly detector: detection {m['tpr']*100:.0f} %, false alarms {m['fpr']*100:.0f} % | severity regression R² = {m['r2']:.2f} (synthetic data)", fontsize=9)
    elif name == PLOTS[8]:
        for i in range(8):
            ax = fig.add_subplot(3, 4, i + 1); data = [m["X"][m["y"] == k, i] for k in range(4)]
            bp = ax.boxplot(data, patch_artist=True, widths=.6, flierprops=dict(markersize=2))
            for patch, st in zip(bp["boxes"], bm.STATES): patch.set_facecolor(COL[st]); patch.set_alpha(.75)
            ax.set_xticklabels([s_[:3] for s_ in bm.STATES], fontsize=6); ax.set_title(bm.FEATURES[i], fontsize=7.5); ax.tick_params(labelsize=6); ax.grid(alpha=.3)
        ax = fig.add_subplot(3, 4, (9, 12)); da = m["dist_all"]; bins = np.linspace(0, max(da["damaged"].max(), m["thr"] * 1.2), 40)
        ax.hist(da["healthy"], bins, color=COL["Healthy"], alpha=.8, label="Healthy"); ax.hist(da["damaged"], bins, color=COL["Severe"], alpha=.6, label="Damaged")
        ax.axvline(m["thr"], color="k", ls="--", label=f"Alarm threshold = {m['thr']:.1f}"); ax.set_xlabel("Mahalanobis distance from healthy baseline"); ax.set_ylabel("Samples"); ax.legend(fontsize=7); ax.set_title("Anomaly score distribution", fontsize=9)
        fig.subplots_adjust(hspace=.55, wspace=.4)
    elif name == PLOTS[9]:
        T = m["timeline"]; y_ = T["yrs"]
        ax = fig.add_subplot(311); ax.plot(y_, T["hi"], color="#1A365D", lw=1.6); ax.fill_between(y_, 0, T["hi"], color="#BEE3F8", alpha=.5)
        for lv, c in ((75, "#D69E2E"), (50, "#DD6B20"), (25, "#C53030")): ax.axhline(lv, color=c, ls=":", lw=.8)
        ax.set_ylabel("Health index (0-100)"); ax.set_ylim(0, 105); ax.set_title("AI health monitoring over 30 years of synthetic monthly data (damage progresses with time)", fontsize=10); ax.grid(alpha=.3)
        ax = fig.add_subplot(312, sharex=ax)
        for k, st in enumerate(bm.STATES): ax.plot(y_, T["probs"][:, k], color=COL[st], lw=1.1, label=st)
        ax.set_ylabel("Class probability"); ax.legend(fontsize=7, ncol=4, loc="center left"); ax.grid(alpha=.3)
        ax = fig.add_subplot(313, sharex=ax); ax.plot(y_, T["dist"], color="#6B46C1", lw=1); ax.axhline(m["thr"], color="k", ls="--", lw=.9); ax.set_ylabel("Anomaly score"); ax.set_xlabel("Years in service"); ax.grid(alpha=.3)
        a2 = ax.twinx(); a2.plot(y_, T["f1"], color="#2B6CB0", lw=.9); a2.set_ylabel("f1 (Hz)", color="#2B6CB0", fontsize=8)
        for lab, yr in T["milestones"][:4]:
            if yr is not None:
                for a in fig.axes[:3]: a.axvline(yr, color="#718096", ls=":", lw=.7)
        fig.subplots_adjust(hspace=.35)
    else:
        ax = fig.add_subplot(111); ax.axis("off"); d = m["decision"]; c = m["current"]
        ax.set_title("Condition assessment → maintenance decision", fontsize=11)
        steps = [("Condition assessment", f"AI/ML state: {c['pred']} (p = {c['prob'].max():.2f})\nAnomaly: {'YES' if d['anomaly'] else 'no'} | f1 shift {d['f1_shift']:.1f} % | Pe left {d['Pe_remaining']:.0f} %"),
                 ("Routine monitoring or detailed investigation", d["action"]), ("Maintenance / repair", d["detail"]), ("Reinspection and monitoring", f"Urgency: {d['urgency']}")]
        for i, (h, t_) in enumerate(steps):
            y = .92 - i * .25; ax.text(.5, y, h + "\n" + t_, ha="center", va="center", fontsize=8.5, wrap=True, transform=ax.transAxes,
                                       bbox=dict(boxstyle="round,pad=.5", fc="#EBF4FF" if i != 3 else "#FEF3C7", ec="#2B6CB0"))
            if i < 3: ax.annotate("", (.5, y - .21), (.5, y - .13), xycoords="axes fraction", arrowprops=dict(arrowstyle="->", color="#2B6CB0", lw=1.5))


class MonitorPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        lay = QVBoxLayout(self); top = QHBoxLayout()
        self.combo = QComboBox(); self.combo.addItems(PLOTS); self.combo.currentIndexChanged.connect(self.refresh)
        self.state = QComboBox(); self.state.addItems(bm.STATES); self.state.setCurrentText("Moderate"); self.state.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel("View:")); top.addWidget(self.combo); top.addWidget(QLabel("Condition (time history):")); top.addWidget(self.state); top.addStretch()
        fb = QPushButton("⛶ Full screen"); fb.clicked.connect(self.full_screen); top.addWidget(fb); lay.addLayout(top)
        self.fig = Figure(figsize=(9, 5)); self.canvas = Canvas(self.fig); attach_interaction(self.canvas); lay.addWidget(self.canvas, 1)
        self.info = QLabel(); self.info.setWordWrap(True); self.info.setStyleSheet("background:white;border:1px solid #E2E8F0;padding:10px;font-size:12px;"); lay.addWidget(self.info)

    def full_screen(self):
        r = self.main.results
        if r is None: return
        n, s = self.combo.currentText(), self.state.currentText()
        dlg = FullScreenDialog(self.main, n, lambda fig: draw_monitor(fig, n, r, s)); dlg.setStyleSheet(self.main.styleSheet()); dlg.showFullScreen(); dlg.exec()

    def refresh(self):
        r = self.main.results
        if r is None: return
        draw_monitor(self.fig, self.combo.currentText(), r, self.state.currentText()); self.canvas.draw_idle()
        m = get_monitor(r); d = m["decision"]
        self.info.setText(f"<b>Synthetic study</b> ({m['n']} samples, {m['n_train']} train / {m['n']-m['n_train']} test; deterioration values are assumed). "
                          f"Baseline f1 = {m['b']['f'][0]:.2f} Hz | classifier accuracy {m['acc']*100:.0f} % | anomaly detection {m['tpr']*100:.0f} % at {m['fpr']*100:.0f} % false alarms | "
                          f"<b>Demonstration assessment: {m['current']['pred']} → {d['action']}</b>")
