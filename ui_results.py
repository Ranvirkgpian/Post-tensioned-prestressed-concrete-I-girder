"""Results page: KPIs and the full checks table, all from engine results."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QTextEdit)
from PySide6.QtGui import QColor


class ResultsPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        lay = QVBoxLayout(self)
        self.banner = QLabel(); self.banner.setStyleSheet("font-weight:bold;font-size:14px;padding:8px;border-radius:4px;")
        lay.addWidget(self.banner)
        self.kpi = QHBoxLayout(); lay.addLayout(self.kpi)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Check", "Demand", "Limit", "Unit", "Utilisation", "Status", "Clause / location", "Calculation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellClicked.connect(self.show_calc)
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self.show_calc(r))
        lay.addWidget(self.table, 2)
        self.detail = QTextEdit(); self.detail.setReadOnly(True)
        self.detail.setStyleSheet("background:#FFFFFF;border:1px solid #E2E8F0;padding:6px;")
        self.detail.setPlaceholderText("Click a row in the table to see its calculation details.")
        lay.addWidget(self.detail, 3)
        self.notes = QTextEdit(); self.notes.setReadOnly(True); lay.addWidget(self.notes, 1)

    def _kpi(self, title, val):
        f = QFrame(); f.setStyleSheet("background:white;border:1px solid #E2E8F0;border-radius:6px;")
        l = QVBoxLayout(f); a = QLabel(title); a.setStyleSheet("color:#718096;font-size:11px;border:none;")
        b = QLabel(val); b.setStyleSheet("color:#123B63;font-size:18px;font-weight:bold;border:none;")
        l.addWidget(a); l.addWidget(b); self.kpi.addWidget(f)

    def show_calc(self, row, _col=0):
        r = self.main.results
        if r is None or row >= len(r["checks"]): return
        c = r["checks"][row]
        ok = c["status"] == "PASS"
        col, bg = ("#22543D", "#C6F6D5") if ok else ("#822727", "#FED7D7")
        util = "-" if c["util"] is None else f"{c['util']*100:.1f} %"
        h = ["<div style='font-family:Segoe UI,Arial,sans-serif;font-size:13px;color:#2D3748;'>",
             f"<div style='font-size:16px;font-weight:bold;color:#123B63;'>{c['name']} "
             f"<span style='background:{bg};color:{col};font-size:12px;padding:2px 8px;'>&nbsp;{c['status']}&nbsp;</span></div>",
             f"<div style='color:#718096;margin-bottom:6px;'>{c['clause']}" + (f" &nbsp;|&nbsp; {c['where']}" if c["where"] else "") + "</div>",
             "<table cellspacing='0' cellpadding='5' style='border:1px solid #E2E8F0;margin-bottom:8px;'><tr style='background:#F8FAFC;'>"
             "<th align='left'>Demand</th><th align='left'>Limit</th><th align='left'>Utilisation</th></tr>"
             f"<tr><td>{c['demand']:,.2f} {c['unit']}</td><td>{c['limit']:,.2f} {c['unit']}</td><td>{util}</td></tr></table>"]
        for kind, txt in c.get("calc", []):
            txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if kind == "h": h.append(f"<div style='color:#123B63;font-weight:bold;margin-top:8px;border-bottom:1px solid #E2E8F0;'>{txt}</div>")
            elif kind == "t": h.append(f"<div style='color:#4A5568;margin:2px 0;'>{txt}</div>")
            elif kind == "f": h.append(f"<div style='margin:2px 0 2px 12px;font-style:italic;color:#2B6CB0;'>{txt}</div>")
            elif kind == "s": h.append(f"<div style='margin:2px 0 2px 12px;font-family:Consolas,monospace;'>{txt}</div>")
            else: h.append(f"<div style='margin:2px 0 2px 12px;font-weight:bold;'>{txt}</div>")
        h.append("</div>")
        self.detail.setHtml("".join(h))

    def refresh(self):
        r = self.main.results
        if r is None: return
        while self.kpi.count():
            w = self.kpi.takeAt(0).widget()
            if w: w.deleteLater()
        k, p, fl, sh, d = r["kpi"], r["prestress"], r["flexure"], r["shear"], r["deflection"]
        for t, v in [("Design moment Mu", f"{k['m_uls']:.0f} kNm"), ("Moment capacity", f"{fl['Mu_cap']:.0f} kNm"),
                     ("Design shear (support)", f"{k['v_uls']:.0f} kN"), ("P0 / Pe,mid", f"{p['P0']:.0f} / {p['Pe_mid']:.0f} kN"),
                     ("Total loss", f"{p['total_loss_pct']:.1f} %"), ("Long-term deflection", f"{d['total']:.1f} mm"),
                     ("Reaction (ULS)", f"{r['reactions']['uls']:.0f} kN")]:
            self._kpi(t, v)
        ch = r["checks"]; nf = sum(c["status"] == "FAIL" for c in ch)
        if nf == 0:
            self.banner.setText(f"All {len(ch)} checks pass for the current inputs."); self.banner.setStyleSheet(self.banner.styleSheet() + "background:#C6F6D5;color:#22543D;")
        else:
            names = ", ".join(c["name"] for c in ch if c["status"] == "FAIL")
            self.banner.setText(f"{nf} of {len(ch)} checks FAIL: {names}"); self.banner.setStyleSheet(self.banner.styleSheet() + "background:#FED7D7;color:#822727;")
        self.table.setRowCount(len(ch))
        for i, c in enumerate(ch):
            u = c["util"]
            vals = [c["name"], f"{c['demand']:.2f}", f"{c['limit']:.2f}", c["unit"], "-" if u is None else f"{u*100:.1f} %",
                    c["status"], c["clause"] + (f"  [{c['where']}]" if c["where"] else "")]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j == 5: it.setForeground(QColor("#2F855A" if v == "PASS" else "#C53030"))
                self.table.setItem(i, j, it)
            self.table.setItem(i, 7, QTableWidgetItem("Show calculation ▸"))
            self.table.item(i, 7).setForeground(QColor("#3182CE"))
        txt = "".join(f"WARNING: {w}\n" for w in r["warnings"])
        txt += "\nAssumptions to verify against the codes:\n" + "\n".join(f"- {a}" for a in r.get("assumptions", []))
        self.notes.setPlainText(txt)
        self.detail.clear()
        if ch: self.table.selectRow(0); self.show_calc(0)
