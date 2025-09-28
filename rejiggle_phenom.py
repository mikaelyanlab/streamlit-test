import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- Constants ---
E_a = 50e3  # J/mol for MMO; activation energy from typical enzyme kinetics
E_a_MeOH = 45e3  # J/mol for methanol oxidation
R = 8.314  # Gas constant, J/mol/K
T_ref = 298.15  # Reference temperature, K
k_MeOH_ref = 0.00011  # 1/s at 25°C; methanol oxidation rate constant
# Henry's constants in mmol/L/atm (adjusted for model units)
H_0_CH4 = 1.4  # mmol/L/atm for CH4 at 25°C
H_0_O2 = 1.3  # mmol/L/atm for O2 at 25°C
g_s_ref = 0.2  # mol/m²/s; reference stomatal conductance for scaling
V_cell = 1e-15  # L; typical plant cell volume
baseline_cell_density = 10  # g/L; implicit baseline biomass density

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                     k_L_CH4, k_L_O2, V_cell, scaling_factor, photosynthesis_on):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15
    # Vmax and Km adjustments
    Vmax_T = Vmax_ref * (expression_percent / 100) * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/T_K - 1/T_ref))
    # Henry’s constants with temperature and osmolarity adjustments
    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    # Partial pressures (atm)
    P_CH4 = (C_atm / 1e6)  # ppm -> mole fraction
    P_O2 = (O2_atm / 100.0)  # % -> fraction
    # Equilibrium concentrations at the interface (mmol/L)
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2
    # Fluxes scaled by relative stomatal conductance
    g_s_scale = g_s / g_s_ref
    J_CH4 = k_L_CH4 * g_s_scale * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2 * g_s_scale * (O2_eq - O2_cyt)
    # MMO activity
    Km_O2 = 0.001  # mmol/L
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) * (O2_cyt / (Km_O2 + O2_cyt))
    # Optional photosynthetic O₂ production
    O2_prod = 0.005 if photosynthesis_on else 0.0
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
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.05, 2.0, 0.5)
k_L_CH4 = st.sidebar.slider("CH₄ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.1)
k_L_O2 = st.sidebar.slider("O₂ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.03)

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of total protein)", 0.1, 20.0, 1.0, step=0.1)  # Indicates pMMO protein fraction, not currently linked to Vmax_ref
Vmax_ref = st.sidebar.slider("Vmax_ref (mmol/L/s)", 0.001, 0.1, 0.01, step=0.001)  # Base maximum rate from Baani and Liesack (2008) and Schmider et al. (2024). Conversion from per-cell to per-liter assuming methanotroph cell volume of ~1 fL.
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.00001, 0.005, 0.005, step=0.00001)  # Values and ranges based on Baani and Liesack (2008) and Schmider et al. (2024).

st.sidebar.header("Biomass Settings")
cytosol_fraction = st.sidebar.slider("Cytosol Fraction (% of cell volume)", 1, 100, 5) / 100  # Percent of total cell volume that is cytosol
active_volume = V_cell * cytosol_fraction  # L of active cytosol per cell, scaled per liter
scaling_factor = cytosol_fraction  # Fraction of cell volume that is active cytosol

# Input validation
error_message = None
if Km_ref <= 0:
    error_message = "Invalid input: Km_ref must be greater than 0."
elif Vmax_ref <= 0:
    error_message = "Invalid input: Vmax_ref must be greater than 0."
elif k_L_CH4 <= 0 or k_L_O2 <= 0:
    error_message = "Invalid input: Mass transfer coefficients (k_L) must be greater than 0."
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
time = np.linspace(0, 1000, 5000)
O2_init = H_0_O2 * np.exp(-0.02 * (T - 25)) * (1 - 0.01 * Pi) * (O2_atm / 100.0)
C0 = [0.0001, 0.0001, O2_init]

# Solve ODEs
def wrapped_ode(t, C):
    return methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                            k_L_CH4, k_L_O2, V_cell, scaling_factor, photosynthesis_on)
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

