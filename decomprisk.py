import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

st.title("Decomposer Biodiversity Risk Model")

# Layout: sliders in left column, output + map on right
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Controls")
    B = st.slider("Biodiversity Index (0-100)", 0, 100, 50)
    D = st.slider("Decomposition Rate Factor (0.5-2.0x)", 0.5, 2.0, 1.0)
    F = st.slider("Fuel Load (kg/m²)", 5.0, 50.0, 25.0)
    M = st.slider("Soil Moisture (%)", 10, 90, 50)

with col2:
    st.header("Outputs")

    # List of representative countries
    countries = ['USA', 'CAN', 'BRA', 'FRA', 'ZAF', 'AUS', 'CHN', 'IND', 'RUS', 'EGY']
    base_values = np.linspace(10, 30, len(countries))

    # Compute a simple risk adjustment value for each country
    k_base = 0.1
    k = k_base * (1 + 0.5 * B / 100) * D
    risk_adj = base_values * (1 + k) * (1 - M / 100) * (F / 50)

    # Build dataframe
    df_map = pd.DataFrame({
        'iso_alpha': countries,
        'risk': risk_adj
    })

    # Show numerical summaries
    avg_risk = np.mean(risk_adj)
    st.metric("Average Risk Adjustment", f"{avg_risk:.2f}")

    # Create dynamic world map
    fig_map = go.Figure(data=go.Choropleth(
        locations=df_map['iso_alpha'],
        z=df_map['risk'],
        locationmode='ISO-3',
        colorscale='RdYlGn_r',
        colorbar_title="Risk Adj (%)"
    ))

    fig_map.update_layout(
        title="Global Risk Adjustment Based on Decomposer Dynamics",
        geo=dict(showframe=False, showcoastlines=False)
    )

    st.plotly_chart(fig_map, use_container_width=True)
