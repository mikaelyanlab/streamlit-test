# Aram Mikaelyan, NCSU | Impact Layer Model for Methane Oxidation
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("Methane Oxidation Impact Model")
st.sidebar.header("Adjust Parameters")

# Sliders for parameters
ox_rate = st.sidebar.slider("Instantaneous CH₄ Oxidation Rate (mmol/L/s)", 1e-7, 1e-5, 1e-6)
active_density = st.sidebar.slider("Active Cellular Density (%)", 10, 100, 50)  # Increased via genetic enhancements
plant_density = st.sidebar.slider("Plant Density (plants/m²)", 1.0, 10.0, 5.0)  # Realistic crop range
stomatal_open = st.sidebar.slider("Stomatal Opening Period (hours/day)", 8.0, 16.0, 12.0)
growing_days = st.sidebar.slider("Growing Days per Year", 150, 300, 200)
total_adoption = st.sidebar.slider("Total Adoption Area (ha)", 1e5, 5e9, 1e6)
optimization_factor = st.sidebar.slider("Nutrient/Temp Optimization Factor", 1.0, 1.5, 1.2)  # 20% boost
co2_factor = st.sidebar.slider("CO2 Synergy Factor", 1.0, 1.3, 1.1)  # 10-30% biomass increase
symbiotic_efficiency = st.sidebar.slider("Symbiotic Integration Efficiency", 1.0, 1.5, 1.2)  # 20% boost
canopy_multiplier = st.sidebar.slider("Multi-layer Canopy Multiplier", 1.0, 5.0, 2.0)  # 2-5x biomass

# Constants
g_per_mmol = 0.01604  # g CH₄/mmol
cytosol_fraction = 0.03  # L cytosol per kg biomass

# Range of leaf biomass values to plot
biomass_range = np.linspace(0.1, 10, 100)
impact_output3 = []

for B in biomass_range:
    # Adjust biomass for canopy and CO2 effects
    effective_biomass = B * canopy_multiplier * co2_factor
    # Calculate per-plant oxidation rate
    output1 = ox_rate * (active_density / 100) * effective_biomass * cytosol_fraction * (stomatal_open * 3600) * g_per_mmol
    # Scale by plant density, optimization, and symbiotic efficiency
    output2 = output1 * plant_density * optimization_factor * symbiotic_efficiency
    # Annual impact in tonnes
    output3 = output2 * growing_days * total_adoption * 10  # 10 = 10,000 m²/ha * 1e-6 tonnes/g * 1000 g/kg
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
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
