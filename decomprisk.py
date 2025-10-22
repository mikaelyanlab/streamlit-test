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

# Biomes with sensitivities
biomes = pd.DataFrame({
    'biome': ['Arid Deserts', 'Temperate Forests', 'Humid Tropics'],
    'area_km2': [5000000, 10000000, 15000000],
    'baseline_risk': [0.3, 0.2, 0.15],
    'fuel_sens': [1.5, 1.0, 0.7],
    'moisture_sens': [0.5, 1.0, 1.5]
})

# Baseline (B=0, fixed)
baseline_impacts = []
for _, row in biomes.iterrows():
    zone = row['biome'].split()[0].lower()
    k_base_zone = k_base * (1 + 0.5 * 0 / 100) * 1.0 * C_factor[zone]
    F_zone_base = 25.0 * row['fuel_sens']  # Fixed F=25
    fire_base = F_zone_base ** 1.5
    pct_red_base = 0  # No reduction at B=0
    delta_whc_base = 0
    score_base = 2 * (50 / 100)  # Fixed M=50
    adj_base = - (2.0 * pct_red_base + 1.0 * delta_whc_base / 5 + 1.0 * score_base / 5)
    total_base = fire_base * row['area_km2'] * row['baseline_risk']  # Absolute baseline liability
    baseline_impacts.append({'biome': row['biome'], 'baseline_liability': total_base})

df_baseline = pd.DataFrame(baseline_impacts)

# Current impacts
current_impacts = []
for _, row in biomes.iterrows():
    zone = row['biome'].split()[0].lower()
    k_zone = k_base * (1 + 0.5 * B / 100) * D * C_factor[zone]
    F_zone = F * row['fuel_sens']
    F_remaining_zone = F_zone * np.exp(-k_zone * 1)
    fire_intensity_base = F_zone ** 1.5
    fire_intensity_red_zone = F_remaining_zone ** 1.5
    pct_red_zone = (1 - fire_intensity_red_zone / fire_intensity_base) * 100
    delta_whc_zone = 5 * (k_zone * B / 100) * (M / 100) * row['moisture_sens']
    score_zone = 5 * (1 - np.exp(-0.05 * k_zone * B * row['fuel_sens'])) + 2 * (M / 100)
    adj_zone = - (2.0 * pct_red_zone + 1.0 * delta_whc_zone / 5 + 1.0 * score_zone / 5)
    total_reduction = (adj_zone / 100) * fire_intensity_base * row['area_km2'] * row['baseline_risk']
    current_impacts.append({'biome': row['biome'], 'reduction': total_reduction})

df_current = pd.DataFrame(current_impacts)

# Combine for grouped bar
df_plot = pd.merge(df_baseline, df_current, on='biome')
df_plot = pd.melt(df_plot, id_vars='biome', value_vars=['baseline_liability', 'reduction'],
                  var_name='type', value_name='value')
df_plot['type'] = df_plot['type'].replace({'baseline_liability': 'Baseline Liability', 'reduction': 'Reduction'})

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

    # Grouped bar: Baseline vs Reduction by biome
    fig_bar = px.bar(df_plot, x='biome', y='value', color='type',
                     barmode='group',
                     labels={'value': 'Liability ($M equiv.)', 'biome': 'Biome', 'type': 'Metric'},
                     title="Baseline Liability vs Achieved Reduction by Biome")
    st.plotly_chart(fig_bar, use_container_width=True)
