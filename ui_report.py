"""Report page: PDF / CSV / TXT written from engine results only."""
import csv
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel


def build_text(r, name=""):
    g, l, p, f, s, d = r["geom"], r["loads"], r["prestress"], r["flexure"], r["shear"], r["deflection"]
    L = [f"PSC I-GIRDER BRIDGE DESIGN REPORT  {name}", "=" * 70, "",
         f"Span {g['L']:.2f} m | {g['n_girders']} girders @ {g['spacing']:.2f} m | deck {g['W']:.2f} m | depth {g['depth']:.2f} m", ""]
    for w in r["warnings"]: L.append(f"WARNING: {w}")
    L += ["", "CHECK SUMMARY", "-" * 70]
    for c in r["checks"]:
        u = "-" if c["util"] is None else f"{c['util']*100:.1f}%"
        L.append(f"{c['status']:4s} {c['name']:38s} {c['demand']:10.2f} / {c['limit']:10.2f} {c['unit']:4s} {u:>7s}  {c['clause']}")
    L = L[:4] + ["DESCRIPTION", "-" * 70] + describe(r) + [""] + L[4:]
    L += ["", "STEP-BY-STEP CALCULATIONS", "-" * 70]
    for n_, c in enumerate(r["checks"], 1):
        L += ["", f"{n_}. {c['name']}  [{c['status']}]"]
        for kind, txt in c.get("calc", []):
            L.append(("   " + txt) if kind != "h" else ("  " + txt))
    L += ["", "GLOBAL NOTES", "-" * 70]
    for st in r["steps"]:
        L += [st["title"], f"  Given        : {st['given']}", f"  Formula      : {st['formula']}",
              f"  Substitution : {st['substitution']}", f"  Result       : {st['result']}",
              f"  Verification : {st['verification']}   [{st['status']}]", ""]
    L += ["ASSUMPTIONS TO VERIFY"] + [f"- {a}" for a in r["assumptions"]]
    return "\n".join(L)


def describe(r, meta=None):
    """Plain-language description generated from the analysis results."""
    g, l, p, f, s, d, i = r["geom"], r["loads"], r["prestress"], r["flexure"], r["shear"], r["deflection"], r["inputs"]
    ch = r["checks"]; nf = [c["name"] for c in ch if c["status"] == "FAIL"]
    t = [f"The structure is a simply supported, post-tensioned prestressed concrete (PSC) I-girder bridge with an effective span of "
         f"{g['L']:.2f} m. The deck is {g['W']:.2f} m wide and carries {i['n_lanes']} traffic lanes of {i['lane_w']:.1f} m "
         f"({g['Wc']:.2f} m carriageway), a {i['footpath_w']:.1f} m footpath and a {i['barrier_w']:.1f} m crash barrier on each side. "
         f"It is supported on {g['n_girders']} precast I-girders at {g['spacing']:.2f} m spacing, each {g['depth']:.2f} m deep, "
         f"carrying a {i['slab_t']*1000:.0f} mm cast-in-situ RCC deck slab and {i['n_diaphragms']} cross diaphragms.",
         f"Girders use M{i['fck']:.0f} concrete, Fe{i['fy']:.0f} reinforcement and {i['fpk']:.0f} MPa strands. Prestress is provided by "
         f"{p['nc']} post-tensioned cables of {p['strands_per_cable']} strands ({p['Aps_mm2']:,.0f} mm²), "
         f"{'sized automatically' if p['auto'] else 'as specified'}, jacked to {p['sigma_j']:.0f} MPa (P0 = {p['P0']:,.0f} kN). "
         f"After friction, anchorage slip, elastic shortening, creep, shrinkage and relaxation the effective force at midspan is "
         f"{p['Pe_mid']:,.0f} kN, a total loss of {p['total_loss_pct']:.1f} %.",
         f"Live load is taken as {l['gov_vehicle']} with a worst-girder distribution factor of {l['df']:.3f} and an impact factor of "
         f"{l['impact']:.3f}. The ultimate design moment at midspan is {f['Mu']:,.0f} kNm against a capacity of {f['Mu_cap']:,.0f} kNm; "
         f"the critical design shear is {s['Ved']:,.0f} kN against {min(s['VRd_s'], s['VRd_max']):,.0f} kN. "
         f"The long-term midspan deflection is {d['total']:.1f} mm (limit {d['lim_total']:.0f} mm)."]
    t.append(f"Of {len(ch)} design checks, {len(ch)-len(nf)} pass" + (f" and {len(nf)} fail: {', '.join(nf)}. The failing check(s) need a design change "
             "(for example staged stressing, a higher strength at transfer, or a larger bottom flange)." if nf else ". All requirements are satisfied for the inputs given."))
    return t


