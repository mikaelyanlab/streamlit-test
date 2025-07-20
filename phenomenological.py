import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Plant Cell MMO Methane Oxidation Model")

# --- Sidebar sliders ---
st.sidebar.header("Adjust Parameters")
Vmax_ref = st.sidebar.slider("Vmax_ref (mmol/L/s)", 0.0001, 0.01, 0.001)
K_CH4 = st.sidebar.slider("K_CH4 (mmol/L)", 0.001, 1.0, 0.01)
K_O2 = st.sidebar.slider("K_O2 (mmol/L)", 0.001, 1.0, 0.01)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.01, 1.0, 0.3)
O2_env = st.sidebar.slider("Atmospheric O₂ (mmol/L)", 0.1, 0.3, 0.21)
CH4_env = st.sidebar.slider("Atmospheric CH₄ (mmol/L)", 1e-5, 1e-3, 2e-4, format="%.5f")
k_L = st.sidebar.slider("Gas Transfer Coefficient k_L (1/s)", 0.0001, 0.01, 0.001)
k_MeOH = st.sidebar.slider("Methanol Decay Rate (1/s)", 1e-6, 0.01, 0.001, format="%.6f")

# --- Time vector ---
t = np.linspace(0, 100, 1000)

# --- Initial conditions ---
C_CH4_0 = 0.01
C_O2_0 = 0.01
C_MeOH_0 = 0.0

# --- Placeholder arrays ---
C_CH4 = np.zeros_like(t)
C_O2 = np.zeros_like(t)
C_MeOH = np.zeros_like(t)
V_MMO_series = np.zeros_like(t)

C_CH4[0] = C_CH4_0
C_O2[0] = C_O2_0
C_MeOH[0] = C_MeOH_0
dt = t[1] - t[0]

for i in range(1, len(t)):
    V_MMO = Vmax_ref * (C_CH4[i-1] / (K_CH4 + C_CH4[i-1])) * (C_O2[i-1] / (K_O2 + C_O2[i-1]))
    V_MMO_series[i] = V_MMO
    dCH4 = (k_L * (CH4_env - C_CH4[i-1]) - V_MMO) * dt
    dO2 = (g_s * (O2_env - C_O2[i-1]) - V_MMO) * dt
    dMeOH = (V_MMO - k_MeOH * C_MeOH[i-1]) * dt

    C_CH4[i] = max(C_CH4[i-1] + dCH4, 0)
    C_O2[i] = max(C_O2[i-1] + dO2, 0)
    C_MeOH[i] = max(C_MeOH[i-1] + dMeOH, 0)

# --- Plot ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=t, y=C_CH4, mode='lines', name="Cytosolic CH₄"))
fig.add_trace(go.Scatter(x=t, y=C_MeOH, mode='lines', name="Methanol (CH₃OH)"))
fig.add_trace(go.Scatter(x=t, y=C_O2, mode='lines', name="Cytosolic O₂"))
fig.update_layout(title="Concentration Dynamics", xaxis_title="Time (s)", yaxis_title="Concentration (mmol/L)",
                  width=700, height=500)

# --- Gauge ---
final_rate = V_MMO_series[-1]
gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=final_rate,
    title={'text': "Final CH₄ Oxidation Rate"},
    number={'suffix': " mmol/L/s"},
    gauge={
        'axis': {'range': [0, 0.25]},
        'bar': {'color': "black"},
        'steps': [
            {'range': [0, 0.05], 'color': '#fdd'},
            {'range': [0.05, 0.1], 'color': '#faa'},
            {'range': [0.1, 0.15], 'color': '#f66'},
            {'range': [0.15, 0.2], 'color': '#d00'},
            {'range': [0.2, 0.25], 'color': '#800'}
        ]
    }
))
gauge.update_layout(width=400, height=400)

# --- Display ---
col1, col2 = st.columns([3, 1])
with col1:
    st.plotly_chart(fig)
with col2:
    st.plotly_chart(gauge)
    st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