# Plots
fig_plots = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                          subplot_titles=("Cytosolic CH₄", "Methanol (CH₃OH)", "Cytosolic O₂"))
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode='lines', name="Cytosolic CH₄"), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode='lines', name="Methanol (CH₃OH)"), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode='lines', name="Cytosolic O₂"), row=3, col=1)
fig_plots.update_layout(height=800, title_text="Concentration Dynamics Over Time", showlegend=False)
fig_plots.update_xaxes(title_text="Time (s)", row=3, col=1)
for r in (1, 2, 3):
    fig_plots.update_yaxes(title_text="Concentration (mmol/L)", row=r, col=1)

# Final MMO rate (for gauge)
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

# Sensitivity Analysis
st.subheader("Sensitivity Analysis")
param_options = {
    "T": {"label": "Temperature (°C)", "range": np.linspace(5, 45, 20)},
    "expression_percent": {"label": "pMMO Expression (% of total protein)", "range": np.linspace(0.1, 20.0, 20)},
    "Vmax_ref": {"label": "Vmax_ref (mmol/L/s)", "range": np.linspace(0.001, 0.1, 20)},
    "Km_ref": {"label": "Km_ref (mmol/L)", "range": np.linspace(1e-6, 0.1, 20)},
    "Pi": {"label": "Cytosolic Osmolarity (%)", "range": np.linspace(0, 100, 20)},
    "g_s": {"label": "Stomatal Conductance (mol/m²/s)", "range": np.linspace(0.05, 2.0, 20)},
    "k_L_CH4": {"label": "CH₄ Mass Transfer Coefficient (1/s)", "range": np.linspace(0.0001, 0.1, 20)},
    "k_L_O2": {"label": "O₂ Mass Transfer Coefficient (1/s)", "range": np.linspace(0.0001, 0.1, 20)},
    "C_atm": {"label": "Atmospheric CH₄ (ppm)", "range": np.linspace(0.1, 10.0, 20)},
    "O2_atm": {"label": "Atmospheric O₂ (%)", "range": np.linspace(1.0, 25.0, 20)},
}

selected_param = st.selectbox("Select Parameter to Sweep", list(param_options.keys()),
                              format_func=lambda k: param_options[k]["label"])
if st.button("Run Sensitivity Analysis"):
    param_info = param_options[selected_param]
    param_range = param_info["range"]
    results = []
    for val in param_range:
        local_T = T if selected_param != "T" else val
        local_expression_percent = expression_percent if selected_param != "expression_percent" else val
        local_Vmax_ref = Vmax_ref if selected_param != "Vmax_ref" else val
        local_Km_ref = Km_ref if selected_param != "Km_ref" else val
        local_Pi = Pi if selected_param != "Pi" else val
        local_g_s = g_s if selected_param != "g_s" else val
        local_k_L_CH4 = k_L_CH4 if selected_param != "k_L_CH4" else val
        local_k_L_O2 = k_L_O2 if selected_param != "k_L_O2" else val
        local_scaling_factor = cytosol_fraction
        local_C_atm = C_atm if selected_param != "C_atm" else val
        local_O2_atm = O2_atm if selected_param != "O2_atm" else val
        local_O2_init = H_0_O2 * np.exp(-0.02 * (local_T - 25)) * (1 - 0.01 * local_Pi) * (local_O2_atm / 100.0)
        local_C0 = [0.0001, 0.0001, local_O2_init]
        sol_local = solve_ivp(
            fun=lambda t, C: methane_oxidation(
                C, t, local_C_atm, local_O2_atm, local_g_s, local_Vmax_ref, local_Km_ref,
                local_Pi, local_T, local_k_L_CH4, local_k_L_O2, V_cell, local_scaling_factor, photosynthesis_on
            ),
            t_span=(time[0], time[-1]),
            y0=local_C0,
            t_eval=time,
            method='LSODA',
            rtol=1e-6,
            atol=1e-9
        ).y.T
        local_C_cyt_final = sol_local[-1, 0]
        local_Km_T = local_Km_ref * (1 + 0.02 * (local_T - 25))
        local_Vmax_T = local_Vmax_ref * local_scaling_factor * np.exp(-E_a / R * (1/(local_T + 273.15) - 1/T_ref))
        local_Vmax_osm = local_Vmax_T * np.exp(-0.02 * (local_Pi / 100))
        local_O2_cyt_final = sol_local[-1, 2]
        Km_O2_local = 0.001
        local_V_MMO_final = local_Vmax_osm * (local_C_cyt_final / (local_Km_T + local_C_cyt_final)) * \
                            (local_O2_cyt_final / (Km_O2_local + local_O2_cyt_final))
        results.append((val, local_V_MMO_final))
    df = pd.DataFrame(results, columns=[param_info["label"], "Final CH₄ Oxidation Rate (mmol/L/s)"])
    fig_sa = go.Figure()
    fig_sa.add_trace(go.Scatter(x=df[param_info["label"]],
                                y=df["Final CH₄ Oxidation Rate (mmol/L/s)"],
                                mode="lines+markers"))
    fig_sa.update_layout(title=f"Sensitivity: {param_info['label']} vs. Final CH₄ Oxidation Rate",
                         xaxis_title=param_info["label"], yaxis_title="mmol/L/s")
    st.plotly_chart(fig_sa)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "sensitivity_analysis.csv", "text/csv")

