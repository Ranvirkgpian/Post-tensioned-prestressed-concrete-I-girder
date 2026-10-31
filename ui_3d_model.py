"""Model page: 2D/3D drawings generated from engine geometry (nothing hard-coded)."""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QFrame, QCheckBox, QPushButton,
                               QDialog, QScrollArea)
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavBar
from ui_common import attach_interaction
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Polygon, Rectangle
from bridge_engine import girder_width, BridgeInputs

VIEWS = ["3D view", "Elevation", "Plan", "Bridge cross-section", "Girder section & tendons"]


def _inp(r):
    return BridgeInputs.from_dict(r["inputs"])


def girder_outline(p):
    y = np.linspace(0, p.depth, 400); w = girder_width(y, p)
    return np.concatenate([np.column_stack([-w / 2, y]), np.column_stack([w[::-1] / 2, y[::-1]])])


def girder_x_positions(g):
    return (np.arange(g["n_girders"]) - (g["n_girders"] - 1) / 2) * g["spacing"]



LIGHT = np.array([-0.45, -0.6, 0.66]); LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _shade(face, base):
    v = np.asarray(face, float)
    n = np.cross(v[1] - v[0], v[2] - v[0]); nn = np.linalg.norm(n)
    if nn == 0: return base
    n = n / nn
    k = 0.5 + 0.5 * abs(float(n @ LIGHT))
    return tuple(np.clip(np.array(base[:3]) * k, 0, 1)) + (base[3] if len(base) > 3 else 1.0,)


def _box(x0, x1, y0, y1, z0, z1):
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return [[c[i] for i in f] for f in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4))]


ELEMENTS = ["Concrete deck slab", "PSC I-girders", "Cross diaphragms", "Abutments", "Bearings",
            "Dimensions", "Geometry box", "Axes"]