def input_tables(r):
    i, g = r["inputs"], r["geom"]
    return [("Span and deck", [("Effective span", f"{g['L']:.2f} m"), ("Deck width", f"{g['W']:.2f} m"), ("Carriageway", f"{g['Wc']:.2f} m"),
             ("Lanes", f"{i['n_lanes']} x {i['lane_w']:.1f} m"), ("Footpath / barrier", f"{i['footpath_w']:.1f} m / {i['barrier_w']:.1f} m"),
             ("Girders / spacing", f"{g['n_girders']} @ {g['spacing']:.2f} m"), ("Overhang", f"{g['overhang']:.2f} m"),
             ("Slab / haunch", f"{i['slab_t']*1000:.0f} mm / {i['haunch']*1000:.0f} mm"), ("Diaphragms", f"{i['n_diaphragms']} x {i['dia_t']*1000:.0f} mm")]),
            ("Girder section", [("Depth", f"{i['depth']*1000:.0f} mm"), ("Top flange", f"{i['bt']*1000:.0f} x {i['tf']*1000:.0f} mm"),
             ("Web", f"{i['tw']*1000:.0f} mm"), ("Bottom flange", f"{i['bb']*1000:.0f} x {i['tb']*1000:.0f} mm"),
             ("Area A", f"{r['section']['A']:.4f} m²"), ("Centroid from soffit", f"{r['section']['yb']*1000:.0f} mm"),
             ("Inertia I", f"{r['section']['I']:.4f} m⁴"), ("Zb / Zt", f"{r['section']['Zb']:.4f} / {r['section']['Zt']:.4f} m³"),
             ("Composite Ic", f"{r['section']['Ic']:.4f} m⁴")]),
            ("Materials", [("Girder concrete fck", f"{i['fck']:.0f} MPa"), ("Deck concrete fck", f"{i['deck_fck']:.0f} MPa"),
             ("Ecm (girder)", f"{r['section']['Ecm']:,.0f} MPa"), ("Reinforcement fy", f"{i['fy']:.0f} MPa"),
             ("Strand fpk", f"{i['fpk']:.0f} MPa"), ("Strand area", f"{i['strand_area']:.0f} mm²")]),
            ("Prestressing", [("Cables x strands", f"{r['prestress']['nc']} x {r['prestress']['strands_per_cable']}"),
             ("Aps", f"{r['prestress']['Aps_mm2']:,.0f} mm²"), ("Jacking stress", f"{r['prestress']['sigma_j']:.0f} MPa"),
             ("μ / k", f"{i['mu']} / {i['k_wobble']}"), ("Anchorage draw-in", f"{i['slip']*1000:.1f} mm"),
             ("Creep φ / shrinkage", f"{i['creep_phi']} / {i['shrinkage']:.1e}"), ("Relaxation (1000 h)", f"{i['relax1000']} %")]),
            ("Loads", [("Self weight + slab", f"{r['loads']['w_g_total']:.2f} kN/m"), ("SIDL", f"{r['loads']['w_sidl']:.2f} kN/m"),
             ("Wearing coat", f"{r['loads']['w_wc']:.2f} kN/m"), ("Footpath live", f"{r['loads']['w_fpll']:.2f} kN/m"),
             ("Governing vehicle", r["loads"]["gov_vehicle"]), ("Distribution factor", f"{r['loads']['df']:.3f}"), ("Impact factor", f"{r['loads']['impact']:.3f}")])]


