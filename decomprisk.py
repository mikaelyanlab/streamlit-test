import streamlit as st
import numpy as np
import plotly.express as px
import pandas as pd

st.title("Decomposer Biodiversity Risk Model")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Controls")
    B = st.slider("Biodiversity Index (0-100)", 0, 100, 50)
    D = st.slider("Decomposition Rate Factor (0.5-2.0x)", 0.5, 2.0, 1.0)
    F = st.slider("Fuel Load (kg/m²)", 5.0, 50.0, 25.0)
    M = st.slider("Soil Moisture (%)", 10, 90, 50)

countries = ['USA', 'CAN', 'BRA', 'FRA', 'ZAF', 'AUS', 'CHN', 'IND', 'RUS', 'EGY']

# Country-specific fuel multipliers (higher for fire-prone)
fuel_mult = {'USA': 1.5, 'CAN': 1.2, 'BRA': 1.0, 'FRA': 0.8, 'ZAF': 1.3, 'AUS': 2.0, 'CHN': 1.1, 'IND': 0.9, 'RUS': 1.4, 'EGY': 1.6}

k_base = 0.1
k = k_base * (1 + 0.5 * B / 100) * D

# Per-country risk_adj with multipliers
base_values = np.array([fuel_mult[c] for c in countries])
risk_adj = base_values * (1 + 10 * k) * (1 - M/100) * (F/50)  # Now varies uniquely

df_map = pd.DataFrame({
    'iso_alpha': countries,
    'risk': risk_adj
})

k_val = k_base * (1 + 0.5 * B / 100) * D
F_remaining = F * np.exp(-k_val * 1)
fire_intensity_base = F ** 1.5
fire_intensity_red = F_remaining ** 1.5
pct_red = (1 - fire_intensity_red / fire_intensity_base) * 100
delta_whc = 5 * (k_val * B / 100) * (M / 100)
score = 5 * (1 - np.exp(-0.05 * k_val * B)) + 2 * (M / 100)
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

    fig_line = px.line(x=biodiversity_range, y=risks, labels={"x": "Biodiversity Index", "y": "Risk Adjustment (%)"},
                       title="Risk Liability vs Biodiversity")
    st.plotly_chart(fig_line, use_container_width=True)

    # Dynamic map
    fig_map = px.choropleth(df_map, locations="iso_alpha",
                            color="risk",
                            locationmode='ISO-3',
                            color_continuous_scale="RdYlGn_r",
                            labels={'risk': 'Risk Adj'},
                            title="Dynamic Risk Map")
    st.plotly_chart(fig_map, use_container_width=True)
