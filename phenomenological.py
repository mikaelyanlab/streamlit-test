# Aram Mikaelyan, NCSU | Streamlit App: Methane Oxidation Model with Photosynthesis
import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Constants ---
E_a = 50e3         # J/mol for MMO; activation energy from typical enzyme kinetics
E_a_MeOH = 45e3    # J/mol for methanol oxidation
R = 8.314          # Gas constant, J/mol/K
T_ref = 298.15     # Reference temperature, K
k_MeOH_ref = 0.00011  # 1/s at 25°C; methanol oxidation rate constant

# Henry's constants in mmol/L/atm (adjusted for model units)
# Source: Sander (2015) compilation: https://acp.copernicus.org/articles/15/4399/2015/acp-15-4399-2015.pdf
H_0_CH4 = 1.4      # mmol/L/atm for CH4 at 25°C
H_0_O2 = 1.3       # mmol/L/atm for O2 at 25°C

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      k_L_CH4, k_L_O2, V_cell, scaling_factor, photosynthesis_on):
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

    # Partial pressures (in atm, assuming total P=1 atm; g_s scales effective flux)
    P_CH4 = g_s * (C_atm / 1e6)  # Corrected for ppm to mole fraction
    P_O2 = g_s * (O2_atm / 100.0)  # % to fraction

    # Equilibrium concentrations (mmol/L)
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2

    # Fluxes
    J_CH4 = k_L_CH4 * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2 * (O2_eq - O2_cyt)

    # MMO activity
    # Km_O2 from literature on pMMO: ~1-2 µM (0.001-0.002 mmol/L)
    # Source: Semrau et al. (2010): https://www.pnas.org/doi/10.1073/pnas.0702643105
    Km_O2 = 0.001  # mmol/L
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) * (O2_cyt / (Km_O2 + O2_cyt))

    # Optional photosynthetic O₂ production
    # Volumetric rate ~0.001-0.01 mmol/L/s based on leaf rates (10-30 µmol/m²/s, ~200 µm thickness)
    # Source: Flexas et al. (2018): https://academic.oup.com/pcp/article/59/6/1072/5026149
    O2_prod = 0.005 if photosynthesis_on else 0  # mmol/L/s, lowered for conservatism

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
k_L_CH4 = st.sidebar.slider("CH₄ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.01)
# Source for k_L: Plant gas exchange models, e.g., Defraeye et al. (2014): https://www.sciencedirect.com/science/article/pii/S0017931013004372
k_L_O2 = st.sidebar.slider("O₂ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.03)

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of total cell protein)", 0.1, 5.0, 1.0, step=0.1)
baseline_vmax_at_10_percent = 0.001  # mmol/L/s at 10% expression, from Schmider et al. (2024)
# Source: https://www.nature.com/articles/s41467-024-48197-1
Vmax_ref = baseline_vmax_at_10_percent * (expression_percent / 10.0)
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.0, 0.1, 5e-5, step=1e-6)
# Updated range/default for pMMO high affinity: 0.0-0.1 mmol/L (allowing 0 for testing)
# Source: Hakobyan et al. (2005) and Schmider et al. (2024): links above

st.sidebar.header("Biomass Settings")
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)
baseline_cell_density = 0.7
cytosol_fraction = 0.03  # 3% of cell volume; fixed for simplicity, but pMMO is membrane-bound
active_volume = cellular_material * cytosol_fraction  # g/L
scaling_factor = active_volume / baseline_cell_density

V_cell = 1e-15  # Plant cell volume (L); currently unused, for potential scaling

# Input validation
error_message = None
if Km_ref <= 0:
    error_message = "Invalid input: Km_ref must be greater than 0 to avoid undefined enzyme kinetics."
elif k_L_CH4 <= 0 or k_L_O2 <= 0:
    error_message = "Invalid input: Mass transfer coefficients (k_L) must be greater than 0."
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
elif T < -273.15:  # Absolute zero check, though slider min is 5
    error_message = "Invalid input: Temperature must be above absolute zero (-273.15°C)."
# Add more checks as needed for unrealistic values, e.g., Pi > 100 or T > 100 for biological realism

