import numpy as np

class BridgeEngine:
    def __init__(self):
        self.results = {}

    def analyze(self, L, num_girders, f_ck, load_class):
        girder_spacing = (3 * 3.5 + 3.0 + 1.0) / num_girders
        area_girder, h, y_b, I_val, e, b_w = 0.85, 2.0, 1.0, 0.35, 0.85, 0.30
        Z_b = I_val / y_b
        
        w_total_dl = (area_girder * 25) + (0.250 * girder_spacing * 25) + (0.065 * girder_spacing * 22)
        max_moment_dl = (w_total_dl * (L ** 2)) / 8
        v_dl = (w_total_dl * L) / 2

        if load_class in ["Class A", "Class B"]: impact = round(min(4.5 / (6.0 + L), 0.50), 4)
        elif load_class == "Class 70R Tracked": impact = 0.25 if L <= 40.0 else 0.10
        elif load_class == "Class 70R Wheeled": impact = 0.25 if L <= 12.0 else 0.154
        else: impact = 0.15

        axle_loads = np.array([27, 27, 114, 114, 68, 68, 68, 68])
        axle_positions = np.array([0, 1.1, 4.3, 5.5, 9.8, 12.8, 15.8, 18.8])
        max_moment, max_shear = 0.0, 0.0
        
        for pos in np.arange(0, L + axle_positions[-1], 0.1):
            curr_pos = pos - axle_positions
            on_bridge = (curr_pos >= 0) & (curr_pos <= L)
            act_loads, act_pos = axle_loads[on_bridge], curr_pos[on_bridge]
            if len(act_loads) == 0: continue
            
            m_sum = sum([p * (0.5 * x if x <= L / 2 else 0.5 * (L - x)) for p, x in zip(act_loads, act_pos)])
            s_sum = sum([p * (L - x) / L for p, x in zip(act_loads, act_pos)])
            max_moment, max_shear = max(max_moment, m_sum), max(max_shear, s_sum)
                
        exact_ll_moment = round((max_moment * 0.65), 2)
        exact_ll_shear = round((max_shear * 0.65), 2)
        
        ll_moment_impact = exact_ll_moment * (1 + impact)
        v_ll_impact = exact_ll_shear * (1 + impact)
        uls_moment = (1.35 * max_moment_dl) + (1.5 * ll_moment_impact)
        v_uls = (1.35 * v_dl) + (1.5 * v_ll_impact)

        p_jack_initial = ((max_moment_dl + ll_moment_impact) / Z_b) / ((1 / area_girder) + (e / Z_b)) / 0.80
        f_c = max((p_jack_initial / area_girder) + (p_jack_initial * (e ** 2) / I_val) - (max_moment_dl * e / I_val), 0)
        A_s = p_jack_initial / 1.2e6
        
        loss_es = (0.5 * (200e6/35e6) * f_c) * A_s
        loss_creep = (1.6 * (200e6/35e6) * f_c) * A_s
        loss_shrink = (2.0e-4 * 200e6) * A_s
        loss_relax, loss_frict = 0.025 * p_jack_initial, 0.03 * p_jack_initial
        total_loss = loss_es + loss_creep + loss_shrink + loss_relax + loss_frict
        p_eff = p_jack_initial - total_loss

        f_t, f_cp = 0.24 * np.sqrt(f_ck) * 1000, p_eff / area_girder
        v_co = 0.67 * b_w * h * np.sqrt((f_t ** 2) + (0.8 * f_cp * f_t))
        v_req = max(0, v_uls - v_co)
        s_v = (0.87 * 500 * 157.08 * ((h*1000)-100)) / (v_req * 1000) if v_req > 0 else 999
        practical_spacing = int(min(s_v, (0.87 * 500 * 157.08) / (0.4 * b_w * 1000), 0.75 * ((h*1000)-100), 300) // 25 * 25)

        self.results = {
            "L": L, "num_girders": num_girders, "spacing": girder_spacing, "f_ck": f_ck, "load_class": load_class,
            "w_dl": w_total_dl, "m_dl": max_moment_dl, "v_dl": v_dl,
            "m_ll": exact_ll_moment, "v_ll": exact_ll_shear, "impact": impact,
            "m_ll_imp": ll_moment_impact, "v_ll_imp": v_ll_impact,
            "m_uls": uls_moment, "v_uls": v_uls,
            "p_jack": p_jack_initial, "total_loss": total_loss, "loss_pct": (total_loss/p_jack_initial)*100, "p_eff": p_eff,
            "v_co": v_co, "v_req": v_req, "stirrup_spacing": practical_spacing
        }
        return self.results