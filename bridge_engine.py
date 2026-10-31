"""
Parametric engine for a simply supported, post-tensioned PSC I-girder bridge.

Every number shown by the GUI comes from BridgeEngine.run(); nothing is hard-coded
in the UI.  Any valid combination of inputs is accepted (see BridgeInputs); invalid
combinations raise InputError with a readable message.

Units: m, kN, kNm, MPa (stress), mm only where stated.
Sign convention for stresses: compression positive.

IMPORTANT - ASSUMPTIONS TO VERIFY AGAINST THE CODES (see ASSUMPTIONS list at bottom):
the clause-level constants below were written from memory of IRC:6-2017 / IRC:112-2011 /
EN 1992-1-1 and must be checked against the code books before submission.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict, fields

import numpy as np

EP = 195000.0          # MPa, strand modulus (IRC:112 / EN 1992)
GAMMA_C = 25.0         # kN/m3
NSTA = 201             # stations along the span (odd -> midspan is a station)
DY = 0.002             # m, section integration step


class InputError(ValueError):
    pass


# ----------------------------------------------------------------------------------
# INPUTS
# ----------------------------------------------------------------------------------
@dataclass
class BridgeInputs:
    # --- global
    L: float = 33.0
    n_girders: int = 5
    spacing: float = 0.0            # m, 0 -> derived from deck width and girder count
    load_class: str = "Governing"   # Governing / Class A / Class B / Class 70R Wheeled / Class 70R Tracked
    # --- deck / carriageway
    n_lanes: int = 3
    lane_w: float = 3.5
    footpath_w: float = 1.5
    barrier_w: float = 0.5
    slab_t: float = 0.25
    haunch: float = 0.05
    deck_fck: float = 35.0
    # --- girder section
    depth: float = 2.0
    bt: float = 1.0                 # top flange width
    tf: float = 0.20                # top flange thickness
    tw: float = 0.30                # web thickness
    bb: float = 0.80                # bottom flange width
    tb: float = 0.30                # bottom flange thickness
    tw_end: float = 0.0             # web thickness in end block (0 -> same as tw)
    l_end: float = 2.0              # end-block length
    # --- materials
    fck: float = 50.0
    fy: float = 500.0
    fpk: float = 1860.0
    strand_area: float = 140.0      # mm2 (15.2 mm strand)
    # --- loads
    wc_t: float = 0.065
    wc_gamma: float = 22.0
    barrier_wt: float = 10.0        # kN/m per barrier
    footpath_t: float = 0.25
    fp_ll: float = 4.0              # kN/m2 footpath live load
    n_diaphragms: int = 5
    dia_t: float = 0.30
    # --- prestressing
    n_cables: int = 0               # 0 -> auto
    flange_ducts: int = 2           # ducts kept in the bottom flange; any further ducts go in the web, below the centroid
    strands_per_cable: int = 19
    duct_d: float = 0.10
    jack_ratio: float = 0.75        # jacking stress / fpk
    mu: float = 0.17
    k_wobble: float = 0.0015        # per m
    slip: float = 0.006             # m anchorage draw-in
    e_end: float = 0.0              # cable eccentricity at supports (below centroid, +ve)
    creep_phi: float = 1.8
    shrinkage: float = 3.5e-4
    relax1000: float = 2.5          # % (Class 2 low relaxation)
    transfer_ratio: float = 0.75    # fci / fck at stressing
    bottom_tension_rare: float = 0.0   # MPa permitted tension, rare combination
    # --- limits
    defl_ll_ratio: float = 800.0
    defl_total_ratio: float = 250.0

    @classmethod
    def from_dict(cls, d: dict) -> "BridgeInputs":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


# ----------------------------------------------------------------------------------
# VEHICLES (IRC:6) - axle loads kN, offsets m from leading axle
# ----------------------------------------------------------------------------------
_A_OFF = np.array([0, 1.1, 4.3, 5.5, 9.8, 12.8, 15.8, 18.8])
VEHICLES = {
    "Class A": (np.array([27, 27, 114, 114, 68, 68, 68, 68.0]), _A_OFF, 2.3),
    "Class B": (np.array([16, 16, 68, 68, 41, 41, 41, 41.0]), _A_OFF, 2.3),
    "Class 70R Wheeled": (np.array([80, 120, 120, 170, 170, 170, 170.0]),
                          np.array([0, 3.96, 5.48, 7.61, 8.98, 12.03, 13.40]), 2.9),
    "Class 70R Tracked": (np.full(10, 70.0), np.linspace(0, 4.57, 10), 2.9),
}


def impact_factor(cls: str, L: float) -> float:
    if cls in ("Class A", "Class B"):
        return min(4.5 / (6.0 + L), 0.5)
    if cls == "Class 70R Wheeled":
        return 0.25 if L <= 12 else min(4.5 / (6.0 + L), 0.5)
    # tracked: 25% to 5 m, linear to 10% at 9 m, 10% beyond
    if L <= 5:
        return 0.25
    if L >= 9:
        return 0.10
    return 0.25 - (L - 5) * 0.15 / 4.0


def lane_reduction(k: int) -> float:
    return 1.0 if k <= 2 else (0.9 if k == 3 else 0.8)


def ecm(fck: float) -> float:
    """Secant modulus, MPa (IRC:112 Table 6.5 expression)."""
    return 22.0 * ((fck + 10.0) / 10.0) ** 0.3 * 1000.0


# ----------------------------------------------------------------------------------
# SECTION
# ----------------------------------------------------------------------------------
def girder_width(y: np.ndarray, p: BridgeInputs) -> np.ndarray:
    """Width of the I-girder at height y above the soffit (vectorised)."""
    D, tb, tf = p.depth, p.tb, p.tf
    e = 1e-9
    ys = [0, 0.4 * tb, tb, D - tf, D - 0.4 * tf, D]
    ws = [p.bb, p.bb, p.tw, p.tw, p.bt, p.bt]
    # step discontinuities: the polyline above already has them as sloped segments
    return np.interp(y, ys, ws)


def _props(y, w):
    dA = w * DY
    A = dA.sum()
    yb = (dA * y).sum() / A
    I = (dA * (y - yb) ** 2).sum() + (w * DY ** 3 / 12).sum()
    return A, yb, I


def build_sections(p: BridgeInputs, s: float):
    D = p.depth
    yg = np.arange(DY / 2, D, DY)
    wg = girder_width(yg, p)
    A, yb, I = _props(yg, wg)
    Ecg, Ecd = ecm(p.fck), ecm(p.deck_fck)
    nd = Ecd / Ecg
    # effective slab width (EN 1992 5.3.2.1 form, l0 = L)
    bi = max((s - p.tw) / 2.0, 0.0)
    beff_i = min(0.2 * bi + 0.1 * p.L, 0.2 * p.L, bi)
    beff = min(p.tw + 2 * beff_i, s)
    beff = max(beff, p.bt)
    # composite (transformed to girder concrete)
    yh = np.arange(D + DY / 2, D + p.haunch, DY)
    wh = np.full_like(yh, p.bt) * nd
    ys = np.arange(D + p.haunch + DY / 2, D + p.haunch + p.slab_t, DY)
    ws = np.full_like(ys, beff * nd)
    yc = np.concatenate([yg, yh, ys])
    wc = np.concatenate([wg, wh, ws])
    Ac, ybc, Ic = _props(yc, wc)
    H = D + p.haunch + p.slab_t
    # actual (untransformed) widths and concrete strength per layer, for ULS
    wc_act = np.concatenate([wg, np.full_like(yh, p.bt), np.full_like(ys, beff)])
    fck_layer = np.concatenate([np.full_like(yg, p.fck), np.full_like(yh, p.deck_fck), np.full_like(ys, p.deck_fck)])
    # shear: first moment above centroid at girder level (for info)
    return dict(A=A, yb=yb, I=I, Zb=I / yb, Zt=I / (D - yb), Ac=Ac, ybc=ybc, Ic=Ic, H=H, nd=nd, beff=beff,
                yc=yc, wc_act=wc_act, fck_layer=fck_layer, Ecg=Ecg, Ecd=Ecd)


# ----------------------------------------------------------------------------------
# MOVING LOAD ENVELOPES (simply supported span)
# ----------------------------------------------------------------------------------
def moving_load_envelope(P, off, L, xs, ds=0.1):
    """Max/min moment and shear at stations xs for a train of point loads, both travel directions."""
    outs = []
    for loads, offs in ((P, off), (P[::-1], off[-1] - off[::-1])):
        train = offs[-1]
        s = np.arange(0.0, L + train + ds, ds)
        X = s[:, None] - offs[None, :]                       # (S,k) axle positions
        valid = ((X >= 0) & (X <= L)).astype(float) * loads[None, :]
        Xe = X[:, :, None]
        A = xs[None, None, :]
        M = np.where(Xe <= A, Xe * (L - A) / L, A * (L - Xe) / L)
        M = (M * valid[:, :, None]).sum(axis=1)               # (S,N)
        V = (valid[:, :, None] * ((L - Xe) / L - (Xe < A))).sum(axis=1)
        outs.append((M.max(axis=0), V.max(axis=0), V.min(axis=0)))
    Mmax = np.maximum(outs[0][0], outs[1][0])
    Vmax = np.maximum(outs[0][1], outs[1][1])
    Vmin = np.minimum(outs[0][2], outs[1][2])
    return Mmax, Vmax, Vmin


def courbon_df(n, s, Wc, lane_w, n_lanes_avail, veh_width, k):
    """Distribution factor on the worst girder for k vehicles (rigid cross-beam / Courbon)."""
    if n == 1:
        return float(k)
    xi = (np.arange(n) - (n - 1) / 2.0) * s
    sx2 = float((xi ** 2).sum())
    x_max = xi.max()
    lanes = [-Wc / 2 + lane_w * (j + 0.5) for j in range(n_lanes_avail)]
    shift = max((lane_w - veh_width) / 2.0, 0.0)
    chosen = sorted(lanes, reverse=True)[:k]
    df = sum(1.0 / n + (c + shift) * x_max / sx2 for c in chosen)
    return max(df, 0.0)


# ----------------------------------------------------------------------------------
# ENGINE
# ----------------------------------------------------------------------------------
class BridgeEngine:
    def __init__(self):
        self.results: dict = {}
        self.step_by_step: list = []

    # ---- validation -----------------------------------------------------------
    @staticmethod
    def validate(p: BridgeInputs):
        msgs = []
        def need(cond, msg):
            if not cond:
                msgs.append(msg)
        need(8 <= p.L <= 80, "Span L must be between 8 and 80 m.")
        need(1 <= p.n_girders <= 20, "Number of girders must be 1-20.")
        need(1 <= p.n_lanes <= 6, "Number of lanes must be 1-6.")
        need(2.5 <= p.lane_w <= 4.5, "Lane width must be 2.5-4.5 m.")
        need(p.depth >= 0.8 and p.depth / p.L >= 1 / 30 and p.depth / p.L <= 1 / 8,
             "Girder depth should be between L/30 and L/8 (and >= 0.8 m).")
        need(p.tf >= 0.10 and p.tw >= 0.15 and p.tb >= 0.15, "Flange/web thicknesses below minimum (100/150/150 mm).")
        need(p.tf + p.tb + 0.3 < p.depth, "Flanges leave no room for the web (depth too small).")
        need(p.bb >= p.tw and p.bt >= p.tw, "Flange widths must be >= web thickness.")
        need(p.slab_t >= 0.15, "Deck slab thickness must be >= 150 mm.")
        need(30 <= p.fck <= 90, "fck must be 30-90 MPa.")
        need(20 <= p.deck_fck <= p.fck + 20, "Deck concrete grade is out of range.")
        need(p.fy in (415, 500, 550) or 400 <= p.fy <= 600, "fy out of range.")
        need(p.fpk in (1770, 1860) or 1500 <= p.fpk <= 2000, "fpk out of range.")
        need(p.strands_per_cable >= 1, "Strands per cable must be >= 1.")
        need(p.jack_ratio <= min(0.80, 0.9 * 0.88), "Jacking stress must not exceed min(0.8 fpk, 0.9 fp0.1k).")
        need(p.duct_d >= 0.04, "Duct diameter too small.")
        need(p.e_end >= 0, "End eccentricity must be >= 0.")
        need(p.load_class in ("Governing", *VEHICLES.keys()), "Unknown load class.")
        if msgs:
            raise InputError(" ".join(msgs))

    # ---- main entry -----------------------------------------------------------
    def run(self, inputs) -> dict:
        p = inputs if isinstance(inputs, BridgeInputs) else BridgeInputs.from_dict(dict(inputs))
        self.validate(p)
        warns: list[str] = []
        L = p.L
        xs = np.linspace(0, L, NSTA)
        mid = NSTA // 2

        # ---------- deck geometry
        Wc = p.n_lanes * p.lane_w
        W = Wc + 2 * p.footpath_w + 2 * p.barrier_w
        if p.spacing > 0:
            s = p.spacing
        else:
            s = W / p.n_girders
        overhang = (W - (p.n_girders - 1) * s) / 2.0
        if overhang < -1e-6:
            raise InputError(f"Girders ({p.n_girders} x {s:.2f} m) are wider than the deck ({W:.2f} m). "
                             "Reduce girder count or spacing.")
        if not (2.0 <= s <= 3.6):
            warns.append(f"Girder spacing {s:.2f} m is outside the usual 2.0-3.6 m range.")
        if p.n_girders > 1 and overhang > 0.5 * s + 0.5:
            warns.append(f"Deck overhang {overhang:.2f} m is large vs spacing {s:.2f} m (slab flexure/outer girder load).")
        if p.n_girders == 1:
            warns.append("Single girder: transverse distribution not meaningful.")

        # ---------- sections
        S = build_sections(p, s)
        A, yb, I, Zb, Zt = S["A"], S["yb"], S["I"], S["Zb"], S["Zt"]
        Ac, ybc, Ic, H, nd = S["Ac"], S["ybc"], S["Ic"], S["H"], S["nd"]
        D = p.depth
        Ecg = S["Ecg"]
        fcd = 0.67 * p.fck / 1.5

        # ---------- dead / superimposed loads, per girder (kN/m)
        w_girder = A * GAMMA_C
        w_haunch = p.bt * p.haunch * GAMMA_C
        w_slab = W * p.slab_t * GAMMA_C / p.n_girders
        dia_w = s * max(D - p.tf - 0.1, 0.2) * p.dia_t * GAMMA_C
        w_dia = p.n_diaphragms * dia_w / L
        g_self = w_girder + w_haunch                    # on girder alone
        g_slab = w_slab + w_dia                        # on girder alone (unpropped)
        w_barrier = 2 * p.barrier_wt / p.n_girders
        w_fpdl = 2 * p.footpath_w * p.footpath_t * GAMMA_C / p.n_girders
        w_wc = p.wc_t * Wc * p.wc_gamma / p.n_girders
        w_fpll = 2 * p.footpath_w * p.fp_ll / p.n_girders
        w_sidl = w_barrier + w_fpdl                    # factor 1.35
        w_g_total = g_self + g_slab

        def M_u(w):  return w * xs * (L - xs) / 2.0
        def V_u(w):  return w * (L / 2.0 - xs)

        M_g1, M_g2 = M_u(g_self), M_u(g_slab)
        M_g = M_g1 + M_g2
        M_sidl, M_wc, M_fp = M_u(w_sidl), M_u(w_wc), M_u(w_fpll)
        V_g, V_sidl, V_wc, V_fp = V_u(w_g_total), V_u(w_sidl), V_u(w_wc), V_u(w_fpll)

        # ---------- live load envelopes (per girder, incl. impact)
        cand = list(VEHICLES) if p.load_class == "Governing" else [p.load_class]
        veh_res = {}
        for name in cand:
            P, off, vw = VEHICLES[name]
            Mm, Vmx, Vmn = moving_load_envelope(P, off, L, xs)
            kmax = p.n_lanes if name in ("Class A", "Class B") else 1
            best = (0.0, 1)
            for k in range(1, kmax + 1):
                df = courbon_df(p.n_girders, s, Wc, p.lane_w, p.n_lanes, vw, k) * lane_reduction(k)
                if df > best[0]:
                    best = (df, k)
            df, kbest = best
            imp = impact_factor(name, L)
            veh_res[name] = dict(df=df, k=kbest, imp=imp, M=Mm * df, Vmax=Vmx * df, Vmin=Vmn * df)
        names = list(veh_res)
        M_ll_raw = np.max([veh_res[n]["M"] for n in names], axis=0)        # no impact, per girder
        # impact applied per vehicle before enveloping
        M_ll = np.max([veh_res[n]["M"] * (1 + veh_res[n]["imp"]) for n in names], axis=0)
        V_ll = np.max([veh_res[n]["Vmax"] * (1 + veh_res[n]["imp"]) for n in names], axis=0)
        gov_M = max(names, key=lambda n: veh_res[n]["M"][mid] * (1 + veh_res[n]["imp"]))
        gov_V = max(names, key=lambda n: veh_res[n]["Vmax"][0] * (1 + veh_res[n]["imp"]))

        # ---------- prestressing: cable arrangement
        sig_j = p.jack_ratio * p.fpk                         # MPa
        ns = p.strands_per_cable
        cable_A = ns * p.strand_area * 1e-6                  # m2 per cable
        cover = 0.075
        clear = 0.075

        def arrange(nc):
            """Duct layout: flange_ducts ducts side by side in the bottom flange; the remaining ducts are stacked
            in the web on the centreline, above the bottom flange and below the girder centroid."""
            n_fl = min(p.flange_ducts, nc)
            n_web = nc - n_fl
            per_row = max(1, int((p.bb - 2 * cover + clear) // (p.duct_d + clear)))
            pts, left, r = [], n_fl, 0
            while left > 0:
                n_in = min(per_row, left)
                for j in range(n_in):
                    pts.append(((j - (n_in - 1) / 2) * (p.duct_d + clear), cover + p.duct_d / 2 + r * (p.duct_d + clear)))
                left -= n_in
                r += 1
            for k in range(n_web):
                pts.append((0.0, p.tb + clear + p.duct_d / 2 + k * (p.duct_d + clear)))
            ys_ = [q[1] for q in pts]
            return float(np.mean(ys_)), r + (1 if n_web else 0), max(ys_) + p.duct_d / 2, ys_, [q[0] for q in pts]

        Eci = ecm(p.transfer_ratio * p.fck)
        Ecm_ = Ecg
        fci = p.transfer_ratio * p.fck
        fct_i = 0.3 * fci ** (2 / 3)
        sidl_tot_M = M_sidl + M_wc                            # QP superimposed

        def prestress_state(nc, ns_c=None):
            ns_c = ns if ns_c is None else ns_c
            Aps = nc * ns_c * p.strand_area * 1e-6
            cg_mid, rows, top_duct, duct_ys, duct_xs = arrange(nc)
            e_mid = yb - cg_mid
            f = e_mid - p.e_end
            e_x = p.e_end + f * 4 * xs * (L - xs) / L ** 2
            xp = np.minimum(xs, L - xs)
            alpha = 8 * abs(f) * xp / L ** 2
            P0 = sig_j * Aps * 1000.0                         # kN
            Pf = P0 * np.exp(-(p.mu * alpha + p.k_wobble * xp))
            rate = max((P0 - P0 * math.exp(-(p.mu * 4 * abs(f) / L + p.k_wobble * L / 2))) / (L / 2), 1e-9)
            lset = math.sqrt(EP * 1000.0 * Aps * p.slip / rate)
            slip_loss = np.where(xp < lset, 2 * rate * (lset - xp), 0.0)
            slip_loss = np.minimum(slip_loss, 0.5 * Pf)
            P1 = Pf - slip_loss
            # elastic shortening, sequential stressing mean (EN 1992 5.10.5 form)
            sig_cgp = (P1[mid] / A + P1[mid] * e_x[mid] ** 2 / I - M_g1[mid] * e_x[mid] / I) / 1000.0
            sig_cgp = max(sig_cgp, 0.0)
            es_stress = 0.5 * (nc - 1) / nc * (EP / Eci) * sig_cgp
            Pi = P1 - es_stress * Aps * 1000.0
            # time-dependent losses (EN 1992 eq. 5.46 form), evaluated per station
            sig_pi = Pi / (Aps * 1000.0)
            mu_r = np.clip(sig_pi / p.fpk, 0.3, 0.9)
            d_pr = 0.66 * p.relax1000 * np.exp(9.1 * mu_r) * (500000.0 / 1000.0) ** (0.75 * (1 - mu_r)) * 1e-5 * sig_pi
            cg_x = yb - e_x
            ec = ybc - cg_x
            sig_qp = (Pi / A + Pi * e_x ** 2 / I - M_g * e_x / I) / 1000.0 - (sidl_tot_M * ec / Ic) / 1000.0
            sig_qp = np.maximum(sig_qp, 0.0)
            den = 1 + (EP / Ecm_) * (Aps / A) * (1 + A / I * e_x ** 2) * (1 + 0.8 * p.creep_phi)
            d_time = (p.shrinkage * EP + 0.8 * d_pr + (EP / Ecm_) * p.creep_phi * sig_qp) / den
            Pe = Pi - d_time * Aps * 1000.0
            return dict(duct_ys=duct_ys, duct_xs=duct_xs, nc=nc, Aps=Aps, cg_mid=cg_mid, rows=rows, top_duct=top_duct, e_mid=e_mid, e_x=e_x, f=f,
                        ns_c=ns_c, P0=P0, Pf=Pf, slip=slip_loss, P1=P1, Pi=Pi, Pe=Pe, es_stress=es_stress,
                        d_time=d_time, d_pr=d_pr, lset=lset, sig_pi=sig_pi, alpha=alpha,
                        sig_cgp=sig_cgp, slope=4 * f * (L - 2 * xs) / L ** 2)

        M_rare = M_g + M_sidl + M_wc + M_ll + M_fp
        M_c_rare = M_rare - M_g                                # on composite
        M_c_qp = sidl_tot_M

        def bottom_rare(ps):
            Pe, e = ps["Pe"], ps["e_x"]
            return (Pe / A + Pe * e / Zb - M_g / Zb) / 1000.0 - (M_c_rare * ybc / Ic) / 1000.0

        if p.n_cables > 0:
            ps = prestress_state(p.n_cables)
            auto = False
        else:
            auto = True
            ps = None
            for T in range(1, 60 * ns + 1):          # total strands, smallest that works
                nc_t = -(-T // ns)
                cand_ps = prestress_state(nc_t, -(-T // nc_t))
                ps = cand_ps
                if bottom_rare(cand_ps)[mid] >= -p.bottom_tension_rare:
                    break
            if bottom_rare(ps)[mid] < -p.bottom_tension_rare:
                warns.append("Even 60 cables do not remove bottom tension at midspan under the rare "
                             "combination - increase girder depth/width, reduce spacing, or accept tension.")
        nc, Aps = ps["nc"], ps["Aps"]
        ns = ps["ns_c"]
        Pe, Pi, e_x, P0 = ps["Pe"], ps["Pi"], ps["e_x"], ps["P0"]
        loss_total_mid = P0 - Pe[mid]
        if P0 > 0.85 * p.fpk * Aps * 1000:
            warns.append("Jacking force exceeds 85% of characteristic strength.")

        # ---------- stresses at all stations
        # transfer (girder alone, self weight only)
        s_top_T = (Pi / A - Pi * e_x / Zt + M_g1 / Zt) / 1000.0
        s_bot_T = (Pi / A + Pi * e_x / Zb - M_g1 / Zb) / 1000.0
        # service (Pe, girder alone for g1+g2, composite for the rest)
        def serv(Mcomp):
            top_g = (Pe / A - Pe * e_x / Zt + M_g / Zt) / 1000.0 + (Mcomp * (D - ybc) / Ic) / 1000.0
            bot = (Pe / A + Pe * e_x / Zb - M_g / Zb) / 1000.0 - (Mcomp * ybc / Ic) / 1000.0
            slab_top = (Mcomp * (H - ybc) / Ic) / 1000.0 * nd + 0.0
            return top_g, bot, slab_top
        top_r, bot_r, slab_r = serv(M_c_rare)
        top_q, bot_q, slab_q = serv(M_c_qp)

        # ---------- flexure ULS (strain compatibility, rectangular block)
        M_uls = 1.35 * (M_g + M_sidl) + 1.75 * M_wc + 1.5 * (M_ll + M_fp)
        yc, wca, fkl = S["yc"], S["wc_act"], S["fck_layer"]
        top_y = H
        d = H - ps["cg_mid"]
        fp01k = 0.88 * p.fpk
        fpd = fp01k / 1.15
        eps_pe = (Pe[mid] / (Aps * 1000.0)) / EP
        eps_c0 = ((Pe[mid] / A + Pe[mid] * e_x[mid] ** 2 / I) / 1000.0) / Ecg
        eps_p0 = eps_pe + eps_c0
        lam = 0.8
        fcd_layer = 0.67 * fkl / 1.5

        def flex_eq(x):
            eps_p = eps_p0 + 0.0035 * (d - x) / x
            sp = min(EP * eps_p, fpd)
            T = sp * Aps * 1000.0
            ytop_blk = top_y - lam * x
            mask = yc >= ytop_blk
            C = float((fcd_layer[mask] * wca[mask]).sum() * DY * 1000.0)
            ybar = float((fcd_layer[mask] * wca[mask] * (top_y - yc[mask])).sum() * DY * 1000.0 / C) if C > 0 else 0.0
            return C - T, T, C, ybar, sp, eps_p
        lo, hi = 1e-3, H - 1e-3
        for _ in range(80):
            m = 0.5 * (lo + hi)
            if flex_eq(m)[0] > 0:
                hi = m
            else:
                lo = m
        x_na = 0.5 * (lo + hi)
        _, T_f, C_f, ybar_c, sp_f, eps_pf = flex_eq(x_na)
        Mu_cap = T_f * (d - ybar_c)
        if x_na / d > 0.45:
            warns.append(f"x/d = {x_na / d:.2f} > 0.45: section is over-reinforced (brittle) - check ductility.")

        # ---------- shear (EN 1992 / IRC:112 variable-strut method)
        V_uls = 1.35 * (V_g + V_sidl) + 1.75 * V_wc + 1.5 * (V_ll + V_fp)
        Vp = Pe * np.sin(np.arctan(np.abs(ps["slope"])))
        Ved = np.maximum(V_uls - Vp * 0.9, 0.0)
        d_x = np.maximum((H - yb) + e_x, 0.5 * H)
        z_x = 0.9 * d_x
        bw_x = np.where(xs <= p.l_end, max(p.tw_end, p.tw) if p.tw_end > 0 else p.tw, p.tw)
        sig_cp = np.minimum((Pe * np.cos(np.arctan(np.abs(ps["slope"]))) / A) / 1000.0, 0.2 * fcd)
        kk = np.minimum(1 + np.sqrt(200.0 / (d_x * 1000.0)), 2.0)
        rho1 = np.minimum(Aps / (bw_x * d_x), 0.02)
        vrdc = np.maximum(0.12 * kk * (80 * rho1 * p.fck) ** (1 / 3) + 0.15 * sig_cp,
                          0.031 * kk ** 1.5 * np.sqrt(p.fck) + 0.15 * sig_cp)
        VRd_c = vrdc * bw_x * d_x * 1000.0
        nu1 = 0.6 * (1 - p.fck / 250.0)
        acw = 1 + sig_cp / fcd
        fywd = p.fy / 1.15

        def vrdmax(cot):
            return acw * bw_x * z_x * nu1 * fcd * 1000.0 / (cot + 1.0 / cot)
        cot_sel = np.full(NSTA, 1.0)
        for c in (1.0, 1.5, 2.0, 2.5):          # largest cot that still passes crushing -> least steel
            cot_sel = np.where(vrdmax(c) >= Ved, c, cot_sel)
        VRd_max = vrdmax(cot_sel)
        asw_s_req = Ved / (z_x * fywd * cot_sel * 1000.0) * 1e6      # mm2/m ... (mm2 per m of length)
        rho_min = 0.072 * math.sqrt(p.fck) / p.fy
        asw_s_min = rho_min * bw_x * 1000.0 * 1000.0                 # mm2 per m
        asw_s_need = np.maximum(asw_s_req, asw_s_min)
        # choose link diameter (2-leg) giving >=100 mm spacing in the end zone
        i_crit = int(np.argmin(np.abs(xs - d_x[0])))
        zone1 = slice(0, NSTA // 4 + 1)
        zone2 = slice(NSTA // 4 + 1, mid + 1)
        link = None
        for dia in (10, 12, 16, 20):
            Asw = 2 * math.pi * dia ** 2 / 4
            s1 = min(1000.0 * Asw / asw_s_need[zone1].max(), 0.75 * d_x[i_crit] * 1000, 300)
            if s1 >= 100:
                link = dia
                break
        if link is None:
            link = 20
        Asw = 2 * math.pi * link ** 2 / 4
        def spacing(zone):
            sv = 1000.0 * Asw / asw_s_need[zone].max()
            sv = min(sv, 0.75 * d_x[zone].min() * 1000, 300)
            return max(math.floor(sv / 25.0) * 25, 50)
        s_z1, s_z2 = spacing(zone1), spacing(zone2)
        s_prov = np.where(np.arange(NSTA) <= zone1.stop - 1, s_z1, s_z2).astype(float)
        VRd_s = (Asw / s_prov) * (z_x * 1000.0) * fywd * cot_sel / 1000.0
        V_cap = np.minimum(VRd_s, VRd_max)
        util_shear = Ved / V_cap
        i_worst_shear = int(np.argmax(util_shear[: mid + 1]))

        # ---------- deflection (service)
        def defl(M, EI):
            kap = M / EI
            y1 = np.concatenate([[0], np.cumsum((kap[1:] + kap[:-1]) / 2 * np.diff(xs))])
            y2 = np.concatenate([[0], np.cumsum((y1[1:] + y1[:-1]) / 2 * np.diff(xs))])
            return (xs / L * y2[-1] - y2) * 1000.0   # mm, downward +              # downward positive
        EIg = Ecg * 1000.0 * I
        EIc = Ecg * 1000.0 * Ic
        d_g = defl(M_g, EIg)
        d_sidl = defl(M_sidl + M_wc, EIc)
        d_pe = defl(-Pe * e_x, EIg)
        d_ll = defl(M_ll + M_fp, EIc)
        d_transfer = defl(M_g1 - Pi * e_x, EIg)
        d_sust = (1 + p.creep_phi) * (d_g + d_sidl + d_pe)        # incl. long-term (creep) amplification
        d_total = d_sust + d_ll
        lim_ll = L * 1000.0 / p.defl_ll_ratio
        lim_tot = L * 1000.0 / p.defl_total_ratio

        # ---------- reactions (per girder, unfactored)
        R_dl = w_g_total * L / 2
        R_sidl = (w_sidl + w_wc) * L / 2
        R_ll = V_ll[0]
        R_uls = V_uls[0]

        # ---------- cable fit
        web_need = p.duct_d + 2 * 0.05
        rows_h = ps["top_duct"]
        n_in_flange = min(p.flange_ducts, nc)
        n_in_web = nc - n_in_flange

        # ---------- checks list
        checks = []
        def add(name, demand, limit, unit, util, ok, clause, where=""):
            checks.append(dict(name=name, demand=demand, limit=limit, unit=unit, util=util,
                               status="PASS" if ok else "FAIL", clause=clause, where=where))
        Mu = M_uls[mid]
        add("Flexural capacity (ULS)", Mu, Mu_cap, "kNm", Mu / Mu_cap, Mu <= Mu_cap, "IRC:112 Sec.8 (verify)", "midspan")
        iv = i_worst_shear
        add("Shear capacity (ULS)", Ved[iv], V_cap[iv], "kN", util_shear[iv], util_shear[iv] <= 1.0,
            "IRC:112 cl.10.3 (verify)", f"x = {xs[iv]:.2f} m")
        add("Web crushing VRd,max", Ved[iv], VRd_max[iv], "kN", Ved[iv] / VRd_max[iv], Ved[iv] <= VRd_max[iv],
            "IRC:112 cl.10.3.3 (verify)", f"x = {xs[iv]:.2f} m")
        add("Transfer: max compression", max(s_top_T.max(), s_bot_T.max()), 0.6 * fci, "MPa",
            max(s_top_T.max(), s_bot_T.max()) / (0.6 * fci), max(s_top_T.max(), s_bot_T.max()) <= 0.6 * fci,
            "0.6 fck(t), EN 1992 5.10.2.2 / IRC:112 (verify)")
        add("Transfer: max tension", max(-min(s_top_T.min(), s_bot_T.min()), 0.0), fct_i, "MPa", max(-min(s_top_T.min(), s_bot_T.min()), 0.0) / fct_i,
            min(s_top_T.min(), s_bot_T.min()) >= -fct_i, "tension limit = fctm(fci) at transfer (adopted)")
        top_c = max(top_r.max(), slab_r.max())
        add("Service rare: max compression", top_c, 0.48 * p.fck, "MPa", top_c / (0.48 * p.fck), top_c <= 0.48 * p.fck,
            "IRC:112 cl.12.2.1 (verify)")
        add("Service rare: bottom tension", max(-bot_r.min(), 0.0), p.bottom_tension_rare, "MPa", None,
            bot_r.min() >= -p.bottom_tension_rare - 1e-9, "decompression/tension limit (adopted)",
            f"x = {xs[int(np.argmin(bot_r))]:.2f} m")
        qp_c = max(top_q.max(), slab_q.max())
        add("Service QP: max compression", qp_c, 0.36 * p.fck, "MPa", qp_c / (0.36 * p.fck), qp_c <= 0.36 * p.fck,
            "IRC:112 cl.12.2.1 (verify)")
        add("Service QP: bottom decompression", max(-bot_q.min(), 0.0), 0.0, "MPa", None, bot_q.min() >= -1e-9,
            "IRC:112 Table 12.1 (verify)")
        add("Live-load deflection", float(d_ll[mid]), lim_ll, "mm", d_ll[mid] / lim_ll, d_ll[mid] <= lim_ll,
            f"L/{p.defl_ll_ratio:.0f} (verify clause)")
        add("Total deflection (long-term)", float(d_total[mid]), lim_tot, "mm", abs(d_total[mid]) / lim_tot,
            abs(d_total[mid]) <= lim_tot, f"L/{p.defl_total_ratio:.0f} (verify clause)")
        add("Prestress: jacking stress", sig_j, min(0.8 * p.fpk, 0.9 * fp01k), "MPa", sig_j / min(0.8 * p.fpk, 0.9 * fp01k),
            sig_j <= min(0.8 * p.fpk, 0.9 * fp01k), "IRC:112 cl.12.2.2 (verify)")
        add("Prestress: Pe < P0", float(Pe[mid]), float(P0), "kN", Pe[mid] / P0, Pe[mid] < P0, "IRC brief")
        add("Cables fit in bottom flange / web", rows_h, yb, "m",
            rows_h / yb, (n_in_web == 0 or p.tw >= web_need) and rows_h <= yb,
            "all ducts below centroid; web ≥ duct + 100 mm (IRC:112 cl.15, verify)")

        # ---------- per-check calculation details (shown when a row is clicked)
        m_ = mid
        wcomp = lambda: f"Wearing coat {p.wc_t*1000:.0f} mm, barriers, footpaths shared equally among {p.n_girders} girders"
        eT = e_x
        imax_T = int(np.argmax(np.maximum(s_top_T, s_bot_T))); imin_T = int(np.argmin(np.minimum(s_top_T, s_bot_T)))
        ibr = int(np.argmin(bot_r))
        cH = lambda t: ("h", t)          # sub-heading
        cT = lambda t: ("t", t)          # plain note
        cF = lambda t: ("f", t)          # formula
        cS = lambda t: ("s", t)          # substitution
        cR = lambda t: ("r", t)          # result
        qv = lambda t: ("t", t)
        calcs = {
          "Flexural capacity (ULS)": [
            cH("1. Design moment at midspan"),
            cF("Mu = 1.35 (Mg + Msidl) + 1.75 Mwc + 1.5 (Mll + Mfp)"),
            cS(f"Mu = 1.35 × ({M_g[m_]:.1f} + {M_sidl[m_]:.1f}) + 1.75 × {M_wc[m_]:.1f} + 1.5 × ({M_ll[m_]:.1f} + {M_fp[m_]:.1f})"),
            cR(f"Mu = {M_uls[m_]:,.1f} kNm"),
            cT(f"Live load: {gov_M}; distribution factor {veh_res[gov_M]['df']:.3f}; impact {veh_res[gov_M]['imp']:.3f}"),
            cH("2. Moment capacity (strain compatibility, rectangular stress block)"),
            cT("λ = 0.8, fcd = 0.67 fck / 1.5, fpd = 0.88 fpk / 1.15"),
            cS(f"d = {d:.3f} m;  Aps = {Aps*1e6:,.0f} mm²;  fpd = {fpd:.1f} MPa;  pre-strain εp0 = {eps_p0:.5f}"),
            cS(f"Neutral axis x = {x_na:.3f} m   (x/d = {x_na/d:.3f})"),
            cS(f"Tendon stress = {sp_f:.1f} MPa   →   T = {T_f:,.0f} kN;   C = {C_f:,.0f} kN"),
            cF("Mu,cap = T × z"),
            cS(f"Mu,cap = {T_f:,.0f} × {d-ybar_c:.3f}"),
            cR(f"Mu,cap = {Mu_cap:,.1f} kNm"),
            cH("3. Check"),
            cR(f"Mu = {Mu:,.1f} kNm  ≤  Mu,cap = {Mu_cap:,.1f} kNm   →   utilisation {Mu/Mu_cap*100:.1f} %")],
          "Shear capacity (ULS)": [
            cH(f"1. Design shear at x = {xs[iv]:.2f} m"),
            cF("VEd = V_uls − 0.9 Vp,   V_uls = 1.35 (Vg + Vsidl) + 1.75 Vwc + 1.5 (Vll + Vfp)"),
            cS(f"V_uls = {V_uls[iv]:,.1f} kN;   Vp = Pe sin θ = {Vp[iv]:,.1f} kN"),
            cR(f"VEd = {V_uls[iv]:,.1f} − 0.9 × {Vp[iv]:,.1f} = {Ved[iv]:,.1f} kN"),
            cH("2. Section and links"),
            cS(f"d = {d_x[iv]:.3f} m;  z = 0.9 d = {z_x[iv]:.3f} m;  bw = {bw_x[iv]*1000:.0f} mm;  cot θ = {cot_sel[iv]:.1f}"),
            cS(f"Links: 2-leg {link} mm @ {s_prov[iv]:.0f} mm  (Asw = {Asw:.1f} mm²);  fywd = fy / 1.15 = {fywd:.1f} MPa"),
            cH("3. Capacity"),
            cF("VRd,s = (Asw / s) · z · fywd · cot θ"),
            cR(f"VRd,s = {VRd_s[iv]:,.1f} kN      (VRd,c without links = {VRd_c[iv]:,.1f} kN, for information)"),
            cR(f"Capacity = min(VRd,s ; VRd,max) = {V_cap[iv]:,.1f} kN"),
            cH("4. Check"),
            cR(f"VEd = {Ved[iv]:,.1f} kN  ≤  {V_cap[iv]:,.1f} kN   →   utilisation {util_shear[iv]*100:.1f} %")],
          "Web crushing VRd,max": [
            cH("1. Strut parameters"),
            cF("ν1 = 0.6 (1 − fck / 250);   αcw = 1 + σcp / fcd"),
            cS(f"ν1 = {nu1:.3f};   fcd = {fcd:.2f} MPa;   σcp = {sig_cp[iv]:.2f} MPa;   αcw = {acw[iv]:.3f}"),
            cH("2. Strut capacity"),
            cF("VRd,max = αcw · bw · z · ν1 · fcd / (cot θ + tan θ)"),
            cS(f"VRd,max = {acw[iv]:.3f} × {bw_x[iv]:.2f} × {z_x[iv]:.3f} × {nu1:.3f} × {fcd:.2f} × 10³ / ({cot_sel[iv]:.1f} + {1/cot_sel[iv]:.2f})"),
            cR(f"VRd,max = {VRd_max[iv]:,.1f} kN"),
            cH("3. Check"),
            cR(f"VEd = {Ved[iv]:,.1f} kN  ≤  {VRd_max[iv]:,.1f} kN   →   utilisation {Ved[iv]/VRd_max[iv]*100:.1f} %")],
          "Transfer: max compression": [
            cH("1. Stage and strength"),
            cT("Girder alone: initial prestress Pi plus girder self weight only."),
            cS(f"fci = {p.transfer_ratio} × {p.fck:.0f} = {fci:.1f} MPa"),
            cH("2. Stress at the governing section"),
            cF("σ = Pi / A  ±  Pi · e / Z  ∓  Mg1 / Z"),
            cS(f"x = {xs[imax_T]:.2f} m;  Pi = {Pi[imax_T]:,.0f} kN;  e = {eT[imax_T]:.3f} m;  Mg1 = {M_g1[imax_T]:,.0f} kNm"),
            cR(f"σtop = {s_top_T[imax_T]:.2f} MPa;   σbottom = {s_bot_T[imax_T]:.2f} MPa"),
            cH("3. Check"),
            cR(f"σmax = {max(s_top_T.max(), s_bot_T.max()):.2f} MPa  vs  limit 0.6 fci = {0.6*fci:.2f} MPa"),
            cT("Limit adopted from EN 1992-1-1 cl. 5.10.2.2; confirm the IRC:112 value.")],
          "Transfer: max tension": [
            cH("1. Governing section"),
            cS(f"x = {xs[imin_T]:.2f} m:  σtop = {s_top_T[imin_T]:.2f} MPa;  σbottom = {s_bot_T[imin_T]:.2f} MPa   (negative = tension)"),
            cH("2. Limit"),
            cF("fctm(fci) = 0.3 · fci^(2/3)"),
            cR(f"fctm = {fct_i:.2f} MPa  (adopted)")],
          "Service rare: max compression": [
            cT("Stages: Pe and girder loads on the girder alone; SIDL and live load on the composite section."),
            cS(f"Maximum girder top stress = {top_r.max():.2f} MPa;   maximum deck slab stress = {slab_r.max():.2f} MPa"),
            cF("Limit = 0.48 fck"),
            cR(f"Limit = {0.48*p.fck:.2f} MPa")],
          "Service rare: bottom tension": [
            cF("σbottom = Pe / A + Pe · e / Zb − Mg / Zb − Mcomp · ybc / Ic"),
            cS(f"x = {xs[ibr]:.2f} m;  Pe = {Pe[ibr]:,.0f} kN;  e = {e_x[ibr]:.3f} m;  Mcomp = {M_c_rare[ibr]:,.0f} kNm"),
            cR(f"σbottom = {bot_r[ibr]:.2f} MPa   (negative = tension);   permitted tension = {p.bottom_tension_rare:.2f} MPa"),
            cT(f"Automatic sizing selected {nc} cable(s) × {ns} strands to satisfy this check at midspan.")],
          "Service QP: max compression": [
            cS(f"Maximum girder top stress = {top_q.max():.2f} MPa;   maximum deck slab stress = {slab_q.max():.2f} MPa"),
            cF("Limit = 0.36 fck"),
            cR(f"Limit = {0.36*p.fck:.2f} MPa")],
          "Service QP: bottom decompression": [
            cS(f"Minimum bottom stress under quasi-permanent load = {bot_q.min():.2f} MPa"),
            cR("Requirement: σbottom ≥ 0 (no decompression)")],
          "Live-load deflection": [
            cT("Double integration of M / EI on the composite section; simply supported, zero deflection at both supports."),
            cS(f"EIc = Ecm × Ic = {Ecg*1000:,.0f} kN/m² × {Ic:.4f} m⁴"),
            cR(f"δLL (midspan) = {d_ll[m_]:.2f} mm"),
            cF(f"Limit = L / {p.defl_ll_ratio:.0f}"),
            cR(f"Limit = {lim_ll:.2f} mm")],
          "Total deflection (long-term)": [
            cS(f"Girder weight = {d_g[m_]:.2f} mm;   prestress = {d_pe[m_]:.2f} mm;   SIDL = {d_sidl[m_]:.2f} mm   (downward positive)"),
            cF("δsustained = (1 + φ) · (δg + δsidl + δp)"),
            cS(f"δsustained = (1 + {p.creep_phi}) × {d_g[m_]+d_sidl[m_]+d_pe[m_]:.2f} = {d_sust[m_]:.2f} mm"),
            cR(f"δtotal = δsustained + δLL = {d_total[m_]:.2f} mm"),
            cF(f"Limit = L / {p.defl_total_ratio:.0f}"),
            cR(f"Limit = {lim_tot:.1f} mm")],
          "Prestress: jacking stress": [
            cF("σj = ratio × fpk"),
            cS(f"σj = {p.jack_ratio} × {p.fpk:.0f} = {sig_j:.0f} MPa"),
            cF("Limit = min(0.8 fpk ; 0.9 fp0.1k)"),
            cR(f"Limit = min({0.8*p.fpk:.0f} ; {0.9*fp01k:.0f}) = {min(0.8*p.fpk,0.9*fp01k):.0f} MPa")],
          "Prestress: Pe < P0": [
            cF("P0 = σj × Aps"),
            cS(f"P0 = {sig_j:.0f} MPa × {Aps*1e6:,.0f} mm² = {P0:,.0f} kN"),
            cT(f"Losses: friction (μ = {p.mu}, k = {p.k_wobble}/m), anchorage draw-in {p.slip*1000:.1f} mm, elastic shortening, creep, shrinkage, relaxation."),
            cS(f"At midspan: Pi = {Pi[m_]:,.0f} kN;   Pe = {Pe[m_]:,.0f} kN"),
            cR(f"Total loss = {(P0-Pe[m_])/P0*100:.1f} % of P0")],
          "Cables fit in bottom flange / web": [
            cH("1. Duct layout"),
            cS(f"{nc} ducts of Ø{p.duct_d*1000:.0f} mm: {n_in_flange} in the bottom flange, {n_in_web} stacked in the web (below the centroid)"),
            cS(f"Top of duct group = {rows_h:.3f} m above soffit;   girder centroid = {yb:.3f} m"),
            cR(f"All ducts below the centroid: {'yes' if rows_h <= yb else 'NO'}"),
            cH("2. Web width (needed only if ducts are placed in the web)"),
            cF("Required web width ≥ duct diameter + 2 × 50 mm"),
            cR(f"Required = {web_need*1000:.0f} mm;   provided = {p.tw*1000:.0f} mm")],
        }
        for c in checks:
            c["calc"] = calcs.get(c["name"], [])

        # ---------- step-by-step (real substituted numbers)
        steps = [
            dict(title="Section properties (girder alone)",
                 given=f"D={D:.2f} m, bt={p.bt:.2f}, tf={p.tf:.2f}, tw={p.tw:.2f}, bb={p.bb:.2f}, tb={p.tb:.2f} m",
                 formula="A = Σ b·Δy ; ȳ = Σ b·y·Δy / A ; I = Σ b(y-ȳ)²Δy",
                 substitution=f"A={A:.4f} m², ȳb={yb:.3f} m, I={I:.4f} m⁴",
                 result=f"Zb={Zb:.4f} m³, Zt={Zt:.4f} m³", verification="numerical integration, dy=2 mm", status="INFO"),
            dict(title="Dead load per girder",
                 given=f"slab {p.slab_t} m, deck width W={W:.2f} m, {p.n_girders} girders",
                 formula="w = A·25 + haunch + W·t_slab·25/n + diaphragms",
                 substitution=f"w = {g_self:.2f} + {g_slab:.2f}",
                 result=f"{w_g_total:.2f} kN/m", verification=f"M_DL(mid) = wL²/8 = {M_g[mid]:.1f} kNm", status="INFO"),
            dict(title="Live load",
                 given=f"governing vehicle {gov_M}, DF={veh_res[gov_M]['df']:.3f} ({veh_res[gov_M]['k']} lane(s), Courbon), "
                       f"impact={veh_res[gov_M]['imp'] * 100:.1f}%",
                 formula="M_LL = DF · (1+i) · M_vehicle,max (moving-load envelope)",
                 substitution=f"M_LL(mid) = {M_ll[mid]:.1f} kNm incl. impact",
                 result=f"{M_ll[mid]:.1f} kNm", verification="envelope from 0.1 m load steps, both directions", status="INFO"),
            dict(title="Prestress force and losses (midspan)",
                 given=f"{nc} cables x {ns} strands, Aps={Aps * 1e6:.0f} mm², σj={sig_j:.0f} MPa",
                 formula="P0 = σj·Aps ; Pe = P0 - friction - slip - ES - (creep+shrinkage+relaxation)",
                 substitution=f"P0={P0:.0f} kN ; Pi(mid)={Pi[mid]:.0f} kN ; Pe(mid)={Pe[mid]:.0f} kN",
                 result=f"total loss {100 * loss_total_mid / P0:.1f} %", verification="Pe < P0", status="PASS" if Pe[mid] < P0 else "FAIL"),
            dict(title="Flexural capacity (ULS)",
                 given=f"d={d:.3f} m, Aps={Aps * 1e6:.0f} mm², fpd={fpd:.0f} MPa, x={x_na:.3f} m",
                 formula="T = σp·Aps = C ; Mu,cap = T·(d - ȳc)",
                 substitution=f"T={T_f:.0f} kN, lever arm={d - ybar_c:.3f} m",
                 result=f"Mu,cap = {Mu_cap:.0f} kNm", verification=f"Demand Mu = {Mu:.0f} kNm",
                 status="PASS" if Mu <= Mu_cap else "FAIL"),
            dict(title="Shear (variable-strut method)",
                 given=f"critical x={xs[iv]:.2f} m, bw={bw_x[iv]:.2f} m, z={z_x[iv]:.2f} m, cotθ={cot_sel[iv]:.1f}",
                 formula="VRd,s = (Asw/s)·z·fywd·cotθ ; VRd,max = αcw·bw·z·ν1·fcd/(cotθ+tanθ)",
                 substitution=f"VRd,s={VRd_s[iv]:.0f} kN, VRd,max={VRd_max[iv]:.0f} kN",
                 result=f"Ved = {Ved[iv]:.0f} kN ; 2L-{link}mm @ {s_z1:.0f}/{s_z2:.0f} mm",
                 verification=f"utilisation {util_shear[iv]:.2f}", status="PASS" if util_shear[iv] <= 1 else "FAIL"),
        ]
        self.step_by_step = steps

        # ---------- assemble
        self.results = dict(
            inputs=asdict(p), assumptions=ASSUMPTIONS, warnings=warns, checks=checks, steps=steps,
            geom=dict(L=L, W=W, Wc=Wc, spacing=s, overhang=overhang, n_girders=p.n_girders, depth=D,
                      beff=S["beff"], H=H),
            section=dict(A=A, yb=yb, I=I, Zb=Zb, Zt=Zt, Ac=Ac, ybc=ybc, Ic=Ic, nd=nd, Ecm=Ecg),
            loads=dict(g_self=g_self, g_slab=g_slab, w_g_total=w_g_total, w_sidl=w_sidl, w_wc=w_wc, w_fpll=w_fpll,
                       gov_vehicle=gov_M, df=veh_res[gov_M]["df"], lanes_loaded=veh_res[gov_M]["k"],
                       impact=veh_res[gov_M]["imp"], per_vehicle={n: dict(df=v["df"], k=v["k"], imp=v["imp"]) for n, v in veh_res.items()}),
            forces=dict(xs=xs, M_g=M_g, M_sidl=M_sidl, M_wc=M_wc, M_ll=M_ll, M_ll_raw=M_ll_raw, M_fp=M_fp, M_uls=M_uls,
                        M_rare=M_rare, V_g=V_g, V_uls=V_uls, V_ll=V_ll, Ved=Ved, VRd_s=VRd_s, VRd_max=VRd_max, V_cap=V_cap,
                        d_ll=d_ll, d_sust=d_sust, d_total=d_total, d_transfer=d_transfer, d_g=d_g, d_pe=d_pe),
            prestress=dict(nc=nc, strands_per_cable=ns, Aps_mm2=Aps * 1e6, auto=auto, sigma_j=sig_j, P0=P0,
                           Pe_mid=float(Pe[mid]), Pi_mid=float(Pi[mid]), P_support_after_fric=float(ps["Pf"][0]),
                           friction_mid=float(P0 - ps["Pf"][mid]), slip_mid=float(ps["slip"][mid]),
                           slip_end=float(ps["slip"][0]), lset=ps["lset"], es_loss=float(ps["es_stress"] * Aps * 1000),
                           time_loss=float(ps["d_time"][mid] * Aps * 1000), total_loss_pct=100 * loss_total_mid / P0,
                           e_mid=ps["e_mid"], e_end=p.e_end, cg_mid=ps["cg_mid"], rows=ps["rows"],
                           e_x=e_x, Pe=Pe, Pi=Pi, cable_y=yb - e_x, duct_ys=ps['duct_ys'], duct_xs=ps['duct_xs'], duct_d=p.duct_d),
            stresses=dict(top_T=s_top_T, bot_T=s_bot_T, top_rare=top_r, bot_rare=bot_r, slab_rare=slab_r,
                          top_qp=top_q, bot_qp=bot_q, slab_qp=slab_q),
            flexure=dict(Mu=Mu, Mu_cap=Mu_cap, d=d, x=x_na, x_over_d=x_na / d, fpd=fpd, T=T_f, C=C_f,
                         lever=d - ybar_c, sigma_p=sp_f),
            shear=dict(i=iv, x=float(xs[iv]), Ved=float(Ved[iv]), VRd_c=float(VRd_c[iv]), VRd_s=float(VRd_s[iv]),
                       VRd_max=float(VRd_max[iv]), cot=float(cot_sel[iv]), link=link, s_z1=s_z1, s_z2=s_z2, z=float(z_x[iv]),
                       bw=float(bw_x[iv]), Asw=Asw, util=float(util_shear[iv]), Vu_support=float(V_uls[0])),
            deflection=dict(ll=float(d_ll[mid]), sustained=float(d_sust[mid]), total=float(d_total[mid]),
                            transfer=float(d_transfer[mid]), lim_ll=lim_ll, lim_total=lim_tot),
            reactions=dict(dl=R_dl, sidl=R_sidl, ll=R_ll, uls=R_uls),
            kpi=dict(m_uls=float(M_uls[mid]), v_uls=float(V_uls[0]), defl=float(abs(d_total[mid])),
                     reaction=float(R_uls), x_m=float(xs[int(np.argmax(M_uls))])),
        )
        return self.results

    # backwards-compatible alias
    def analyze(self, L, num_girders, f_ck, load_class, **extra):
        d = dict(L=L, n_girders=num_girders, fck=f_ck, load_class=load_class)
        d.update(extra)
        return self.run(d)


ASSUMPTIONS = [
    "Courbon (rigid cross-beam) distribution of live load to the worst girder; no grillage/FE refinement.",
    "IRC:6 lane reduction taken as 1.0 (<=2 lanes), 0.9 (3), 0.8 (>=4) - verify against IRC:6-2017.",
    "70R wheeled/tracked treated as a single lane vehicle; Class A/B may fill all lanes. 'Governing' envelopes all.",
    "Impact factors: Class A/B 4.5/(6+L); 70R wheeled 25% to 12 m then 4.5/(6+L); tracked 25%->10% - verify.",
    "ULS partial factors: DL & SIDL 1.35, wearing coat 1.75, live 1.5 - verify IRC:6-2017 Table B.2.",
    "Deck cast on unpropped girders: girder alone carries self-weight, slab, diaphragms; composite carries SIDL and LL.",
    "SIDL shared equally by all girders (no outer-girder cantilever effect).",
    "Wind, temperature, braking, seismic are NOT modelled (the GUI no longer invents values for them).",
    "Time-dependent losses via the EN 1992-1-1 eq. 5.46 form; shrinkage/creep inputs are user values.",
    "Flexure: strain compatibility, rectangular block 0.8x, fcd = 0.67fck/1.5, strand fpd = 0.88fpk/1.15.",
    "Shear: variable-strut method with ν1 = 0.6(1-fck/250); fywd = fy/1.15 - verify IRC:112 cl.10.3.",
    "End-block bursting/anchorage-zone design, interface shear, diaphragm design and handling are NOT checked.",
    "Section is prismatic except optional end-block web thickness (used for shear only).",
]
