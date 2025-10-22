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

# Sample country data for map (ISO3 codes grouped by approximate climate zone)
countries_data = {
    'arid': ['AUS', 'SAU', 'EGY', 'IRQ', 'ARE', 'LBY', 'DZA', 'AFG', 'PAK', 'MNG', 'CHL', 'PER', 'NAM'],
    'temperate': ['GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'PRT', 'GRC', 'TUR', 'JPN', 'KOR', 'USA', 'CAN', 'ARG'],
    'humid': ['BRA', 'COL', 'ECU', 'VEN', 'IDN', 'MYS', 'SGP', 'PHL', 'VNM', 'THA', 'SSD', 'TZA', 'KEN']
}

# Create df for map
df_map = []
for zone, isos in countries_data.items():
    for iso in isos:
        df_map.append({'iso_alpha': iso, 'climate': zone})
df_map = pd.DataFrame(df_map)

# Constants
k_base = 0.1
C_factor = {"arid": 0.8, "temperate": 1.0, "humid": 1.2}

# Compute adj for each zone
adj_per_zone = {}
for zone in C_factor.keys():
    k_zone = k_base * (1 + 0.5 * B / 100) * D * C_factor[zone]
    F_remaining_zone = F * np.exp(-k_zone * 1)
    fire_intensity_base = F ** 1.5
    fire_intensity_red_zone = F_remaining_zone ** 1.5
    pct_red_zone = (1 - fire_intensity_red_zone / fire_intensity_base) * 100
    delta_whc_zone = 5 * (k_zone * B / 100) * (M / 100)
    score_zone = 5 * (1 - np.exp(-0.05 * k_zone * B)) + 2 * (M / 100)
    adj_zone = - (0.4 * pct_red_zone + 0.3 * delta_whc_zone / 10 + 0.2 * score_zone / 10)
    adj_per_zone[zone] = adj_zone

# Set risk_adj per climate
df_map['risk_adj'] = df_map['climate'].map(adj_per_zone)

# Calculations for selected C
k = k_base * (1 + 0.5 * B / 100) * D * C_factor[C]
F_remaining = F * np.exp(-k * 1)
fire_intensity_base = F ** 1.5
fire_intensity_red = F_remaining ** 1.5
pct_red = (1 - fire_intensity_red / fire_intensity_base) * 100
delta_whc = 5 * (k * B / 100) * (M / 100)
score = 5 * (1 - np.exp(-0.05 * k * B)) + 2 * (M / 100)
adj = adj_per_zone[C]

with col2:
    st.header("Outputs")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Reduced Wildfire Intensity (%)", f"{pct_red:.1f}")
        st.metric("Improved Water Retention (mm)", f"{delta_whc:.1f}")
    with col_b:
        st.metric("Erosion Resistance Score", f"{score:.1f}")
        st.metric("Risk Liability Adjustment (%)", f"{adj:.1f}")

    # Graph: Risk vs Biodiversity (for selected zone)
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

    fig_line = px.line(x=biodiversity_range, y=risks, labels={"x": "Biodiversity Index", "y": "Risk Adjustment (%)"},
                       title="Risk Liability vs Biodiversity")
    st.plotly_chart(fig_line, use_container_width=True)

    # World Map: Biomes colored by risk adjustment (heatmap-style choropleth)
    fig_map = px.choropleth(df_map, locations="iso_alpha",
                            color="risk_adj",
                            color_continuous_scale="RdYlGn_r",
                            labels={'risk_adj': 'Risk Adjustment (%)'},
                            title="Global Risk Reduction by Biomes (Heatmap)")
    fig_map.update_layout(coloraxis_colorbar=dict(title="Risk Adj (%)"))
    st.plotly_chart(fig_map, use_container_width=True)
