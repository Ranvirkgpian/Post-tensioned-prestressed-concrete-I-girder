"""Lifecycle module: healthy baseline -> inspection -> NDT -> monitoring -> synthetic data ->
features -> AI/ML assessment -> maintenance decision.  Everything is derived from the design
engine results `r`; no external ML library is needed (numpy only).  Synthetic values are
ASSUMED deterioration scenarios, not measurements, and are labelled as such everywhere."""
import numpy as np

STATES = ["Healthy", "Minor", "Moderate", "Severe"]
FEATURES = ["f1 (Hz)", "f2 (Hz)", "f3 (Hz)", "a_RMS (m/s²)", "δ_max (mm)", "ε_soffit (µε)", "UPV (km/s)", "Rebound no."]
FS, T_REC = 100.0, 40.0            # sampling frequency (Hz), record length (s)

# Deterioration scenarios (assumed, physically motivated; ranges give sample-to-sample variation)
#  dP   : loss of effective prestress force (fraction of Pe)           [tendon corrosion / extra relaxation]
#  dEI  : loss of flexural stiffness (fraction of EI)                  [cracking, concrete deterioration]
#  corr : corrosion / deterioration index 0..1 (drives NDT + visual)
SCENARIOS = {
    "Healthy":  dict(dP=(0.00, 0.01), dEI=(0.00, 0.01), corr=(0.00, 0.05), crack=(0.00, 0.05), why="Design condition; only measurement noise."),
    "Minor":    dict(dP=(0.03, 0.07), dEI=(0.02, 0.05), corr=(0.10, 0.25), crack=(0.05, 0.15), why="Hairline cracking, early chloride ingress; ~5 % prestress loss."),
    "Moderate": dict(dP=(0.10, 0.15), dEI=(0.07, 0.12), corr=(0.35, 0.55), crack=(0.20, 0.30), why="Flexural cracking at midspan, local duct corrosion; ~12 % prestress loss."),
    "Severe":   dict(dP=(0.20, 0.30), dEI=(0.15, 0.25), corr=(0.65, 0.90), crack=(0.40, 0.70), why="Wide cracks, spalling, strand corrosion; ~25 % prestress loss."),
}


def baseline(r):
    s, g, l, p, f = r["section"], r["geom"], r["loads"], r["prestress"], r["forces"]
    L = g["L"]; mid = len(f["xs"]) // 2
    EI = s["Ecm"] * 1e6 * s["Ic"]                              # N·m², composite girder
    m = (l["w_g_total"] + l["w_sidl"] + l["w_wc"]) * 1000.0 / 9.81   # kg/m (dead mass per girder)
    f1 = np.pi / (2 * L ** 2) * np.sqrt(EI / m)
    return dict(L=L, EI=EI, mass=m, f=[f1, 4 * f1, 9 * f1], Pe=p["Pe_mid"], P0=p["P0"], e_mid=p["e_mid"],
                delta=float(f["d_total"][mid]), camber=float(f["d_pe"][mid]), sig_bot=float(r["stresses"]["bot_rare"][mid]),
                A=s["A"], Zb=s["Zb"], Ecm=s["Ecm"], mid=mid,
                upv=4.30, rebound=36.0, crack=0.0, score=10.0)


def response(b, dP, dEI, corr, crack, rng, noise=True):
    """Structural + measured response for one damage state."""
    n = (lambda s: rng.normal(0, s)) if noise else (lambda s: 0.0)
    f = [fi * np.sqrt(max(1 - dEI, 0.05)) * (1 + n(0.004)) for fi in b["f"]]
    delta = (b["delta"] + abs(b["camber"]) * dP) / max(1 - dEI, 0.05) * (1 + n(0.01))
    d_sig = -b["Pe"] * dP * (1 / b["A"] + b["e_mid"] / b["Zb"]) / 1000.0       # MPa, loss of compression
    eps = -(b["sig_bot"] + d_sig) / b["Ecm"] * 1e6 + n(1.5)                  # soffit strain, microstrain (tension +)
    eps = eps + 8.0 * dEI * 10                                                # extra live-load strain from lost stiffness
    upv = b["upv"] * (1 - 0.30 * corr) + n(0.04)
    reb = b["rebound"] * (1 - 0.32 * corr) + n(0.8)
    return dict(f=f, delta=delta, eps=eps, upv=upv, rebound=reb, Pe=b["Pe"] * (1 - dP), crack=crack,
                score=float(np.clip(10 * (1 - 0.9 * corr - 0.8 * crack / 0.7 * 0.3), 0, 10)))


