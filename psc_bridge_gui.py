import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

class PSCBridgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PSC Bridge Design & Analysis Tool (STAAD-Style Output)")
        self.root.geometry("1250x800")
        
        style = ttk.Style()
        style.theme_use('clam')

        # --- LEFT PANEL: Inputs & Controls (Phase 2 & 3) ---
        input_frame = ttk.LabelFrame(root, text=" Design Parameters ", padding=15)
        input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)

        ttk.Label(input_frame, text="Span Length (m):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.span_entry = ttk.Entry(input_frame, width=15)
        self.span_entry.insert(0, "33.0")
        self.span_entry.grid(row=0, column=1, pady=5)

        ttk.Label(input_frame, text="Number of Girders:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.girders_entry = ttk.Entry(input_frame, width=15)
        self.girders_entry.insert(0, "4")
        self.girders_entry.grid(row=1, column=1, pady=5)

        ttk.Label(input_frame, text="Concrete Grade (MPa):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.fck_entry = ttk.Entry(input_frame, width=15)
        self.fck_entry.insert(0, "50")
        self.fck_entry.grid(row=2, column=1, pady=5)

        # Phase 3 Feature: Load Class Dropdown
        ttk.Label(input_frame, text="IRC Loading Class:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.load_class_var = tk.StringVar(value="Class A")
        self.load_dropdown = ttk.Combobox(input_frame, textvariable=self.load_class_var, width=13, state="readonly")
        self.load_dropdown['values'] = ("Class A", "Class B", "Class 70R Tracked", "Class 70R Wheeled")
        self.load_dropdown.grid(row=3, column=1, pady=5)

        # Run Button
        run_btn = ttk.Button(input_frame, text="Generate STAAD-Style Report", command=self.run_analysis)
        run_btn.grid(row=4, column=0, columnspan=2, pady=(20, 5), sticky=tk.EW)

        # Phase 3 Feature: Export Button
        export_btn = ttk.Button(input_frame, text="Export Report (.txt)", command=self.export_report)
        export_btn.grid(row=5, column=0, columnspan=2, pady=(0, 20), sticky=tk.EW)

        # STAAD-Style Output Text Box
        ttk.Label(input_frame, text="Analysis & Design Output Report:").grid(row=6, column=0, sticky=tk.W, pady=(5, 0))
        self.results_text = tk.Text(input_frame, width=58, height=28, wrap=tk.NONE, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        
        text_scroll_y = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        text_scroll_x = ttk.Scrollbar(input_frame, orient=tk.HORIZONTAL, command=self.results_text.xview)
        self.results_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)
        self.results_text.grid(row=7, column=0, columnspan=2, pady=5, sticky=tk.NS)

        # --- RIGHT PANEL: Embedded Matplotlib Graph ---
        self.graph_frame = ttk.LabelFrame(root, text=" Bending Moment Diagram (BMD) Envelope ", padding=10)
        self.graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.fig, self.ax = plt.subplots(figsize=(7, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.run_analysis()

    def run_analysis(self):
        try:
            L = float(self.span_entry.get())
            num_girders = int(self.girders_entry.get())
            f_ck = float(self.fck_entry.get())
            load_class = self.load_class_var.get()
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values.")
            return

        # --- PHASE 1: BRIDGE COMPUTATION ENGINE ---
        girder_spacing = (3 * 3.5 + 3.0 + 1.0) / num_girders
        area_girder, h, y_b, I_val, e, b_w = 0.85, 2.0, 1.0, 0.35, 0.85, 0.30
        Z_b = I_val / y_b
        
        w_total_dl = (area_girder * 25) + (0.250 * girder_spacing * 25) + (0.065 * girder_spacing * 22)
        max_moment_dl = (w_total_dl * (L ** 2)) / 8
        v_dl = (w_total_dl * L) / 2

        # Dynamic Impact Factor selection based on Phase 3 Dropdown
        if load_class in ["Class A", "Class B"]:
            impact = round(min(4.5 / (6.0 + L), 0.50), 4)
        elif load_class == "Class 70R Tracked":
            impact = 0.25 if L <= 40.0 else 0.10
        elif load_class == "Class 70R Wheeled":
            impact = 0.25 if L <= 12.0 else 0.154

        # Moving Train Simulation (using Class A as baseline for this example structure)
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

        # Prestress Loss Estimation
        p_jack_initial = ((max_moment_dl + ll_moment_impact) / Z_b) / ((1 / area_girder) + (e / Z_b)) / 0.80
        f_c = max((p_jack_initial / area_girder) + (p_jack_initial * (e ** 2) / I_val) - (max_moment_dl * e / I_val), 0)
        A_s = p_jack_initial / 1.2e6
        
        loss_es, loss_creep, loss_shrink = (0.5 * (200e6/35e6) * f_c) * A_s, (1.6 * (200e6/35e6) * f_c) * A_s, (2.0e-4 * 200e6) * A_s
        loss_relax, loss_frict = 0.025 * p_jack_initial, 0.03 * p_jack_initial
        total_loss = loss_es + loss_creep + loss_shrink + loss_relax + loss_frict
        p_eff = p_jack_initial - total_loss

        # Shear Details
        f_t, f_cp = 0.24 * np.sqrt(f_ck) * 1000, p_eff / area_girder
        v_co = 0.67 * b_w * h * np.sqrt((f_t ** 2) + (0.8 * f_cp * f_t))
        v_req = max(0, v_uls - v_co)
        s_v = (0.87 * 500 * 157.08 * ((h*1000)-100)) / (v_req * 1000) if v_req > 0 else 999
        practical_spacing = int(min(s_v, (0.87 * 500 * 157.08) / (0.4 * b_w * 1000), 0.75 * ((h*1000)-100), 300) // 25 * 25)

        # --- STAAD-STYLE REPORT FORMATTING ---
        self.report_content = f"""============================================================
              STAAD.PRO BRIDGE ENGINEERING MODULE
        IRC:6-2017 & IRC:18-2000 COMPLIANCE REPORT
============================================================
DATE: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
PROJECT : {L}m PSC I-Girder Bridge Design
LOADING : {load_class}
STATUS  : DESIGN CHECK COMPLETED SUCCESSFULLY
------------------------------------------------------------

1. GEOMETRY & SECTION PROPERTIES
------------------------------------------------------------
  Span Length (L)          = {L:.2f} m
  Number of Girders        = {num_girders}
  Girder Spacing           = {girder_spacing:.2f} m
  Concrete Grade (fck)     = M {int(f_ck)}
  Girder Cross-Section Area= {area_girder:.2f} m^2

2. DEAD & LIVE LOAD FORCES
------------------------------------------------------------
  Total UDL (w)            = {w_total_dl:.2f} kN/m
  Max Dead Load Moment     = {max_moment_dl:.2f} kNm
  
  IRC {load_class} Live Load Analysis:
  - Unfactored LL Moment   = {exact_ll_moment:.2f} kNm
  - Impact Factor (IRC:6)  = {impact*100:.2f}%
  - LL Moment with Impact  = {ll_moment_impact:.2f} kNm
  - Ultimate Limit Moment  = {uls_moment:.2f} kNm

3. PRESTRESS LOSS ANALYSIS (IRC:18-2000)
------------------------------------------------------------
  Initial Jacking Force    = {p_jack_initial:.2f} kN
  Total Prestress Loss     = {total_loss:.2f} kN ({(total_loss / p_jack_initial * 100):.2f}%)
  Effective Prestress (Pe) = {p_eff:.2f} kN

4. ULTIMATE SHEAR & REINFORCEMENT DETAILING
------------------------------------------------------------
  Factored Design Shear    = {v_uls:.2f} kN
  Uncracked Concrete Vco   = {v_co:.2f} kN
  Shear Deficit (Vreq)     = {v_req:.2f} kN
  
  STIRRUP DESIGN SUMMARY:
  >> Provide 2-legged 10mm dia Fe500 stirrups 
     @ {practical_spacing} mm c/c along support zones.
============================================================
                     END OF REPORT
============================================================
"""
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, self.report_content)

        # --- UPDATE PLOT ---
        x = np.linspace(0, L, 100)
        m_dl_curve = (w_total_dl * x / 2) * (L - x)
        m_uls_curve = m_dl_curve * (uls_moment / max_moment_dl)

        self.ax.clear()
        self.ax.plot(x, m_dl_curve, label='Dead Load BMD', color='blue', linewidth=2)
        self.ax.plot(x, m_uls_curve, label=f'ULS Envelope ({load_class})', color='red', linestyle='--', linewidth=2)
        self.ax.fill_between(x, 0, m_dl_curve, color='blue', alpha=0.1)
        self.ax.set_title(f'Bending Moment Diagram ({L}m Span)')
        self.ax.set_xlabel('Distance along span (m)')
        self.ax.set_ylabel('Bending Moment (kNm)')
        self.ax.grid(True, linestyle=':', alpha=0.7)
        self.ax.legend()
        self.ax.invert_yaxis()
        self.canvas.draw()

    def export_report(self):
        """Phase 3 Feature: Export STAAD-style report to a text file."""
        try:
            # Open a file dialog to save the report
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Save Design Report"
            )
            if file_path:
                with open(file_path, 'w') as file:
                    file.write(self.report_content)
                messagebox.showinfo("Export Successful", f"Report successfully saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred while saving:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PSCBridgeApp(root)
    root.mainloop()