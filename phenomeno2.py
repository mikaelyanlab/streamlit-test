import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
# --- Constants ---
E_a = 50e3 # J/mol for MMO; activation energy from typical enzyme kinetics
E_a_MeOH = 45e3 # J/mol for methanol oxidation
R = 8.314 # Gas constant, J/mol/K
T_ref = 298.15 # Reference temperature, K
k_MeOH_ref = 0.00011 # 1/s at 25°C; methanol oxidation rate constant
# Henry's constants in mmol/L/atm (adjusted for model units)
# Source: Sander (2015) compilation: https://acp.copernicus.org/articles/15/4399/2015/acp-15-4399-2015.pdf
H_0_CH4 = 1.4 # mmol/L/atm for CH4 at 25°C
H_0_O2 = 1.3 # mmol/L/atm for O2 at 25°C
A_V = 1e5 # m^{-1}, mesophyll surface area/volume; typical ~10^5 m^{-1} (Evans et al., Proc R Soc B 2021: https://royalsocietypublishing.org/doi/10.1098/rspb.2020.3145)
# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      V_cell, scaling_factor, photosynthesis_on):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15
    # Vmax and Km adjustments
    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/T_K - 1/T_ref))
    # Henry’s constants with temperature and osmolarity adjustments
    # Alpha and beta are empirical; osmolarity effects from Sander (2015)
    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    # Partial pressures (in atm, assuming total P=1 atm)
    P_CH4 = C_atm / 1e6 # ppm to mole fraction
    P_O2 = O2_atm / 100.0 # % to fraction
    # Equilibrium concentrations (mmol/L)
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2
    # Fluxes
    k_L_CH4_eff = g_s * A_V / H_CH4
    k_L_O2_eff = g_s * A_V / H_O2
    J_CH4 = k_L_CH4_eff * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2_eff * (O2_eq - O2_cyt)
    # MMO activity
    # Km_O2 from literature on pMMO: ~1-2 µM (0.001-0.002 mmol/L)
    # Source: Semrau et al. (2010): https://www.pnas.org/doi/10.1073/pnas.0702643105
    Km_O2 = 0.001 # mmol/L
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) * (O2_cyt / (Km_O2 + O2_cyt))
    # Optional photosynthetic O₂ production
    # Volumetric rate ~0.1 mmol/L/s based on leaf rates (20 µmol/m²/s O2, 200 µm thickness, mesophyll fraction ~0.5)
    # Source: Typical PS rates (Sharkey et al., Annu Rev Plant Biol 2008); calculation: 20e-6 mol/m²/s / (2e-4 m * 0.5) = 0.2 mol/m³/s = 0.2 mmol/L/s
    O2_prod = 0.1 if photosynthesis_on else 0 # mmol/L/s
    # ODEs
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    dO2_dt = J_O2 - V_MMO + O2_prod
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]
# --- UI ---
st.title("Methane Oxidation Model (with Optional Photosynthetic O₂)")
# Sidebar inputs
st.sidebar.header("Atmosphere & Gas Transfer")
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
O2_atm = st.sidebar.slider("Atmospheric O₂ (%)", 1.0, 25.0, 21.0)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.1, 2.0, 0.2)
st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)
st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of total cell protein)", 0.1, 5.0, 1.0, step=0.1)
baseline_vmax_at_10_percent = 0.001 # mmol/L/s at 10% expression, from Schmider et al. (2024) [assumed; similar to engineered rates ~10^{-3} mmol/L/s]
Vmax_ref = baseline_vmax_at_10_percent * (expression_percent / 10.0)
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.0, 1e-5, 1e-7, step=1e-8)  # Default 0.1 µM = 1e-7 mmol/L; Semrau et al. PNAS 2008: https://www.pnas.org/doi/10.1073/pnas.0702643105
st.sidebar.header("Biomass Settings")
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)
baseline_cell_density = 10
cytosol_fraction = 0.03 # 3% of cell volume
active_volume = cellular_material * cytosol_fraction
scaling_factor = active_volume / baseline_cell_density
V_cell = 1e-15 # Plant cell volume (L)
# Input validation
error_message = None
if Km_ref <= 0:
    error_message = "Invalid input: Km_ref must be greater than 0 to avoid undefined enzyme kinetics."
