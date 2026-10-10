import numpy as np
import matplotlib.pyplot as plt

class PSCBridgeModel:
    def __init__(self, span_length):
        self.L = span_length  
        
        # Transverse Deck Configuration
        self.num_lanes = 3
        self.lane_width = 3.5  
        self.carriageway_width = self.num_lanes * self.lane_width
        self.footpath_width = 1.5  
        self.crash_barrier_width = 0.5  
        self.total_deck_width = (self.carriageway_width + 
                                 (2 * self.footpath_width) + 
                                 (2 * self.crash_barrier_width))
        
        # Superstructure Assumptions
        self.num_girders = 4  
        self.girder_spacing = self.total_deck_width / self.num_girders
        self.deck_slab_thickness = 0.250  
        
        # Section Properties for a typical 2m deep I-Girder
        self.area_girder = 0.85        
        self.h = 2.0                   
        self.y_b = 1.0                 
        self.I = 0.35                  
        self.Z_b = self.I / self.y_b   
        self.e = 0.85 
        self.b_w = 0.30  
        
        # Material Properties
        self.unit_weight_concrete = 25  
        self.unit_weight_wearing_coat = 22 
        self.wearing_coat_thickness = 0.065 
        self.f_ck = 50.0  
        
        # Elastic Moduli & Loss Coefficients
        self.E_s = 200e6  
        self.E_c = 35e6   
        self.creep_coeff = 1.6 
        self.shrinkage_strain = 2.0e-4 

    def calculate_dead_loads(self):
        self.dl_girder = self.area_girder * self.unit_weight_concrete
        self.dl_deck = self.deck_slab_thickness * self.girder_spacing * self.unit_weight_concrete
        self.sidl_wearing = self.wearing_coat_thickness * self.girder_spacing * self.unit_weight_wearing_coat
        return self.dl_girder + self.dl_deck + self.sidl_wearing

    def calculate_max_bending_moment(self):
        return (self.calculate_dead_loads() * (self.L ** 2)) / 8

    def calculate_impact_factor(self, load_class="Class A"):
        return round(min(4.5 / (6.0 + self.L), 0.50), 4) 

    def calculate_uls_moment(self, unfactored_ll_moment, load_class="Class A"):
        dl_moment = self.calculate_max_bending_moment()
        impact = self.calculate_impact_factor(load_class)
        ll_moment_with_impact = unfactored_ll_moment * (1 + impact)
        return round((1.35 * dl_moment) + (1.5 * ll_moment_with_impact), 2), round(ll_moment_with_impact, 2)

    def calculate_live_load_forces(self):
        axle_loads = np.array([27, 27, 114, 114, 68, 68, 68, 68])
        axle_positions = np.array([0, 1.1, 4.3, 5.5, 9.8, 12.8, 15.8, 18.8])
        max_moment, max_shear = 0.0, 0.0
        step_size = 0.1  
        train_length = axle_positions[-1]
        
        for pos in np.arange(0, self.L + train_length, step_size):
            current_positions = pos - axle_positions
            on_bridge = (current_positions >= 0) & (current_positions <= self.L)
            active_loads = axle_loads[on_bridge]
            active_positions = current_positions[on_bridge]
            
            if len(active_loads) == 0: continue
                
            moment_sum = sum([p * (0.5 * x if x <= self.L / 2 else 0.5 * (self.L - x)) 
                              for p, x in zip(active_loads, active_positions)])
            shear_sum = sum([p * (self.L - x) / self.L for p, x in zip(active_loads, active_positions)])
                
            max_moment = max(max_moment, moment_sum)
            max_shear = max(max_shear, shear_sum)
                
        dist_factor = 0.65  
        return round(max_moment * dist_factor, 2), round(max_shear * dist_factor, 2)

    def calculate_detailed_losses(self, p_jack):
        m_dl = self.calculate_max_bending_moment()
        m = self.E_s / self.E_c  
        
        f_c = max((p_jack / self.area_girder) + (p_jack * (self.e ** 2) / self.I) - (m_dl * self.e / self.I), 0)
        A_s = p_jack / 1.2e6
        
        loss_es_kN = (0.5 * m * f_c) * A_s
        loss_creep_kN = (self.creep_coeff * m * f_c) * A_s
        loss_shrink_kN = (self.shrinkage_strain * self.E_s) * A_s
        loss_relax_kN = 0.025 * p_jack
        loss_friction_kN = 0.03 * p_jack
        
        total_loss_kN = loss_es_kN + loss_creep_kN + loss_shrink_kN + loss_relax_kN + loss_friction_kN
        return p_jack - total_loss_kN, total_loss_kN, (total_loss_kN / p_jack) * 100

    def design_shear_reinforcement(self, v_req_kN):
        """Calculates vertical stirrup spacing as per IS 1343 / IS 456 for Fe500 steel."""
        bar_dia = 10  # mm
        legs = 2
        f_y = 500  # MPa (Fe500)
        
        d_eff = (self.h * 1000) - 100  # Effective depth in mm (~1900 mm)
        b_w_mm = self.b_w * 1000       # Web width in mm (300 mm)
        
        A_sv = legs * (np.pi * (bar_dia ** 2) / 4)
        
        # 1. Theoretical spacing for the shear deficit (V_req)
        s_v_req = float('inf')
        if v_req_kN > 0:
            s_v_req = (0.87 * f_y * A_sv * d_eff) / (v_req_kN * 1000)
            
        # 2. Minimum shear reinforcement spacing limit
        s_v_min_reinf = (0.87 * f_y * A_sv) / (0.4 * b_w_mm)
        
        # 3. Maximum absolute spacing limit
        s_v_max_abs = min(0.75 * d_eff, 300)
        
        final_spacing = min(s_v_req, s_v_min_reinf, s_v_max_abs)
        practical_spacing = np.floor(final_spacing / 25) * 25  # Round down to nearest 25mm
        
        print(f"\n--- SHEAR REINFORCEMENT DETAILING ---")
        if v_req_kN > 0:
            print(f"Theoretical spacing for {v_req_kN:.2f} kN deficit: {s_v_req:.1f} mm")
        print(f"IS 1343 Min. Reinforcement Limit: {s_v_min_reinf:.1f} mm")
        print(f"Absolute Maximum Spacing Limit: {s_v_max_abs:.1f} mm")
        print(f"\n=> DESIGN SUMMARY: Provide {legs}-legged {bar_dia}mm dia Fe500 stirrups @ {int(practical_spacing)} mm c/c")

    def check_shear_capacity(self):
        exact_ll_moment, exact_ll_shear = self.calculate_live_load_forces()
        w_dl = self.calculate_dead_loads()
        v_dl = (w_dl * self.L) / 2
        
        v_ll_impact = exact_ll_shear * (1 + self.calculate_impact_factor("Class A"))
        v_uls = (1.35 * v_dl) + (1.5 * v_ll_impact)
        
        m_sls = self.calculate_max_bending_moment() + v_ll_impact 
        p_jack_initial = (m_sls / self.Z_b) / ((1 / self.area_girder) + (self.e / self.Z_b)) / 0.80
        p_eff, _, _ = self.calculate_detailed_losses(p_jack_initial)
        
        f_t = 0.24 * np.sqrt(self.f_ck) * 1000  
        f_cp = p_eff / self.area_girder  
        v_co = 0.67 * self.b_w * self.h * np.sqrt((f_t ** 2) + (0.8 * f_cp * f_t))
        
        print(f"\n--- ULTIMATE SHEAR RESISTANCE (ULS) ---")
        print(f"Max Dead Load Shear (V_dl): {round(v_dl, 2)} kN")
        print(f"Max Live Load Shear with Impact (V_ll): {round(v_ll_impact, 2)} kN")
        print(f"Factored Design Shear Force (V_uls): {round(v_uls, 2)} kN")
        print(f"Uncracked Concrete Shear Capacity (V_co): {round(v_co, 2)} kN")
        
        if v_co >= v_uls:
            print("Status: SAFE. Minimum shear reinforcement is sufficient.")
            self.design_shear_reinforcement(0)
        else:
            v_req = v_uls - v_co
            print(f"Status: ADDITIONAL REINFORCEMENT REQUIRED. Stirrups must carry {round(v_req, 2)} kN.")
            self.design_shear_reinforcement(v_req)

    def plot_bending_moment_diagram(self, assumed_ll_moment):
        x = np.linspace(0, self.L, 100)
        w_dl = self.calculate_dead_loads()
        m_dl = (w_dl * x / 2) * (self.L - x)
        max_uls, _ = self.calculate_uls_moment(assumed_ll_moment, "Class A")
        m_uls = m_dl * (max_uls / self.calculate_max_bending_moment())

        plt.figure(figsize=(10, 5))
        plt.plot(x, m_dl, label=f'Dead Load BMD', color='blue', linewidth=2)
        plt.plot(x, m_uls, label=f'ULS Factored Envelope', color='red', linestyle='--', linewidth=2)
        plt.fill_between(x, 0, m_dl, color='blue', alpha=0.1)
        plt.title(f'Bending Moment Diagram ({self.L}m Span)')
        plt.xlabel('Distance along span (m)')
        plt.ylabel('Bending Moment (kNm)')
        plt.axhline(0, color='black', linewidth=1)
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend()
        plt.gca().invert_yaxis() 
        plt.show(block=False)
        plt.pause(2)

# --- Execution Block ---
if __name__ == "__main__":
    bridge = PSCBridgeModel(span_length=33)
    bridge.check_shear_capacity()
    exact_ll_moment, _ = bridge.calculate_live_load_forces()
    bridge.plot_bending_moment_diagram(assumed_ll_moment=exact_ll_moment)
    plt.show()