def accel_history(freqs, rng, zeta=0.02, ambient=0.02, fs=FS, T=T_REC):
    """Ambient + impulse-excited acceleration at midspan: sum of damped modes + noise."""
    t = np.arange(0, T, 1 / fs); a = np.zeros_like(t)
    for k, fk in enumerate(freqs):
        w = 2 * np.pi * fk; amp = ambient / (k + 1) ** 1.2
        for t0 in rng.uniform(0, T - 6, 6):                       # random vehicle / wind events
            m = t >= t0
            a[m] += amp * rng.uniform(0.6, 1.4) * np.exp(-zeta * w * (t[m] - t0)) * np.sin(w * (t[m] - t0) + rng.uniform(0, 6.28))
    return t, a + rng.normal(0, 0.004, t.size)


def spectrum(a, fs=FS):
    w = np.hanning(a.size); A = np.abs(np.fft.rfft((a - a.mean()) * w)) * 2 / w.sum()
    return np.fft.rfftfreq(a.size, 1 / fs), A


def pick_freqs(fr, A, expected, win=0.18):
    out = []
    for fe in expected:
        idx = np.where((fr > fe * (1 - win)) & (fr < fe * (1 + win)))[0]
        k = idx[np.argmax(A[idx])]
        if 0 < k < len(A) - 1:                                     # parabolic interpolation
            y0, y1, y2 = A[k - 1], A[k], A[k + 1]; d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-18)
            out.append(fr[k] + d * (fr[1] - fr[0]))
        else: out.append(fr[k])
    return out


def features(resp, rng, b):
    t, a = accel_history(resp["f"], rng); fr, A = spectrum(a)
    f1, f2, f3 = pick_freqs(fr, A, b["f"])
    x = [f1, f2, f3, float(np.sqrt(np.mean(a ** 2))), resp["delta"], resp["eps"], resp["upv"], resp["rebound"]]
    return np.array(x), (t, a, fr, A)


# ---------- ML (numpy only) ----------
def _softmax(z): z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def train_logreg(X, y, k, lr=0.3, it=1500, l2=1e-3):
    W = np.zeros((X.shape[1] + 1, k)); Xb = np.c_[X, np.ones(len(X))]; Y = np.eye(k)[y]
    for _ in range(it):
        P = _softmax(Xb @ W); W -= lr * (Xb.T @ (P - Y) / len(X) + l2 * W)
    return W


def predict(W, X): return _softmax(np.c_[X, np.ones(len(X))] @ W)


