import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

st.title("Decomposer Biodiversity Risk Model")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Controls")
    B = st.slider("Biodiversity Index (0-100)", 0, 100, 50)
    D = st.slider("Decomposition Rate Factor (0.5-2.0x)", 0.5, 2.0, 1.0)
    F = st.slider("Fuel Load (kg/m²)", 5.0, 50.0, 25.0)
    M = st.slider("Soil Moisture (%)", 10, 90, 50)
    C = st.selectbox("Climate Zone", ["arid", "temperate", "humid"])

countries = ['USA', 'CAN', 'BRA', 'FRA', 'ZAF', 'AUS', 'CHN', 'IND', 'RUS', 'EGY']

k_base = 0.1
k = k_base * (1 + 0.5 * B / 100) * D

# Compute artificial risk value for each country (just for visualization)
base_values = np.linspace(10, 30, len(countries))
risk_adj = base_values * (1 + k) * (1 - M/100) * (F/50)

df_map = pd.DataFrame({
    'iso_alpha': countries,
    'risk': risk_adj
})

k = k_base * (1 + 0.5 * B / 100) * D
F_remaining = F * np.exp(-k * 1)
fire_intensity_base = F ** 1.5
fire_intensity_red = F_remaining ** 1.5
pct_red = (1 - fire_intensity_red / fire_intensity_base) * 100
delta_whc = 5 * (k * B / 100) * (M / 100)
score = 5 * (1 - np.exp(-0.05 * k * B)) + 2 * (M / 100)
adj = - (2.0 * pct_red + 1.0 * delta_whc / 5 + 1.0 * score / 5)

with col2:
    st.header("Outputs")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Reduced Wildfire Intensity (%)", f"{pct_red:.1f}")
        st.metric("Improved Water Retention (mm)", f"{delta_whc:.1f}")
    with col_b:
        st.metric("Erosion Resistance Score", f"{score:.1f}")
        st.metric("Risk Liability Adjustment (%)", f"{adj:.1f}")

    biodiversity_range = np.linspace(0, 100, 50)
    risks = []
    for b in biodiversity_range:
        kk = k_base * (1 + 0.5 * b / 100) * D
        ff_rem = F * np.exp(-kk * 1)
        ii_base = F ** 1.5
        ii_red = ff_rem ** 1.5
        p_red = (1 - ii_red / ii_base) * 100
        d_whc = 5 * (kk * b / 100) * (M / 100)
        sc = 5 * (1 - np.exp(-0.05 * kk * b)) + 2 * (M / 100)
        rr = - (2.0 * p_red + 1.0 * d_whc / 5 + 1.0 * sc / 5)
        risks.append(rr)

    import plotly.express as px
    fig_line = px.line(x=biodiversity_range, y=risks, labels={"x": "Biodiversity Index", "y": "Risk Adjustment (%)"},
                       title="Risk Liability vs Biodiversity")
    st.plotly_chart(fig_line, use_container_width=True)

    fig_map = go.Figure(data=go.Choropleth(
        locations=df_map['iso_alpha'],
        z=df_map['risk'],
        locationmode='ISO-3',
        colorscale='RdYlGn_r',
        colorbar_title="Risk Adj (%)"
    ))

    fig_map.update_layout(
        title="Updated Risk Map Based on Decomposition Model",
        geo=dict(showframe=False, showcoastlines=False)
    )
    st.plotly_chart(fig_map, use_container_width=True)