if error_message:
    st.error(error_message)
    st.stop()

# Time and initial conditions
time = np.linspace(0, 100, 5000)
O2_init = H_0_O2 * np.exp(-0.02 * (T - 25)) * (1 - 0.01 * Pi) * (O2_atm / 100.0)
C0 = [0.0001, 0.0001, O2_init]  # Lowered initials for ambient realism (mmol/L)

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

# Create three separate subplots with Plotly for interactive viewing
fig_plots = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                          subplot_titles=("Cytosolic CH₄", "Methanol (CH₃OH)", "Cytosolic O₂"))

# Add traces
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode='lines', name="Cytosolic CH₄"), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode='lines', name="Methanol (CH₃OH)"), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode='lines', name="Cytosolic O₂"), row=3, col=1)

# Update layout
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
    number={'suffix': " mmol/L/s", 'valueformat': '.10g'},  # Use valueformat for precision
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 1e-6]},  # Finer range to capture small rates
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

# Add list of constants and equations for transparency
st.header("Model Constants and Equations")

st.subheader("Constants")
st.markdown("""
- **E_a**: 50,000 J/mol (Activation energy for MMO)
- **E_a_MeOH**: 45,000 J/mol (Activation energy for methanol oxidation)
- **R**: 8.314 J/mol/K (Gas constant)
- **T_ref**: 298.15 K (Reference temperature)
- **k_MeOH_ref**: 0.00011 1/s (Methanol oxidation rate at 25°C)
- **H_0_CH4**: 1.4 mmol/L/atm (Henry's constant for CH4 at 25°C)
- **H_0_O2**: 1.3 mmol/L/atm (Henry's constant for O2 at 25°C)
- **alpha**: 0.02 (Temperature adjustment factor for Henry's constants)
- **beta**: 0.01 (Osmolarity adjustment factor for Henry's constants)
- **Km_O2**: 0.001 mmol/L (Michaelis constant for O2)
- **O2_prod**: 0.005 mmol/L/s (Photosynthetic O2 production rate, if enabled)
- **cytosol_fraction**: 0.03 (Fraction of cell volume that is cytosol)
- **baseline_vmax_at_10_percent**: 0.001 mmol/L/s (Baseline Vmax at 10% protein expression)
- **baseline_cell_density**: 0.7 g/L (Baseline cell density for scaling)
- **V_cell**: 1e-15 L (Typical plant cell volume, currently unused)
""")

st.subheader("Key Equations")
st.latex(r"Vmax_T = Vmax_{ref} \times scaling_factor \times \exp\left(-\frac{E_a}{R} \left(\frac{1}{T_K} - \frac{1}{T_{ref}}\right)\right)")
st.latex(r"Vmax = Vmax_T \times \exp(-0.02 \times (Pi / 100))")
st.latex(r"Km_T = Km_{ref} \times (1 + 0.02 \times (T - 25))")
st.latex(r"H = H_0 \times \exp(-\alpha \times (T - 25)) \times (1 - \beta \times Pi)")
st.latex(r"P_{CH4} = g_s \times (C_{atm} / 10^6), \quad P_{O2} = g_s \times (O2_{atm} / 100)")
st.latex(r"C_{eq} = H \times P")
st.latex(r"J = k_L \times (C_{eq} - C)")
st.latex(r"V_{MMO} = Vmax \times \frac{C_{cyt}}{Km_T + C_{cyt}} \times \frac{O2_{cyt}}{Km_{O2} + O2_{cyt}}")
st.latex(r"\frac{dC_{cyt}}{dt} = J_{CH4} - V_{MMO}")
st.latex(r"\frac{dCH3OH}{dt} = V_{MMO} - k_{MeOH} \times CH3OH")
st.latex(r"\frac{dO2_{cyt}}{dt} = J_{O2} - V_{MMO} + O2_{prod}")

# Debug output
k_MeOH_scaled = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/(T + 273.15) - 1/T_ref))
st.sidebar.text(f"Temp-Adjusted k_MeOH: {k_MeOH_scaled:.6g} 1/s")
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