def run_monitoring(r, n_per=120, seed=7):
    rng = np.random.default_rng(seed); b = baseline(r)
    # 1. representative response per state (noise-free) and example records
    rep, rec = {}, {}
    for st in STATES:
        sc = SCENARIOS[st]; mid = {k: float(np.mean(v)) for k, v in sc.items() if k != "why"}
        rep[st] = response(b, mid["dP"], mid["dEI"], mid["corr"], mid["crack"], rng, noise=False); rep[st].update(mid)
        x, rec[st] = features(response(b, mid["dP"], mid["dEI"], mid["corr"], mid["crack"], rng), rng, b)
    # 2. synthetic dataset
    X, y, sev = [], [], []
    for ci, st in enumerate(STATES):
        sc = SCENARIOS[st]
        for _ in range(n_per):
            v = {k: rng.uniform(*sc[k]) for k in ("dP", "dEI", "corr", "crack")}
            x, _ = features(response(b, v["dP"], v["dEI"], v["corr"], v["crack"], rng), rng, b)
            X.append(x); y.append(ci); sev.append(v["dEI"])
    X, y, sev = np.array(X), np.array(y), np.array(sev)
    # 3. train / test split, standardise
    idx = rng.permutation(len(X)); ntr = int(0.7 * len(X)); tr, te = idx[:ntr], idx[ntr:]
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9; Z = (X - mu) / sd
    W = train_logreg(Z[tr], y[tr], len(STATES)); pred = predict(W, Z[te]).argmax(1)
    cm = np.zeros((4, 4), int)
    for a_, p_ in zip(y[te], pred): cm[a_, p_] += 1
    acc = float((pred == y[te]).mean())
    # 4. anomaly detection: Mahalanobis distance from healthy training samples
    H = Z[tr][y[tr] == 0]; C = np.cov(H.T) + 1e-2 * np.eye(H.shape[1]); Ci = np.linalg.inv(C); m0 = H.mean(0)
    md = lambda Q: np.sqrt(np.einsum("ij,jk,ik->i", Q - m0, Ci, Q - m0))
    thr = 1.3 * float(np.percentile(md(H), 99))  # 30 % margin: training distances are optimistic
    dtest = md(Z[te])
    anom = dtest > thr
    tpr = float(anom[y[te] > 0].mean()); fpr = float(anom[y[te] == 0].mean())
    # 5. severity regression (ridge) of stiffness loss from features
    Zb_ = np.c_[Z, np.ones(len(Z))]; beta = np.linalg.solve(Zb_[tr].T @ Zb_[tr] + 1e-2 * np.eye(Zb_.shape[1]), Zb_[tr].T @ sev[tr])
    pr = Zb_[te] @ beta; ss = 1 - np.sum((sev[te] - pr) ** 2) / np.sum((sev[te] - sev[te].mean()) ** 2)
    imp = np.abs(W[:-1]).mean(1); imp = imp / imp.sum()
    # PCA for display
    U, S, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False); pcs = (Z - Z.mean(0)) @ Vt[:2].T
    # 6. assessment of the "current" condition = Moderate record (demonstration of the workflow)
    cur = "Moderate"
    xc, _ = features(response(b, **{k: float(np.mean(SCENARIOS[cur][k])) for k in ("dP", "dEI", "corr", "crack")}, rng=rng), rng, b)
    zc = (xc - mu) / sd; pc = predict(W, zc[None])[0]; cs = STATES[int(pc.argmax())]
    mc = float(md(zc[None])[0])
    dec = maintenance(cs, mc > thr, r, rep[cs] if cs in rep else rep[cur], b)
    # 7. AI health-monitoring timeline: 30 years of monthly synthetic monitoring with progressive damage
    months = np.arange(0, 361); yrs = months / 12.0; prog = 1 / (1 + np.exp(-(yrs - 17) / 4.5)); prog = (prog - prog[0]) / (prog[-1] - prog[0])
    TL = dict(yrs=yrs, prog=prog, state=[], pmax=[], dist=[], hi=[], f1=[], pe=[], probs=[])
    for pg in prog:
        v = dict(dP=0.28 * pg, dEI=0.22 * pg, corr=0.85 * pg, crack=0.6 * pg)
        rs = response(b, v["dP"], v["dEI"], v["corr"], v["crack"], rng); xx, _ = features(rs, rng, b); zz = (xx - mu) / sd
        pp = predict(W, zz[None])[0]; TL["probs"].append(pp); TL["state"].append(int(pp.argmax())); TL["pmax"].append(float(pp.max()))
        TL["dist"].append(float(md(zz[None])[0])); TL["f1"].append(float(xx[0])); TL["pe"].append(rs["Pe"])
        TL["hi"].append(float(np.clip(100 * (1 - (np.r_[zz, 1.0] @ beta) / 0.22), 0, 100)))
    for k in TL: TL[k] = np.array(TL[k])
    TL["hi"] = np.clip(TL["hi"], 0, 100)
    first = lambda cond: (float(yrs[np.argmax(cond)]) if cond.any() else None)
    TL["milestones"] = [("First anomaly alarm", first(TL["dist"] > thr)), ("Classified Minor", first(TL["state"] >= 1)), ("Classified Moderate", first(TL["state"] >= 2)),
                        ("Classified Severe", first(TL["state"] >= 3)), ("Health index below 50", first(TL["hi"] < 50))]
    perclass = []
    for i in range(4):
        tp = cm[i, i]; rec_ = tp / max(cm[i].sum(), 1); prec = tp / max(cm[:, i].sum(), 1); perclass.append((STATES[i], int(cm[i].sum()), prec, rec_, 2 * prec * rec_ / max(prec + rec_, 1e-9)))
    stats = {st: (X[y == i].mean(0), X[y == i].std(0)) for i, st in enumerate(STATES)}
    dist_all = dict(healthy=md(Z[y == 0]), damaged=md(Z[y > 0]))
    return dict(b=b, states=STATES, rep=rep, rec=rec, X=X, y=y, sev=sev, W=W, mu=mu, sd=sd, cm=cm, acc=acc, thr=thr, tpr=tpr, fpr=fpr,
                r2=float(ss), imp=imp, pcs=pcs, test=te, n=len(X), n_train=ntr, current=dict(true=cur, pred=cs, prob=pc, dist=mc, x=xc),
                decision=dec, timeline=TL, perclass=perclass, stats=stats, dist_all=dist_all, inspection=inspection_plan(r), ndt=ndt_plan(r, rep), sensors=sensor_plan(r))