# Model Constants and Equations
st.header("Model Constants and Equations")
st.subheader("Constants")
st.markdown(f"""
- **E_a**: 50,000 J/mol (Activation energy for MMO)
- **E_a_MeOH**: 45,000 J/mol (Activation energy for methanol oxidation)
- **R**: 8.314 J/mol/K (Gas constant)
- **T_ref**: 298.15 K (Reference temperature)
- **k_MeOH_ref**: 0.00011 1/s (Methanol oxidation rate at 25°C)
- **H_0_CH4**: 1.4 mmol/L/atm (Henry's constant for CH4 at 25°C)
- **H_0_O2**: 1.3 mmol/L/atm (Henry's constant for O2 at 25°C)
- **g_s_ref**: {g_s_ref} mol/m²/s (Reference stomatal conductance for flux scaling)
- **alpha**: 0.02 (Temperature factor for Henry's constants)
- **beta**: 0.01 (Osmolarity factor for Henry's constants)
- **Km_O2**: 0.001 mmol/L (Michaelis constant for O2)
- **O2_prod**: 0.005 mmol/L/s (Photosynthetic O2 production rate, if enabled)
- **baseline_cell_density**: 10 g/L (Baseline cell density for scaling)
- **V_cell**: 1e-15 L (Typical plant cell volume, currently unused)
""")
st.subheader("Key Equations")
st.latex(r"Vmax_T = Vmax_{ref} \times scaling\_factor \times \exp\left(-\frac{E_a}{R}\left(\frac{1}{T_K}-\frac{1}{T_{ref}}\right)\right)")
st.latex(r"Vmax = Vmax_T \times \exp(-0.02 \times (Pi / 100))")
st.latex(r"Km_T = Km_{ref} \times (1 + 0.02 \times (T - 25))")
st.latex(r"H = H_0 \times \exp(-\alpha (T - 25)) \times (1 - \beta \, Pi)")
st.latex(r"P_{CH4} = C_{atm}/10^6, \quad P_{O2} = O2_{atm}/100")
st.latex(r"C_{eq} = H \times P")
st.latex(r"J = k_L \times \left(\frac{g_s}{g_{s,ref}}\right) \times (C_{eq} - C)")
st.latex(r"V_{MMO} = Vmax \times \frac{C_{cyt}}{Km_T + C_{cyt}} \times \frac{O2_{cyt}}{Km_{O2} + O2_{cyt}}")
st.latex(r"\frac{dC_{cyt}}{dt} = J_{CH4} - V_{MMO}")
st.latex(r"\frac{dCH3OH}{dt} = V_{MMO} - k_{MeOH} \times CH3OH")
st.latex(r"\frac{dO2_{cyt}}{dt} = J_{O2} - V_{MMO} + O2_{prod}")

# Debug output
k_MeOH_scaled = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/(T + 273.15) - 1/T_ref))
st.sidebar.text(f"Temp-Adjusted k_MeOH: {k_MeOH_scaled:.6g} 1/s")
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