def write_pdf(path, r, name="", meta=None):
    import io, datetime
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image,
                                    PageBreak, KeepTogether, CondPageBreak)
    import os, matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from ui_analysis import draw_plot, PLOTS
    import ui_3d_model as U
    meta = meta or {}
    fd = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    for nm, fn in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                   ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf"), ("DVM-B", "DejaVuSansMono-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(nm, os.path.join(fd, fn)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")
    NAVY, BLUE, GREY, LINE = colors.HexColor("#123B63"), colors.HexColor("#2B6CB0"), colors.HexColor("#4A5568"), colors.HexColor("#CBD5E0")
    GOOD, BAD = colors.HexColor("#2F855A"), colors.HexColor("#C53030")
    st = dict(
        title=ParagraphStyle("t", fontName="DV-B", fontSize=22, leading=27, textColor=NAVY),
        sub=ParagraphStyle("s", fontName="DV", fontSize=11, leading=15, textColor=GREY),
        h1=ParagraphStyle("h1", fontName="DV-B", fontSize=14, leading=18, textColor=NAVY, spaceBefore=10, spaceAfter=6),
        h2=ParagraphStyle("h2", fontName="DV-B", fontSize=10.5, leading=14, textColor=BLUE, spaceBefore=6, spaceAfter=3),
        body=ParagraphStyle("b", fontName="DV", fontSize=9, leading=13.5, alignment=TA_JUSTIFY, spaceAfter=5),
        cell=ParagraphStyle("c", fontName="DV", fontSize=8, leading=10.5),
        cellb=ParagraphStyle("cb", fontName="DV-B", fontSize=8, leading=10.5),
        head=ParagraphStyle("hd", fontName="DV-B", fontSize=8, leading=10.5, textColor=colors.white),
        lab=ParagraphStyle("l", fontName="DV", fontSize=6.5, leading=9, textColor=colors.HexColor("#718096")),
        note=ParagraphStyle("n", fontName="DV", fontSize=8, leading=11, textColor=GREY),
        form=ParagraphStyle("f", fontName="DV-I", fontSize=8.5, leading=12, textColor=colors.HexColor("#2C5282")),
        sub_=ParagraphStyle("sb", fontName="DVM", fontSize=7.6, leading=11),
        res=ParagraphStyle("r", fontName="DV-B", fontSize=8.5, leading=12, textColor=NAVY),
        sec=ParagraphStyle("sc", fontName="DV-B", fontSize=8.5, leading=12, textColor=NAVY))
    P = lambda t, s="body": Paragraph(escape(str(t)), st[s])
    today = datetime.date.today().strftime("%d %B %Y")
    pname = meta.get("name") or name or "PSC Bridge"

    def deco(c, d):
        c.saveState(); w, h = A4
        c.setStrokeColor(LINE); c.line(18 * mm, h - 14 * mm, w - 18 * mm, h - 14 * mm); c.line(18 * mm, 14 * mm, w - 18 * mm, 14 * mm)
        c.setFont("DV", 7.5); c.setFillColor(GREY)
        c.drawString(18 * mm, h - 11.5 * mm, f"{pname} - Design Report"); c.drawRightString(w - 18 * mm, h - 11.5 * mm, "IRC:6-2017 / IRC:112-2011")
        c.drawString(18 * mm, 9.5 * mm, f"{meta.get('designer', '')}   |   {today}"); c.drawRightString(w - 18 * mm, 9.5 * mm, f"Page {d.page}")
        c.restoreState()
    doc = BaseDocTemplate(path, pagesize=A4, title=f"{pname} - Design Report", leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=19 * mm)
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
    W = doc.width
    def tbl(rows, widths, head=True, extra=()):
        t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
        sty = [("GRID", (0, 0), (-1, -1), .3, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("ROWBACKGROUNDS", (0, 1 if head else 0), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")])]
        if head: sty += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
        t.setStyle(TableStyle(sty + list(extra))); return t

    ch = r["checks"]; nfail = sum(c["status"] == "FAIL" for c in ch); g = r["geom"]
    E = [Spacer(1, 6), P("PSC I-Girder Bridge", "title"), P("Design and Analysis Report", "title"), Spacer(1, 6),
         P(f"{pname}", "sub"), P(f"Prepared by: {meta.get('designer', '-')}      Date: {today}", "sub"),
         P(f"Design basis: {meta.get('code', 'IRC:6-2017, IRC:112-2011')}", "sub"), Spacer(1, 10)]
    col = BAD if nfail else GOOD
    ban = Table([[Paragraph(f"<b>{'%d of %d checks FAIL' % (nfail, len(ch)) if nfail else 'All %d checks PASS' % len(ch)}</b>", ParagraphStyle("bn", fontName="DV-B", fontSize=10, textColor=colors.white))]], colWidths=[W])
    ban.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    E += [ban, Spacer(1, 8), P("1. Description", "h1")]
    if meta.get("description"): E += [P(meta["description"])]
    for para in describe(r): E.append(P(para))
    # key results
    k, fl = r["kpi"], r["flexure"]
    kp = [[P("Design moment Mu", "lab"), P("Moment capacity", "lab"), P("Design shear", "lab"), P("Pe at midspan", "lab"), P("Total deflection", "lab")],
          [P(f"{k['m_uls']:,.0f} kNm", "res"), P(f"{fl['Mu_cap']:,.0f} kNm", "res"), P(f"{k['v_uls']:,.0f} kN", "res"),
           P(f"{r['prestress']['Pe_mid']:,.0f} kN", "res"), P(f"{r['deflection']['total']:.1f} mm", "res")]]
    kt = Table(kp, colWidths=[W / 5] * 5); kt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), .5, LINE), ("INNERGRID", (0, 0), (-1, -1), .3, LINE), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                                                                     ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    E += [kt, P("2. Input Data", "h1")]
    tabs = input_tables(r)
    for k_ in range(0, len(tabs), 2):
        pair = tabs[k_:k_ + 2]; cells = []
        for title, rows in pair:
            rr = [[P(title, "head"), ""]] + [[P(a, "cell"), P(b, "cellb")] for a, b in rows]
            cells.append(tbl(rr, [W / 2 * 0.52, W / 2 * 0.40], True, [("SPAN", (0, 0), (-1, 0))]))
        if len(cells) == 1: cells.append("")
        wrap = Table([cells], colWidths=[W / 2, W / 2]); wrap.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        E.append(wrap)
    E += [PageBreak(), P("3. Design Checks Summary", "h1")]
    rows = [[P(h, "head") for h in ("Check", "Demand", "Limit", "Unit", "Util.", "Status", "Clause")]]
    ex = []
    for n_, c in enumerate(ch, 1):
        u = "-" if c["util"] is None else f"{c['util']*100:.1f} %"
        rows.append([P(c["name"], "cell"), P(f"{c['demand']:,.2f}", "cell"), P(f"{c['limit']:,.2f}", "cell"), P(c["unit"], "cell"), P(u, "cell"),
                     Paragraph(f"<b>{c['status']}</b>", ParagraphStyle("x", fontName="DV-B", fontSize=8, textColor=GOOD if c["status"] == "PASS" else BAD)), P(c["clause"], "note")])
    E.append(tbl(rows, [W * .25, W * .11, W * .11, W * .07, W * .09, W * .1, W * .27]))
    E += [Spacer(1, 4), P("Utilisation = demand / limit. Clause references marked (verify) must be confirmed against the current code editions.", "note"), P("4. Diagrams", "h1")]
    def fig_img(fn, w_=W, h_=W * 0.46, size=(8, 3.7)):
        fg = Figure(figsize=size); FigureCanvasAgg(fg); fn(fg); b = io.BytesIO(); fg.savefig(b, format="png", dpi=150); b.seek(0)
        return Image(b, w_, h_)
    for pl in PLOTS:
        E.append(KeepTogether([P(pl, "h2"), fig_img(lambda fg, pl=pl: draw_plot(fg, pl, r))]))
    E.append(CondPageBreak(90 * mm)); E.append(P("Bridge cross-section and girder section", "h2"))
    E.append(fig_img(lambda fg: U.draw_view(fg, U.VIEWS[3], r), size=(8, 3.8)))
    E.append(fig_img(lambda fg: U.draw_view(fg, U.VIEWS[4], r), W * 0.62, W * 0.62 * 1.12, size=(6.4, 7.2)))
    # step by step
    E += [PageBreak(), P("5. Step-by-Step Calculations", "h1"),
          P("Each check is shown as: Formula (blue italics), Substitution with the actual values (monospace) and Result (bold). Values are in kN, m and MPa unless stated.", "note"), Spacer(1, 4)]
    lblmap = {"f": "Formula", "s": "Values", "r": "Result", "t": "Note"}
    for n_, c in enumerate(ch, 1):
        okc = GOOD if c["status"] == "PASS" else BAD
        util = "-" if c["util"] is None else f"{c['util']*100:.1f} %"
        head = Table([[Paragraph(f"<b>{n_}. {escape(c['name'])}</b>", ParagraphStyle("hh", fontName="DV-B", fontSize=10, textColor=colors.white)),
                       Paragraph(f"<b>{c['status']}</b>", ParagraphStyle("hs", fontName="DV-B", fontSize=9, textColor=colors.white, alignment=2))]], colWidths=[W * .8, W * .2])
        head.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), NAVY), ("BACKGROUND", (1, 0), (1, 0), okc), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        sm = Table([[P("Demand", "lab"), P("Limit", "lab"), P("Utilisation", "lab"), P("Clause / location", "lab")],
                    [P(f"{c['demand']:,.2f} {c['unit']}", "cellb"), P(f"{c['limit']:,.2f} {c['unit']}", "cellb"), P(util, "cellb"),
                     P(c["clause"] + (f"  [{c['where']}]" if c["where"] else ""), "cell")]], colWidths=[W * .2, W * .2, W * .15, W * .45])
        sm.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")), ("BOX", (0, 0), (-1, -1), .4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        body, sty = [], [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("BOX", (0, 0), (-1, -1), .4, LINE)]
        for kind, txt in c.get("calc", []):
            ri = len(body)
            if kind == "h":
                body.append([P(txt, "sec"), ""]); sty += [("SPAN", (0, ri), (1, ri)), ("LINEBELOW", (0, ri), (1, ri), .5, LINE), ("TOPPADDING", (0, ri), (-1, ri), 6)]
            elif kind == "t": body.append([P("Note", "lab"), P(txt, "note")])
            elif kind == "f": body.append([P("Formula", "lab"), P(txt, "form")])
            elif kind == "s": body.append([P("Values", "lab"), P(txt, "sub_")])
            else: body.append([P("Result", "lab"), P(txt, "res")]); sty += [("BACKGROUND", (0, ri), (1, ri), colors.HexColor("#EBF8FF"))]
        ct = Table(body or [["", ""]], colWidths=[W * .1, W * .9]); ct.setStyle(TableStyle(sty))
        E.append(KeepTogether([head, sm, ct, Spacer(1, 12)])) if len(body) < 22 else E.extend([head, sm, ct, Spacer(1, 12)])
    E += [PageBreak(), P("6. Calculation Notes (global)", "h1")]
    for stp in r["steps"]:
        rows = [[P(stp["title"], "head"), ""], [P("Given", "lab"), P(stp["given"], "cell")], [P("Formula", "lab"), P(stp["formula"], "form")],
                [P("Values", "lab"), P(stp["substitution"], "sub_")], [P("Result", "lab"), P(stp["result"], "res")], [P("Check", "lab"), P(stp["verification"], "note")]]
        t = Table(rows, colWidths=[W * .1, W * .9]); t.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (1, 0), NAVY), ("BOX", (0, 0), (-1, -1), .4, LINE),
                                                                                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        E += [KeepTogether([t]), Spacer(1, 8)]
    E.append(P("7. Assumptions to Verify", "h1"))
    for a_ in r["assumptions"]: E.append(P("•  " + a_, "note"))
    for w_ in r["warnings"]: E.append(P("Warning: " + w_, "note"))
    doc.build(E)


class ReportPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        lay = QVBoxLayout(self); row = QHBoxLayout()
        for t, fn in [("Export PDF", self.pdf), ("Export CSV", self.csv), ("Export TXT", self.txt)]:
            b = QPushButton(t); b.setObjectName("nav_next"); b.clicked.connect(fn); row.addWidget(b)
        row.addStretch(); lay.addLayout(row)
        self.view = QTextEdit(); self.view.setReadOnly(True); self.view.setStyleSheet("font-family:monospace;font-size:11px;")
        lay.addWidget(self.view)

    def refresh(self):
        if self.main.results: self.view.setPlainText(build_text(self.main.results, self.main.p_name.text()))

    def _go(self, flt, ext, fn):
        r = self.main.get_results()
        if r is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save", f"bridge_report.{ext}", flt)
        if path:
            try: fn(path, r); QMessageBox.information(self, "Saved", path)
            except Exception as e: QMessageBox.warning(self, "Export failed", str(e))

    def pdf(self): self._go("PDF (*.pdf)", "pdf", lambda p, r: write_pdf(p, r, self.main.p_name.text(), self.main.meta()))
    def txt(self): self._go("Text (*.txt)", "txt", lambda p, r: open(p, "w", encoding="utf-8").write(build_text(r, self.main.p_name.text())))

    def csv(self):
        def w(path, r):
            with open(path, "w", newline="", encoding="utf-8") as fh:
                cw = csv.writer(fh); cw.writerow(["check", "demand", "limit", "unit", "utilisation", "status", "clause", "where"])
                for c in r["checks"]: cw.writerow([c["name"], c["demand"], c["limit"], c["unit"], c["util"], c["status"], c["clause"], c["where"]])
                f = r["forces"]; cw.writerow([]); cw.writerow(["x_m", "M_uls_kNm", "Ved_kN", "VRd_kN", "defl_total_mm", "Pe_kN", "e_m"])
                for i in range(len(f["xs"])):
                    cw.writerow([f["xs"][i], f["M_uls"][i], f["Ved"][i], f["V_cap"][i], f["d_total"][i], r["prestress"]["Pe"][i], r["prestress"]["e_x"][i]])
        self._go("CSV (*.csv)", "csv", w)