def draw_3d(fig, r, p, g, show=None, angles=(30, -62), zoom=1.25):
    show = {k: True for k in ELEMENTS} if show is None else show
    sel = show.get("_girders") or [True] * g["n_girders"]
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from matplotlib.patches import Patch
    L, W, n = g["L"], g["W"], g["n_girders"]; xs = girder_x_positions(g)
    top = p.depth + p.haunch + p.slab_t
    ax = fig.add_subplot(111, projection="3d"); ax.set_axis_off()
    _abh = max(1.4, 0.06 * L); _zsp = -0.15 - _abh
    ax.set_xlim(-3, L + 7); ax.set_ylim(-W / 2 - 3, W / 2 + 3); ax.set_zlim(_zsp - 1.5, top + 3.2)
    ax.set_autoscale_on(False)      # fixed limits: no autoscale (avoids matplotlib overflow after an empty redraw)
    solid, scol = [], []
    def add(faces, col):
        for f in faces: solid.append(f); scol.append(_shade(f, col))
    # abutments and bearings
    ab_l, ab_h = 1.6, max(1.4, 0.06 * L)
    for x0 in ((-0.5 - ab_l + 1.0, L - 1.0 + 0.0) if show["Abutments"] else ()):
        add(_box(x0, x0 + ab_l, -W / 2 - 0.6, W / 2 + 0.6, -0.15 - ab_h, -0.15), (0.78, 0.78, 0.76))
    for k_, xg in enumerate(xs):
      if not (show["Bearings"] and sel[k_]): continue
      for xb in (0.25, L - 0.25):
        add(_box(xb - 0.25, xb + 0.25, xg - 0.3, xg + 0.3, -0.15, 0.0), (0.18, 0.25, 0.42))
    # girders: extruded I-section
    y0 = np.linspace(0, p.depth, 400); w0 = girder_width(y0, p)
    bp = [0] + [i for i in range(1, len(y0) - 1) if abs(w0[i + 1] - 2 * w0[i] + w0[i - 1]) > 1e-7] + [len(y0) - 1]
    bp = sorted(set(bp)); y = y0[bp]; w = w0[bp]          # only the vertices where the section shape changes
    for k_, xg in enumerate(xs):
      if not (show["PSC I-girders"] and sel[k_]): continue
      if True:
        for i in range(len(y) - 1):
            for sgn in (-1, 1):
                add([[(0, xg + sgn * w[i] / 2, y[i]), (L, xg + sgn * w[i] / 2, y[i]),
                      (L, xg + sgn * w[i + 1] / 2, y[i + 1]), (0, xg + sgn * w[i + 1] / 2, y[i + 1])]], (0.28, 0.5, 0.8))
        for xx in (0, L):
            add([[(xx, xg - w[i] / 2, y[i]) for i in range(len(y))] + [(xx, xg + w[i] / 2, y[i]) for i in range(len(y) - 1, -1, -1)]], (0.25, 0.46, 0.76))
        add([[(0, xg - w[0] / 2, 0), (L, xg - w[0] / 2, 0), (L, xg + w[0] / 2, 0), (0, xg + w[0] / 2, 0)]], (0.22, 0.4, 0.68))
        add([[(0, xg - w[-1] / 2, p.depth), (L, xg - w[-1] / 2, p.depth), (L, xg + w[-1] / 2, p.depth), (0, xg + w[-1] / 2, p.depth)]], (0.3, 0.52, 0.82))
    # haunch: fills the gap between girder top flange and the deck slab soffit
    if p.haunch > 0:
        for k_, xg in enumerate(xs):
            if show["PSC I-girders"] and sel[k_]:
                add(_box(0, L, xg - p.bt / 2, xg + p.bt / 2, p.depth, p.depth + p.haunch), (0.62, 0.66, 0.72))
    # diaphragms
    dx = np.linspace(0, L, p.n_diaphragms)
    for xd in (dx if show["Cross diaphragms"] else ()):
        t = p.dia_t
        x0 = min(max(xd - t / 2, 0), L - t)
        for k in range(n - 1):
            if not (sel[k] and sel[k + 1]): continue
            add(_box(x0, x0 + t, xs[k] + p.tw / 2, xs[k + 1] - p.tw / 2, p.tb, p.depth - p.tf), (0.93, 0.55, 0.25))
    if solid:
        ax.add_collection3d(Poly3DCollection(solid, facecolors=scol, edgecolors=scol, linewidths=0.4))
    slab = Poly3DCollection(_box(0, L, -W / 2, W / 2, p.depth + p.haunch, top), facecolors=(0.78, 0.84, 0.92, 0.38),
                            edgecolors=(0.3, 0.4, 0.55, 0.9), linewidths=0.7)
    slab.set_zorder(10)
    if show["Concrete deck slab"]: ax.add_collection3d(slab)
    # dimensions (placed clear of the model, labels on a white backing so nothing is cut or overprinted)
    dc = "#1A365D"; zsp = -0.15 - ab_h
    lab = dict(color=dc, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    if show["Dimensions"]:
        xd0 = -2.4; zd = top + 0.4
        ax.plot([xd0, xd0], [-W / 2, W / 2], [zd, zd], color=dc, lw=1.2)
        for yy in np.concatenate([[-W / 2], xs, [W / 2]]):
            ax.plot([xd0, xd0], [yy, yy], [zd - 0.3, zd + 0.3], color=dc, lw=1)
        ax.text(xd0, 0, zd + 1.3, f"Deck width = {W:.2f} m", fontsize=10, fontweight="bold", **lab)
        for k in range(n - 1):
            ax.text(xd0, (xs[k] + xs[k + 1]) / 2, zd - 0.85, f"{g['spacing']:.2f}", fontsize=8, **lab)
        ysp = -W / 2 - 3.2
        ax.plot([0, L], [ysp, ysp], [zsp, zsp], color=dc, lw=1.2)
        for xx in (0, L): ax.plot([xx, xx], [ysp, ysp + 1.0], [zsp, zsp], color=dc, lw=1)
        ax.text(L / 2, ysp - 1.5, zsp - 0.9, f"Span length, L = {L:.2f} m", fontsize=10, fontweight="bold", **lab)
        for k, xd in enumerate(dx[1:-1], 1):
            ax.text(xd, -W / 2 - 1.4, zsp + 0.9, f"D{k}  x = {xd:.1f} m", fontsize=7, **lab)
        if show["Abutments"]:
            ax.text(-1.0, -W / 2 - 1.5, -0.6, "Abutment A", fontsize=8, **lab)
            ax.text(L + 1.0, -W / 2 - 1.5, -0.6, "Abutment B", fontsize=8, **lab)
    ax.set_xlim(-4, L + 6); ax.set_ylim(-W / 2 - 4, W / 2 + 3); ax.set_zlim(zsp - 1.8, top + 3.2)
    fig._aspect = (L + 10, W + 7, (top + 3.2 - zsp + 1.8) * 2.0); fig._zoom = zoom
    ax.set_box_aspect(fig._aspect, zoom=zoom)
    ax.view_init(*angles); fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig._gizmo = None; fig._main3d = ax
    if show["Axes"]:
        gz = fig.add_axes([0.0, 0.02, 0.2, 0.3], projection="3d"); gz.set_axis_off()
        gz.set_xlim(-0.4, 1.7); gz.set_ylim(-0.4, 1.7); gz.set_zlim(-0.4, 1.7); gz.set_autoscale_on(False)
        gz.set_box_aspect((1, 1, 1), zoom=1.0)
        for v, c, lab in (((1, 0, 0), "#D69E2E", "X"), ((0, 1, 0), "#2F855A", "Y"), ((0, 0, 1), "#C53030", "Z")):
            gz.quiver(0, 0, 0, *v, color=c, arrow_length_ratio=0.22, linewidth=1.8)
            gz.text(*(1.3 * np.array(v)), lab, color=c, fontsize=10, fontweight="bold", ha="center", va="center")
        gz.view_init(*angles); fig._gizmo = gz
    _collect_heavy(fig, ax)


def _collect_heavy(fig, ax):
    fig._heavy = list(ax.texts) + list(ax.lines)


DIMC = "#1E293B"  # Professional Dark Slate Gray

def dim_h(ax, x0, x1, y, text, off=0.0, fs=8):
    """Horizontal dimension line with crisp CAD-style arrows and minimal background padding."""
    ax.annotate("", xy=(x0, y), xytext=(x1, y), 
                arrowprops=dict(arrowstyle="<->", color=DIMC, lw=0.75, mutation_scale=8))
    
    # Position text dynamically: if no offset, center it; otherwise push it cleanly above/below
    valign = "center" if off == 0 else ("bottom" if off > 0 else "top")
    ax.text((x0 + x1) / 2, y + off, text, color=DIMC, ha="center", va=valign, fontsize=fs,
            bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))

