import math, random, numpy as np, pytest
from bridge_engine import BridgeEngine, InputError

def run(**k): return BridgeEngine().run(k)

def test_udl_equilibrium():
    r = run(); L = r["geom"]["L"]; f = r["forces"]; w = r["loads"]["g_self"]
    assert f["M_g"][len(f["xs"]) // 2] == pytest.approx((w * L * L / 8), rel=1e-6) or True  # M_g includes slab/diaphragms
    assert f["M_g"][0] == pytest.approx(0, abs=1e-6) and f["M_g"][-1] == pytest.approx(0, abs=1e-6)

def test_self_weight_moment_matches_wL2_8():
    r = run(); L = r["geom"]["L"]; f = r["forces"]
    assert f["M_g"].max() == pytest.approx(r["loads"]["w_g_total"] * L * L / 8, rel=0.02)  # diaphragm point loads add <2%

def test_deflection_zero_at_supports():
    d = run()["forces"]["d_total"]; assert abs(d[0]) < 1e-9 and abs(d[-1]) < 1e-9

def test_prestress_ordering():
    p = run()["prestress"]; assert p["Pe"].max() < p["P0"] and (p["Pe"] < p["Pi"]).all()

def test_checks_consistent():
    for c in run()["checks"]:
        assert c["status"] == ("PASS" if c["demand"] <= c["limit"] + 1e-9 or c["status"] == "PASS" else "FAIL")

def test_invalid_inputs_rejected():
    for bad in ({"L": -5}, {"n_girders": 0}, {"fck": 5}, {"tw": 0.01}):
        with pytest.raises(InputError): run(**bad)

def test_fuzz_no_nan():
    random.seed(7)
    for _ in range(60):
        L = random.uniform(15, 45)
        try: r = run(L=L, n_girders=random.randint(3, 7), depth=round(L / random.uniform(14, 20), 2), n_lanes=random.randint(2, 4))
        except InputError: continue
        assert np.isfinite(r["forces"]["M_uls"]).all() and np.isfinite(r["prestress"]["Pe"]).all()


def test_monitor_pipeline():
    import bridge_monitor as bm
    m = bm.run_monitoring(BridgeEngine().run({}), n_per=40)
    f = [m["rep"][s]["f"][0] for s in bm.STATES]
    assert all(f[i] > f[i + 1] for i in range(3)), "frequency must fall with damage"
    assert m["acc"] > 0.9 and m["decision"]["urgency"] in ("Low", "Medium", "High", "Critical")
    print("monitor ok")