elif expression_percent <= 0:
    error_message = "Invalid input: pMMO expression must be greater than 0."
elif cellular_material <= 0:
    error_message = "Invalid input: Cellular material must be greater than 0."
elif O2_atm <= 0:
    error_message = "Invalid input: Atmospheric O₂ must be greater than 0."
elif C_atm <= 0:
    error_message = "Invalid input: Atmospheric CH₄ must be greater than 0."
elif g_s <= 0:
    error_message = "Invalid input: Stomatal conductance must be greater than 0."
elif T < -273.15:
    error_message = "Invalid input: Temperature must be above absolute zero (-273.15°C)."
if error_message:
    st.error(error_message)
    st.stop()
# Time and initial conditions
time = np.linspace(0, 100, 5000)
alpha, beta = 0.02, 0.01
H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
P_CH4 = C_atm / 1e6
C_cyt_init = H_CH4 * P_CH4 # ~1-3 nmol/L equilibrium
O2_init = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi) * (O2_atm / 100.0)
C0 = [C_cyt_init, 0, O2_init] # Realistic initials (mmol/L)
# Solve ODEs
def wrapped_ode(t, C):
    return methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                             V_cell, scaling_factor, photosynthesis_on)
sol_ivp = solve_ivp(
    fun=wrapped_ode,
    t_span=(time[0], time[-1]),
    y0=C0,
    t_eval=time,
    method='LSODA',
    rtol=1e-6,
    atol=1e-9
)
sol = sol_ivp.y.T
# Create three separate subplots with Plotly
fig_plots = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                          subplot_titles=("Cytosolic CH₄", "Methanol (CH₃OH)", "Cytosolic O₂"))
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode='lines', name="Cytosolic CH₄"), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode='lines', name="Methanol (CH₃OH)"), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode='lines', name="Cytosolic O₂"), row=3, col=1)
fig_plots.update_layout(height=800, title_text="Concentration Dynamics Over Time", showlegend=False)
fig_plots.update_xaxes(title_text="Time (s)", row=3, col=1)
fig_plots.update_yaxes(title_text="Concentration (mmol/L)", row=1, col=1)
fig_plots.update_yaxes(title_text="Concentration (mmol/L)", row=2, col=1)
fig_plots.update_yaxes(title_text="Concentration (mmol/L)", row=3, col=1)
# Final MMO rate
C_cyt_final = sol[-1, 0]
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/(T + 273.15) - 1/T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
O2_cyt_final = sol[-1, 2]
Km_O2 = 0.001
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final)) * (O2_cyt_final / (Km_O2 + O2_cyt_final))
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s", 'valueformat': '.10g'},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 1e-6]},
        'bar': {'color': "#ffcc00"},
        'steps': [{'range': [i*1e-7, (i+1)*1e-7], 'color': f"rgba(255,0,0,{0.1 + 0.1*i})"} for i in range(10)],
        'threshold': {'line': {'color': "black", 'width': 4}, 'value': V_MMO_final}
    }
))
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_plots, use_container_width=True)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)
# Sensitivity Analysis Section
st.subheader("Sensitivity Analysis")
param_options = {
    "T": {"label": "Temperature (°C)", "range": np.linspace(5, 45, 20)},
    "expression_percent": {"label": "pMMO Expression (%)", "range": np.linspace(0.1, 5.0, 20), "transform": lambda x: baseline_vmax_at_10_percent * (x / 10.0)},
    "Km_ref": {"label": "Km_ref (mmol/L)", "range": np.linspace(1e-8, 1e-5, 20)},
    "Pi": {"label": "Cytosolic Osmolarity (%)", "range": np.linspace(0, 100, 20)},
    "g_s": {"label": "Stomatal Conductance (mol/m²/s)", "range": np.linspace(0.1, 2.0, 20)},
    "cellular_material": {"label": "Cellular Material (g/L)", "range": np.linspace(0.1, 200.0, 20)},
    "C_atm": {"label": "Atmospheric CH₄ (ppm)", "range": np.linspace(0.1, 10.0, 20)},
    "O2_atm": {"label": "Atmospheric O₂ (%)", "range": np.linspace(1.0, 25.0, 20)},
}
selected_param = st.selectbox("Select Parameter to Sweep", list(param_options.keys()), format_func=lambda k: param_options[k]["label"])
if st.button("Run Sensitivity Analysis"):
    param_info = param_options[selected_param]
    param_range = param_info["range"]
    results = []
    alpha_local, beta_local = 0.02, 0.01  # Define here for consistency
    Km_O2_local = 0.001
    for val in param_range:
        local_T = T if selected_param != "T" else val
        local_expression_percent = expression_percent if selected_param != "expression_percent" else val
        local_Vmax_ref = baseline_vmax_at_10_percent * (local_expression_percent / 10.0) if selected_param == "expression_percent" else Vmax_ref
        local_Km_ref = Km_ref if selected_param != "Km_ref" else val
        local_Pi = Pi if selected_param != "Pi" else val
        local_g_s = g_s if selected_param != "g_s" else val
        local_cellular_material = cellular_material if selected_param != "cellular_material" else val
        local_scaling_factor = (local_cellular_material * cytosol_fraction) / baseline_cell_density
        local_C_atm = C_atm if selected_param != "C_atm" else val
        local_O2_atm = O2_atm if selected_param != "O2_atm" else val
        local_H_CH4 = H_0_CH4 * np.exp(-alpha_local * (local_T - 25)) * (1 - beta_local * local_Pi)
        local_P_CH4 = local_C_atm / 1e6
        local_C_cyt_init = local_H_CH4 * local_P_CH4
        local_O2_init = H_0_O2 * np.exp(-alpha_local * (local_T - 25)) * (1 - beta_local * local_Pi) * (local_O2_atm / 100.0)
        local_C0 = [local_C_cyt_init, 0, local_O2_init]
        # Solve ODE
        sol_local = solve_ivp(
            fun=lambda t, C: methane_oxidation(C, t, local_C_atm, local_O2_atm, local_g_s, local_Vmax_ref, local_Km_ref,
                                               local_Pi, local_T, V_cell, local_scaling_factor, photosynthesis_on),
            t_span=(time[0], time[-1]),
            y0=local_C0,
            t_eval=time,
            method='LSODA',
            rtol=1e-6,
            atol=1e-9
        ).y.T
        # Compute final V_MMO
        local_C_cyt_final = sol_local[-1, 0]
        local_Km_T = local_Km_ref * (1 + 0.02 * (local_T - 25))
        local_Vmax_T = local_Vmax_ref * local_scaling_factor * np.exp(-E_a / R * (1/(local_T + 273.15) - 1/T_ref))
        local_Vmax_osm = local_Vmax_T * np.exp(-0.02 * (local_Pi / 100))
        local_O2_cyt_final = sol_local[-1, 2]
        local_V_MMO_final = local_Vmax_osm * (local_C_cyt_final / (local_Km_T + local_C_cyt_final)) * (local_O2_cyt_final / (Km_O2_local + local_O2_cyt_final))
        display_val = param_info["transform"](val) if "transform" in param_info else val
        results.append((display_val, local_V_MMO_final))
    df = pd.DataFrame(results, columns=[param_info["label"], "Final CH₄ Oxidation Rate (mmol/L/s)"])
    # Plot
    fig_sa = go.Figure()
    fig_sa.add_trace(go.Scatter(x=df[param_info["label"]], y=df["Final CH₄ Oxidation Rate (mmol/L/s)"], mode="lines+markers"))
    fig_sa.update_layout(title=f"Sensitivity: {param_info['label']} vs. Final CH₄ Oxidation Rate", xaxis_title=param_info["label"], yaxis_title="mmol/L/s")
    st.plotly_chart(fig_sa)
    # Download
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "sensitivity_analysis.csv", "text/csv")
# Add list of constants and equations
st.header("Model Constants and Equations")
st.subheader("Constants")
st.markdown("""
- **E_a**: 50,000 J/mol (Activation energy for MMO)
- **E_a_MeOH**: 45,000 J/mol (Activation energy for methanol oxidation)
- **R**: 8.314 J/mol/K (Gas constant)
- **T_ref**: 298.15 K (Reference temperature)
- **k_MeOH_ref**: 0.00011 1/s (Methanol oxidation rate at 25°C)
- **H_0_CH4**: 1.4 mmol/L/atm (Henry's constant for CH4 at 25°C; Sander 2015)
- **H_0_O2**: 1.3 mmol/L/atm (Henry's constant for O2 at 25°C; Sander 2015)
- **alpha**: 0.02 (Temperature adjustment factor for Henry's constants)
- **beta**: 0.01 (Osmolarity adjustment factor for Henry's constants)
- **Km_O2**: 0.001 mmol/L (Michaelis constant for O2; Semrau et al. 2010)
- **O2_prod**: 0.1 mmol/L/s (Photosynthetic O2 production rate, if enabled; based on 20 µmol/m²/s / 200 µm thickness)
- **cytosol_fraction**: 0.03 (Fraction of cell volume that is cytosol)
- **baseline_vmax_at_10_percent**: 0.001 mmol/L/s (Baseline Vmax at 10% protein expression; Schmider et al. 2024)
- **baseline_cell_density**: 10 g/L (Baseline cell density for scaling)
- **V_cell**: 1e-15 L (Typical plant cell volume, currently unused)
- **A_V**: 100000 m^{-1} (Specific surface area for gas-liquid interface; Evans et al. 2021)
""")
st.subheader("Key Equations")
st.latex(r"Vmax_T = Vmax_{ref} \times scaling_factor \times \exp\left(-\frac{E_a}{R} \left(\frac{1}{T_K} - \frac{1}{T_{ref}}\right)\right)")
st.latex(r"Vmax = Vmax_T \times \exp(-0.02 \times (Pi / 100))")
st.latex(r"Km_T = Km_{ref} \times (1 + 0.02 \times (T - 25))")
st.latex(r"H = H_0 \times \exp(-\alpha \times (T - 25)) \times (1 - \beta \times Pi)")
st.latex(r"P_{CH4} = C_{atm} / 10^6, \quad P_{O2} = O2_{atm} / 100")
st.latex(r"C_{eq} = H \times P")
st.latex(r"k_{L,eff} = g_s \times A_V / H")
st.latex(r"J = k_{L,eff} \times (C_{eq} - C)")
st.latex(r"V_{MMO} = Vmax \times \frac{C_{cyt}}{Km_T + C_{cyt}} \times \frac{O2_{cyt}}{Km_{O2} + O2_{cyt}}")
st.latex(r"\frac{dC_{cyt}}{dt} = J_{CH4} - V_{MMO}")
st.latex(r"\frac{dCH3OH}{dt} = V_{MMO} - k_{MeOH} \times CH3OH")
st.latex(r"\frac{dO2_{cyt}}{dt} = J_{O2} - V_{MMO} + O2_{prod}")
# Debug output
k_MeOH_scaled = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/(T + 273.15) - 1/T_ref))
st.sidebar.text(f"Temp-Adjusted k_MeOH: {k_MeOH_scaled:.6g} 1/s")
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