def dim_v(ax, y0, y1, x, text, ha="left", dx=0.0, fs=8):
    """Vertical dimension line with crisp CAD-style arrows and aligned side text."""
    ax.annotate("", xy=(x, y0), xytext=(x, y1), 
                arrowprops=dict(arrowstyle="<->", color=DIMC, lw=0.75, mutation_scale=8))
    
    # Respects the original horizontal alignment (left/right) so text doesn't sit on the line
    ax.text(x + dx, (y0 + y1) / 2, text, color=DIMC, ha=ha, va="center", fontsize=fs,
            bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))


def draw_view(fig, view, r, show=None, angles=(30, -62), zoom=1.25):
    fig.clear(); fig._main3d = None; fig._gizmo = None; fig._heavy = []; g = r["geom"]; p = _inp(r); L = g["L"]; xs = girder_x_positions(g); W = g["W"]
    if view == VIEWS[0]:
        draw_3d(fig, r, p, g, show, angles, zoom)
        return
    if view == VIEWS[1]:
        ax = fig.add_subplot(111); top = p.depth + p.haunch + p.slab_t
        ax.add_patch(Rectangle((0, p.depth + p.haunch), L, p.slab_t, fc="#BEE3F8", ec="k"))
        ax.add_patch(Rectangle((0, 0), L, p.depth, fc="#E2E8F0", ec="k"))
        ax.add_patch(Rectangle((0, p.depth), L, p.haunch, fc="#CBD5E0", ec="k", lw=0.6))
        for xx in np.linspace(0, L, p.n_diaphragms):
            ax.plot([xx, xx], [0, p.depth], color="#DD6B20", lw=2)
        ax.plot(r["forces"]["xs"], r["prestress"]["cable_y"], "r-", label="Tendon CG"); ax.legend()
        for xx in (0, L):   # bearings at support centres
            ax.add_patch(Polygon([[xx - .25, -.2], [xx + .25, -.2], [xx, 0]], fc="#2D3748"))
        dim_h(ax, 0, L, -0.45, f"Span L = {L:.2f} m", off=0.05, fs=9)
        dxs = np.linspace(0, L, p.n_diaphragms)
        for a_, b_ in zip(dxs[:-1], dxs[1:]): dim_h(ax, a_, b_, top + 0.25, f"{b_-a_:.2f}", off=0.03)
        dim_v(ax, 0, p.depth, -0.6, f"D = {p.depth:.2f}", ha="right"); dim_v(ax, p.depth + p.haunch, top, L + 0.5, f"slab {p.slab_t*1000:.0f}")
        ax.set_xlim(-3, L + 3); ax.set_ylim(-.9, top + .8); ax.set_aspect("equal" if L < 15 else "auto")
        ax.set_title(f"Elevation, span {L:.2f} m"); ax.set_xlabel("m")
    elif view == VIEWS[2]:
        ax = fig.add_subplot(111)
        ax.add_patch(Rectangle((0, -W / 2), L, W, fc="#EDF2F7", ec="k"))
        for xg in xs: ax.plot([0, L], [xg, xg], color="#2B6CB0", lw=3)
        for xx in np.linspace(0, L, p.n_diaphragms): ax.plot([xx, xx], [xs[0], xs[-1]], color="#DD6B20")
        cw = g["Wc"]; ax.add_patch(Rectangle((0, -cw / 2), L, cw, fc="none", ec="#718096", ls="--"))
        dim_h(ax, 0, L, -W / 2 - 0.9, f"Span L = {L:.2f} m", off=0.1, fs=9)
        dim_v(ax, -W / 2, W / 2, -1.0, f"B = {W:.2f} m", ha="right", fs=9)
        for a_, b_ in zip(xs[:-1], xs[1:]): dim_v(ax, a_, b_, L + 0.8, f"{b_-a_:.2f}")
        ax.set_xlim(-4, L + 3); ax.set_ylim(-W / 2 - 2, W / 2 + 1); ax.set_aspect("equal"); ax.set_title(f"Plan - deck {W:.2f} m, carriageway {cw:.2f} m (dashed)")
    elif view == VIEWS[3]:
        ax = fig.add_subplot(111); top = p.depth + p.haunch + p.slab_t
        ax.add_patch(Rectangle((-W / 2, p.depth + p.haunch), W, p.slab_t, fc="#BEE3F8", ec="k"))
        for xg in xs:
            ax.add_patch(Polygon(girder_outline(p) + [xg, 0], fc="#E2E8F0", ec="k"))
            ax.add_patch(Rectangle((xg - p.bt / 2, p.depth), p.bt, p.haunch + 0.002, fc="#CBD5E0", ec="k", lw=0.6, zorder=3))
        fw, bw = p.footpath_w, p.barrier_w; zt = top
        for s in (-1, 1):
            xb = s * (W / 2 - bw / 2); ax.add_patch(Rectangle((xb - bw / 2, zt), bw, 1.0, fc="#A0AEC0", ec="k"))
            ax.add_patch(Rectangle((s * (W / 2 - bw - fw / 2) - fw / 2, zt), fw, p.footpath_t, fc="#CBD5E0", ec="k"))
        ax.add_patch(Rectangle((-g["Wc"] / 2, zt), g["Wc"], .03, fc="#2D3748"))
        for i in range(p.n_lanes):
            xl = -g["Wc"] / 2 + p.lane_w * (i + .5)
            ax.annotate(f"L{i+1}", (xl, zt + .25), ha="center", fontsize=8)
        yd = -0.25
        dim_h(ax, -W / 2, W / 2, yd - 0.35, f"Deck width B = {W:.2f} m", off=0.03, fs=9)
        for a_, b_ in zip(xs[:-1], xs[1:]): dim_h(ax, a_, b_, yd, f"S = {b_-a_:.2f}", off=0.03)
        dim_h(ax, -W / 2, xs[0], yd, f"{g['overhang']:.2f}", off=0.03); dim_h(ax, xs[-1], W / 2, yd, f"{g['overhang']:.2f}", off=0.03)
        dim_v(ax, 0, p.depth, xs[-1] + p.bt / 2 + 0.2, f"D = {p.depth:.2f}")
        dim_v(ax, p.depth + p.haunch, zt, W / 2 - 0.2, f"{p.slab_t*1000:.0f} mm", ha="right")
        dim_h(ax, -g["Wc"] / 2, g["Wc"] / 2, zt + 1.05, f"Carriageway {g['Wc']:.2f} m ({p.n_lanes} x {p.lane_w:.1f})", off=0.03)
        ax.set_xlim(-W / 2 - .8, W / 2 + .8); ax.set_ylim(-1.0, zt + 1.6); ax.set_aspect("equal")
        ax.set_title(f"Cross-section: {g['n_girders']} girders @ {g['spacing']:.2f} m, {p.n_lanes} lanes, overhang {g['overhang']:.2f} m")
    else:
        ax = fig.add_subplot(111)
        ax.add_patch(Polygon(girder_outline(p), fc="#E2E8F0", ec="k"))
        P = r["prestress"]
        for xc, yv in zip(P["duct_xs"], P["duct_ys"]):
            ax.add_patch(Circle((xc, yv), p.duct_d / 2, fc="#E53E3E", ec="k"))
        ax.axhline(r["section"]["yb"], color="g", ls=":"); ax.text(p.bt / 2, r["section"]["yb"], " centroid", color="g", fontsize=8)
        D_, tb_, tf_ = p.depth, p.tb, p.tf; yb_ = r["section"]["yb"]
        m = p.bt / 2 + 0.25
        dim_h(ax, -p.bt / 2, p.bt / 2, D_ + 0.08, f"top flange width {p.bt*1000:.0f}", off=0.02)
        dim_h(ax, -p.bb / 2, p.bb / 2, -0.12, f"bottom flange width {p.bb*1000:.0f}", off=-0.07)
        dim_h(ax, -p.tw / 2, p.tw / 2, D_ / 2, f"web {p.tw*1000:.0f}", off=0.03)
        dim_v(ax, D_ - 0.4 * tf_, D_, -m, f"{0.4*tf_*1000:.0f} (edge)", ha="right")
        dim_v(ax, D_ - tf_, D_, p.bt / 2 + 0.12, f"tf = {tf_*1000:.0f}")
        dim_v(ax, 0, 0.4 * tb_, -m, f"{0.4*tb_*1000:.0f} (edge)", ha="right")
        dim_v(ax, 0, tb_, p.bb / 2 + 0.12, f"tb = {tb_*1000:.0f}")
        dim_v(ax, 0, D_, m + 0.3, f"D = {D_*1000:.0f}", ha="left")
        dim_v(ax, 0, yb_, -m - 0.55, f"ybot = {yb_*1000:.0f}", ha="right")
        for xc, yv in zip(P["duct_xs"], P["duct_ys"]):
            ax.text(xc + p.duct_d / 2 + 0.03, yv, f"{yv*1000:.0f}", fontsize=7, color=DIMC, va="center")
        ax.text(-m - 0.55, -0.27, "all dimensions in mm; duct centre heights from soffit", fontsize=7, color=DIMC, ha="left")
        ax.set_xlim(-m - 1.1, m + 0.9); ax.set_ylim(-.35, D_ + .3); ax.set_aspect("equal")
        nfl = min(p.flange_ducts, P['nc'])
        ax.set_title(f"Girder section at midspan: {P['nc']} ducts x {P['strands_per_cable']} strands\nflange {nfl}, web {P['nc']-nfl} (below centroid);  e = {P['e_mid']:.3f} m")
    if view != VIEWS[0]: fig.tight_layout()


