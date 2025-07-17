# Aram Mikaelyan, NCSU | Impact Layer Model for Methane Oxidation

import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("Methane Oxidation Impact Model")
st.sidebar.header("Adjust Parameters")

# Sliders for fixed parameters
ox_rate = st.sidebar.slider("Instantaneous CH₄ Oxidation Rate (mmol/L/s)", 0.0, 10.0, 1.0)
active_density = st.sidebar.slider("Active Cellular Density (%)", 0, 100, 10)
plant_density = st.sidebar.slider("Plant Density (plants/m²)", 0.1, 100.0, 10.0)
stomatal_open = st.sidebar.slider("Stomatal Opening Period (hours/day)", 0.0, 24.0, 12.0)
growing_days = st.sidebar.slider("Growing Days per Year", 0, 365, 200)
total_adoption = st.sidebar.slider("Total Adoption Area (ha)", 0.0, 5e9, 1e6)

# Constants
g_per_mmol = 0.01604  # g CH₄/mmol

# Range of leaf biomass values to plot
biomass_range = np.linspace(0.1, 10, 100)
impact_output3 = []

for B in biomass_range:
    output2 = ox_rate * (active_density / 100) * B * (stomatal_open * 3600) * g_per_mmol
    output3 = output2 * growing_days * total_adoption * 1000 * 1e-6  # tonnes/year
    impact_output3.append(output3)

# Plotly chart
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=biomass_range,
    y=impact_output3,
    mode='lines+markers',
    line=dict(color='green'),
    name='Global CH₄ Oxidation'
))
fig.update_layout(
    title="Effect of Leaf Biomass on Annual Global Methane Oxidation",
    xaxis_title="Green Leaf Biomass (kg/m²)",
    yaxis_title="Methane Oxidized (Tonnes/year)",
    template="plotly_white",
    hovermode="closest"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("***Model by A. Mikaelyan | Department of Entomology and Plant Pathology, NCSU***")
