# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU 
# Methane Oxidation Model with Sensitivity Analysis (Streamlit App)

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# Arrhenius parameters
E_a = 50e3  # Activation energy in J/mol
R = 8.314  # Universal gas constant J/(mol*K)
T_ref = 298.15  # Reference temperature (25C in Kelvin)

# Methane oxidation model

def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell, scaling_factor):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15
    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    k_osm = 0.02
    Vmax = Vmax_T * np.exp(-k_osm * (Pi / 100))
    H_0 = 1.4
    alpha = 0.02
    beta = 0.01
    k_MeOH = 0.000011
    C_atm_mmolL = C_atm * 0.0409
    H_CH4 = H_0 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    P_CH4 = g_s * (C_atm / 1.0)
    C_cyt_eq = H_CH4 * P_CH4
    J_CH4 = k_L * (C_cyt_eq - C_cyt)
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))
    dO2_dt = -V_MMO
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# Streamlit UI
st.title("Methane Oxidation Model with Enzyme Sensitivity")
st.sidebar.header("Adjust Model Parameters")

C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
g_s = st.sidebar.slider("Stomatal Conductance (gₛ, mol/m²/s)", 0.01, 0.2, 0.05)
log_vmax = st.sidebar.slider("log₁₀(Max pMMO Activity, mmol/L/s)", -3.0, math.log10(2.0), -1.0, step=0.1)
Vmax_ref = 10 ** log_vmax
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
O2 = st.sidebar.slider("Cytosolic O₂ (mmol/L)", 0.01, 2.0, 0.5)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)", 0.001, 0.1, 0.01)
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)

# Derived values
baseline_cell_density = 0.7
scaling_factor = cellular_material / baseline_cell_density
V_cell = 1e-15  # L

# Time and initial conditions
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1, O2]

# Solve model
sol = odeint(methane_oxidation, C0, time, args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell, scaling_factor))

# Plot concentrations
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="Cytosolic CH₄")
ax.plot(time, sol[:, 1], label="Methanol")
ax.plot(time, sol[:, 2], label="O₂ Consumption")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()

# Display primary output
st.pyplot(fig)

# Compute final oxidation rate
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1 / (T + 273.15) - 1 / T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
C_cyt_final = sol[-1, 0]
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final))

# Gauge for oxidation rate
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s"},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 0.3]},
        'bar': {'color': "#ffcc00"},
        'steps': [
            {'range': [0.0, 0.03], 'color': "#eee"},
            {'range': [0.03, 0.1], 'color': "#ddd"},
            {'range': [0.1, 0.2], 'color': "#bbb"},
            {'range': [0.2, 0.3], 'color': "#999"},
        ],
        'threshold': {'line': {'color': "black", 'width': 4}, 'value': V_MMO_final}
    }
))

col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

# Sensitivity Analysis Section
st.markdown("## 🔍 Sensitivity Analysis")
with st.expander("Run One-at-a-Time Sensitivity Analysis"):
    parameter_to_vary = st.selectbox("Choose parameter to vary", [
        "Vmax_ref", "Km_ref", "g_s", "C_atm", "Pi", "T", "k_L", "cellular_material"
    ])
    run_analysis = st.button("Run Sensitivity Analysis")

    if run_analysis:
        st.info("Running simulations...")
        param_ranges = {
            "Vmax_ref": np.logspace(-3, math.log10(2.0), 20),
            "Km_ref": np.linspace(0.1, 2.0, 20),
            "g_s": np.linspace(0.01, 0.2, 20),
            "C_atm": np.linspace(0.1, 10.0, 20),
            "Pi": np.linspace(0, 100, 20),
            "T": np.linspace(5, 45, 20),
            "k_L": np.linspace(0.001, 0.1, 20),
            "cellular_material": np.linspace(0.1, 200.0, 20)
        }

        param_values = param_ranges[parameter_to_vary]
        VMMO_values = []

        for val in param_values:
            local = {
                "Vmax_ref": Vmax_ref,
                "Km_ref": Km_ref,
                "g_s": g_s,
                "C_atm": C_atm,
                "Pi": Pi,
                "T": T,
                "k_L": k_L,
                "cellular_material": cellular_material,
                "O2": O2
            }
            local[parameter_to_vary] = val

            scaling = local["cellular_material"] / baseline_cell_density
            Km_T_sens = local["Km_ref"] * (1 + 0.02 * (local["T"] - 25))
            Vmax_T_sens = local["Vmax_ref"] * scaling * np.exp(-E_a / R * (1 / (local["T"] + 273.15) - 1 / T_ref))
            Vmax_osm_sens = Vmax_T_sens * np.exp(-0.02 * (local["Pi"] / 100))

            sol_sens = odeint(methane_oxidation, C0, time, args=(
                local["C_atm"], local["g_s"], local["Vmax_ref"], local["Km_ref"],
                local["Pi"], local["O2"], local["T"], local["k_L"], V_cell, scaling
            ))

            C_cyt_final_sens = sol_sens[-1, 0]
            V_MMO_final_sens = Vmax_osm_sens * (C_cyt_final_sens / (Km_T_sens + C_cyt_final_sens))
            VMMO_values.append(V_MMO_final_sens)

        df_sens = pd.DataFrame({parameter_to_vary: param_values, "CH₄ Oxidation Rate (mmol/L/s)": VMMO_values})

        fig_sens, ax_sens = plt.subplots()
        ax_sens.plot(param_values, VMMO_values, marker='o', color='green')
        ax_sens.set_xlabel(parameter_to_vary)
        ax_sens.set_ylabel("Final CH₄ Oxidation Rate (mmol/L/s)")
        ax_sens.set_title(f"Sensitivity to {parameter_to_vary}")
        st.pyplot(fig_sens)

        csv = df_sens.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name=f"sensitivity_{parameter_to_vary}.csv", mime='text/csv')

        st.dataframe(df_sens)

st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