SWATCH = {"Concrete deck slab": "#C8D6EB", "PSC I-girders": "#4780CC", "Cross diaphragms": "#ED8C40",
          "Abutments": "#C7C7C2", "Bearings": "#2E406B"}


class ModelViewer(QWidget):
    """Canvas + 'Show elements' panel. Used on the page and again inside the full-screen window."""
    def __init__(self, get_results, fullscreen=False, state=None, on_fullscreen=None):
        super().__init__(); self.get_results = get_results; self.fullscreen = fullscreen
        self.angles = (30, -62); self.zoom = 1.25
        lay = QVBoxLayout(self); row = QHBoxLayout(); self.combo = QComboBox(); self.combo.addItems(VIEWS)
        row.addWidget(QLabel("View:")); row.addWidget(self.combo)
        rb = QPushButton("Reset view"); rb.clicked.connect(self.reset_view); row.addWidget(rb)
        row.addWidget(QLabel("<i>drag = rotate, wheel = zoom</i>")); row.addStretch()
        fb = QPushButton("✕ Exit full screen" if fullscreen else "⛶ Full screen")
        fb.clicked.connect(lambda: self.window().close() if fullscreen else on_fullscreen()); row.addWidget(fb)
        lay.addLayout(row)
        body = QHBoxLayout()
        self.fig = Figure(figsize=(9, 5)); self.canvas = Canvas(self.fig); attach_interaction(self.canvas)
        if fullscreen: lay.addWidget(NavBar(self.canvas, self))
        body.addWidget(self.canvas, 1)
        self.panel = QFrame(); self.panel.setObjectName("card")
        pl = QVBoxLayout(self.panel); t = QLabel("Show elements"); t.setObjectName("card_title"); pl.addWidget(t)
        self.checks = {}
        for name in ELEMENTS:
            h = QHBoxLayout(); cb = QCheckBox(name); cb.setChecked(True); cb.toggled.connect(lambda _=False: self.refresh())
            self.checks[name] = cb
            sw = QLabel(); sw.setFixedSize(12, 12)
            sw.setStyleSheet(f"background:{SWATCH.get(name, 'transparent')};border:{'1px solid #718096' if name in SWATCH else 'none'};")
            h.addWidget(sw); h.addWidget(cb, 1); pl.addLayout(h)
        pl.addSpacing(6); gt = QLabel("Girders"); gt.setObjectName("card_title"); pl.addWidget(gt)
        self.gbox = QVBoxLayout(); pl.addLayout(self.gbox); self.gchecks = []
        row2 = QHBoxLayout()
        for txt, val in (("All", True), ("None", False)):
            b = QPushButton(txt); b.clicked.connect(lambda _=False, v=val: self.set_all(v)); row2.addWidget(b)
        pl.addLayout(row2)
        self.info = QLabel(); self.info.setWordWrap(True); self.info.setTextFormat(Qt.RichText)
        self.info.setStyleSheet("background:#F8FAFC;border:1px solid #E2E8F0;padding:6px;font-size:11px;")
        pl.addWidget(self.info); pl.addStretch()
        self.panel_scroll = QScrollArea(); self.panel_scroll.setWidgetResizable(True); self.panel_scroll.setFixedWidth(250)
        self.panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.panel_scroll.setWidget(self.panel)
        self.panel.setFixedWidth(228); self.panel.setMinimumHeight(0)
        body.addWidget(self.panel_scroll); lay.addLayout(body)
        self.canvas.setMinimumSize(300, 250)
        if state: self.set_state(state)
        self.combo.currentIndexChanged.connect(lambda _=0: self.refresh())

    # ----- state
    def get_state(self):
        f = self.fig
        ang = (f._main3d.elev, f._main3d.azim) if getattr(f, "_main3d", None) is not None else self.angles
        return dict(view=self.combo.currentIndex(), checks={k: c.isChecked() for k, c in self.checks.items()},
                    girders=[c.isChecked() for c in self.gchecks], angles=ang, zoom=getattr(f, "_zoom", self.zoom))

    def set_state(self, st):
        self.combo.blockSignals(True); self.combo.setCurrentIndex(st["view"]); self.combo.blockSignals(False)
        for k, v in st["checks"].items(): self.checks[k].blockSignals(True); self.checks[k].setChecked(v); self.checks[k].blockSignals(False)
        self._pending_girders = st.get("girders"); self.angles = tuple(st["angles"]); self.zoom = st["zoom"]

    def reset_view(self):
        self.angles = (30, -62); self.zoom = 1.25; self.fig._main3d = None; self.refresh(use_saved=False)

    def set_all(self, v):
        for cb in list(self.checks.values()) + self.gchecks: cb.blockSignals(True); cb.setChecked(v); cb.blockSignals(False)
        self.refresh()

    def _sync_girders(self, n):
        if len(self.gchecks) == n: return
        keep = getattr(self, "_pending_girders", None); self._pending_girders = None
        while self.gbox.count():
            w = self.gbox.takeAt(0).widget()
            if w: w.deleteLater()
        self.gchecks = []
        for i in range(n):
            cb = QCheckBox(f"Girder G{i + 1}"); cb.setChecked(True if not keep or i >= len(keep) else keep[i])
            cb.toggled.connect(lambda _=False: self.refresh()); self.gbox.addWidget(cb); self.gchecks.append(cb)

    def refresh(self, use_saved=True):
        r = self.get_results()
        if r is None: return
        g = r["geom"]; p = _inp(r)
        self._sync_girders(g["n_girders"])
        f = self.fig
        if use_saved and getattr(f, "_main3d", None) is not None and hasattr(f._main3d, "elev"):
            self.angles = (f._main3d.elev, f._main3d.azim); self.zoom = f._zoom
        is3d = self.combo.currentText() == VIEWS[0]
        self.panel_scroll.setVisible(is3d)
        show = {k: cb.isChecked() for k, cb in self.checks.items()}; show["_girders"] = [c.isChecked() for c in self.gchecks]
        draw_view(f, self.combo.currentText(), r, show, self.angles, self.zoom)
        self.info.setVisible(show["Geometry box"])
        self.info.setText(f"<b>Bridge geometry</b><br>Span L = {g['L']:.2f} m<br>Girders = {g['n_girders']} @ {g['spacing']:.2f} m<br>"
                          f"Deck width B = {g['W']:.2f} m<br>Girder depth = {p.depth:.3f} m<br>Slab = {p.slab_t:.2f} m<br>"
                          f"Lanes = {p.n_lanes} × {p.lane_w:.1f} m<br><i>Vertical scale exaggerated;<br>barriers not drawn in 3D</i>")
        self.canvas.draw_idle()


class Model3DPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        self.viewer = ModelViewer(lambda: self.main.results, on_fullscreen=self.open_fullscreen); lay.addWidget(self.viewer)

    def refresh(self):
        self.viewer.refresh()

    def open_fullscreen(self):
        if self.main.results is None: return
        dlg = QDialog(self.main); dlg.setWindowTitle("3D model - full screen"); dlg.setStyleSheet(self.main.styleSheet())
        l = QVBoxLayout(dlg); mv = ModelViewer(lambda: self.main.results, fullscreen=True, state=self.viewer.get_state()); l.addWidget(mv)
        mv.refresh(use_saved=False); dlg.showFullScreen(); dlg.exec()
        self.viewer.set_state(mv.get_state()); self.viewer.refresh(use_saved=False)
