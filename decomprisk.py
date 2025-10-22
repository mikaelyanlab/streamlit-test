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
    C = st.selectbox("Climate Zone", ["arid", "temperate", "humid"])

k_base = 0.1
C_factor = {"arid": 0.8, "temperate": 1.0, "humid": 1.2}

# Real-context biomes with sample areas (km²) and biome-specific sensitivities
biomes = pd.DataFrame({
    'biome': ['Arid Deserts', 'Temperate Forests', 'Humid Tropics'],
    'area_km2': [5000000, 10000000, 15000000],
    'baseline_risk': [0.3, 0.2, 0.15],
    'fuel_sens': [1.5, 1.0, 0.7],  # Higher fuel sensitivity in arid
    'moisture_sens': [0.5, 1.0, 1.5]  # Higher moisture benefit in humid
})

# Compute impacts per biome with non-linear sensitivities
impacts = []
for _, row in biomes.iterrows():
    zone = row['biome'].split()[0].lower()
    k_zone = k_base * (1 + 0.5 * B / 100) * D * C_factor[zone]
    F_zone = F * row['fuel_sens']  # Biome-specific fuel
    F_remaining_zone = F_zone * np.exp(-k_zone * 1)
    fire_intensity_base = F_zone ** 1.5
    fire_intensity_red_zone = F_remaining_zone ** 1.5
    pct_red_zone = (1 - fire_intensity_red_zone / fire_intensity_base) * 100
    delta_whc_zone = 5 * (k_zone * B / 100) * (M / 100) * row['moisture_sens']  # Scaled by sens
    score_zone = 5 * (1 - np.exp(-0.05 * k_zone * B * row['fuel_sens'])) + 2 * (M / 100)  # Non-linear
    adj_zone = - (2.0 * pct_red_zone + 1.0 * delta_whc_zone / 5 + 1.0 * score_zone / 5)
    total_impact = adj_zone * row['area_km2'] * row['baseline_risk'] / 100
    impacts.append({'biome': row['biome'], 'risk_reduction_%': adj_zone, 'total_impact': total_impact})

df_impacts = pd.DataFrame(impacts)

k_val = k_base * (1 + 0.5 * B / 100) * D * C_factor[C]
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
        kk = k_base * (1 + 0.5 * b / 100) * D * C_factor[C]
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

    # Bar chart: Ecological impact by biome (now with varying relative heights)
    fig_bar = px.bar(df_impacts, x='biome', y='total_impact',
                     labels={'total_impact': 'Total Liability Reduction ($M equiv.)', 'biome': 'Biome'},
                     title="Ecological Impact Across Biomes")
    st.plotly_chart(fig_bar, use_container_width=True)
