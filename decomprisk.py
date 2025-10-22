import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.title("Decomposer Biodiversity Risk Model")

# Inputs
B = st.slider("Biodiversity Index", 0, 100, 50)
D = st.slider("Decomp Rate Factor", 0.5, 2.0, 1.0)
F = st.slider("Fuel Load (kg/m²)", 5.0, 50.0, 25.0)
M = st.slider("Soil Moisture (%)", 10, 90, 50)
C = st.selectbox("Climate Zone", ["arid", "temperate", "humid"])

# Constants
k_base = 0.1
C_factor = {"arid": 0.8, "temperate": 1.0, "humid": 1.2}

# Calculations
k = k_base * (1 + 0.5 * B / 100) * D * C_factor[C]
F_remaining = F * np.exp(-k * 1)
fire_intensity_base = F ** 1.5
fire_intensity_red = F_remaining ** 1.5
pct_red = (1 - fire_intensity_red / fire_intensity_base) * 100
delta_whc = 5 * (k * B / 100) * (M / 100)
score = 5 * (1 - np.exp(-0.05 * k * B)) + 2 * (M / 100)
adj = - (0.4 * pct_red + 0.3 * delta_whc / 10 + 0.2 * score / 10)

# Outputs
st.metric("Reduced Wildfire Intensity (%)", f"{pct_red:.1f}")
st.metric("Improved Water Retention (mm)", f"{delta_whc:.1f}")
st.metric("Erosion Resistance Score", f"{score:.1f}")
st.metric("Risk Liability Adjustment (%)", f"{adj:.1f}")

# Graph: Risk vs Biodiversity
biodiversity_range = np.linspace(0, 100, 50)
risks = []
for b in biodiversity_range:
    kk = k_base * (1 + 0.5 * b / 100) * D * C_factor[C]
    ff_rem = F * np.exp(-kk * 1)
    ii_base = F ** 1.5
    ii_red = ff_rem ** 1.5
    p_red = (1 - ii_red / ii_base) * 100
    d_whc = 5 * (kk * b / 100) * (M / 100)
    sc = 5 * (1 - np.exp(-0.05 * kk * b)) + 2 * (M / 100)
    rr = - (0.4 * p_red + 0.3 * d_whc / 10 + 0.2 * sc / 10)
    risks.append(rr)

fig = px.line(x=biodiversity_range, y=risks, labels={"x": "Biodiversity Index", "y": "Risk Adjustment (%)"},
              title="Risk Liability vs Biodiversity")
st.plotly_chart(fig)