def maintenance(state, anomaly, r, rep, b):
    fails = [c["name"] for c in r["checks"] if c["status"] == "FAIL"]
    table = {"Healthy": ("Routine inspection and monitoring", "Visual inspection every 12 months; continue SHM; principal inspection every 5 years.", "Low"),
             "Minor": ("Detailed inspection + additional NDT", "Crack mapping, cover meter and half-cell survey within 3 months; seal cracks; re-measure frequencies every 3 months.", "Medium"),
             "Moderate": ("Detailed structural assessment + preventive repair", "Load-rating re-analysis with reduced Pe and EI; repair cracks and ducts; add accelerometers and strain gauges; reinspect in 1 month.", "High"),
             "Severe": ("Restrict traffic + immediate repair / strengthening", "Impose load restriction, propup if needed, external prestressing or strengthening, then reinspect and monitor continuously.", "Critical")}
    a, d, u = table[state]
    if fails and state == "Healthy": a, d, u = table["Minor"]; d = "Design check failed: " + "; ".join(fails) + ". " + d
    return dict(state=state, action=a, detail=d, urgency=u, anomaly=bool(anomaly),
                Pe_remaining=100 * rep.get("Pe", b["Pe"]) / b["Pe"], f1_shift=100 * (1 - rep["f"][0] / b["f"][0]))


def inspection_plan(r):
    comps = ["Deck slab", "Longitudinal PSC I-girders", "Cross-girders / diaphragms", "Footpaths", "Crash barriers", "Bearings",
             "Expansion joints", "Drainage", "Pier caps", "Piers", "Abutments"]
    defects = {"Deck slab": "Cracking, spalling, leakage", "Longitudinal PSC I-girders": "Flexural / shear cracks, corrosion staining, honeycombing",
               "Cross-girders / diaphragms": "Cracking at connections", "Footpaths": "Surface deterioration", "Crash barriers": "Impact damage, spalling",
               "Bearings": "Tilting, bulging, corrosion", "Expansion joints": "Leakage, seal failure", "Drainage": "Blocked spouts, staining",
               "Pier caps": "Cracking, seepage", "Piers": "Scaling, corrosion", "Abutments": "Settlement, cracking"}
    freq = {"Longitudinal PSC I-girders": "12 months (detailed 5 years)", "Bearings": "6 months"}
    return [(c, defects[c], freq.get(c, "12 months")) for c in comps]


def ndt_plan(r, rep):
    g = r["geom"]; L = g["L"]
    locs = [("G1-1", 0.1 * L), ("G1-2", 0.25 * L), ("G1-3", 0.5 * L), ("G1-4", 0.75 * L)]
    out = []
    for nm, x in locs:
        w = np.exp(-((x - L / 2) / (0.28 * L)) ** 2)              # damage concentrated near midspan
        row = {"loc": nm, "x": x}
        for st in STATES:
            c = rep[st]["corr"] * (0.45 + 0.55 * w)
            row[st] = (36.0 * (1 - 0.32 * c), 4.30 * (1 - 0.30 * c))
        out.append(row)
    return out


def sensor_plan(r):
    L = r["geom"]["L"]
    return [("A1", "Accelerometer (vertical)", 0.5 * L, "midspan, bottom flange", f"{FS:.0f} Hz"),
            ("A2", "Accelerometer (vertical)", 0.25 * L, "quarter span", f"{FS:.0f} Hz"),
            ("A3", "Accelerometer (vertical)", 0.75 * L, "three-quarter span", f"{FS:.0f} Hz"),
            ("D1", "LVDT / displacement transducer", 0.5 * L, "midspan soffit", "10 Hz"),
            ("S1", "Vibrating-wire strain gauge", 0.5 * L, "bottom flange, midspan", "1 Hz"),
            ("S2", "Vibrating-wire strain gauge", 0.25 * L, "bottom flange, quarter span", "1 Hz"),
            ("P1", "Load cell on anchorage", 0.0, "live-end anchorage", "hourly")]
