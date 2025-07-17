import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("Methane Oxidation Impact Model")
st.sidebar.header("Adjust Parameters")

# Sliders
ox_rate = st.sidebar.slider("Instantaneous CH₄ Oxidation Rate (mmol/L/s)", 0.0, 10.0, 1.0)
active_density = st.sidebar.slider("Active Cellular Density (%)", 0, 100, 10)
leaf_biomass = st.sidebar.slider("Green Leaf Biomass (kg/m²)", 0.1, 10.0, 1.0)
plant_density = st.sidebar.slider("Plant Density (plants/m²)", 0.1, 100.0, 10.0)
stomatal_open = st.sidebar.slider("Stomatal Opening Period (hours/day)", 0.0, 24.0, 12.0)
growing_days = st.sidebar.slider("Growing Days per Year", 0, 365, 200)
total_adoption = st.sidebar.slider("Total Adoption Area (ha)", 0.0, 5e9, 1e6)

# Constants
g_per_mmol = 0.01604  # g CH₄/mmol

# Calculate Outputs (based on current leaf biomass setting)
active_fraction = active_density / 100
output1 = ox_rate * (leaf_biomass / plant_density) * active_fraction                      # mmol/plant/sec
output2 = ox_rate * active_fraction * leaf_biomass * (stomatal_open * 3600) * g_per_mmol  # g/m²/day
output3 = output2 * growing_days * total_adoption * 1000 * 1e-6                            # tonnes/year

# Display Metrics
st.subheader("Model Outputs")
st.metric("1. Per-plant Oxidation Rate", f"{output1:.4e} mmol/plant/s")
st.metric("2. Per-day Oxidation per m²", f"{output2:.4f} g/m²/day")
st.metric("3. Annual Global Oxidation", f"{output3:.2f} Tonnes/year")
if output3 > 1e6:
    st.markdown(f"**≈ {output3 / 1e6:.2f} Teragrams/year**")

# Dropdown to choose output to graph
selected_output = st.radio("Choose Output to Plot vs. Leaf Biomass", 
                           ["Output 1: mmol/plant/sec", 
                            "Output 2: g/m²/day", 
                            "Output 3: Tonnes/year"])

# Generate values over a range of leaf biomass
biomass_range = np.linspace(0.1, 10, 100)
y_vals = []

for B in biomass_range:
    if selected_output.startswith("Output 1"):
        val = ox_rate * (B / plant_density) * active_fraction
        y_label = "mmol/plant/s"
    elif selected_output.startswith("Output 2"):
        val = ox_rate * active_fraction * B * (stomatal_open * 3600) * g_per_mmol
        y_label = "g CH₄/m²/day"
    else:
        val = ox_rate * active_fraction * B * (stomatal_open * 3600) * g_per_mmol * growing_days * total_adoption * 1000 * 1e-6
        y_label = "Tonnes CH₄/year"
    y_vals.append(val)

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=biomass_range, y=y_vals,
    mode='lines+markers',
    name=selected_output.split(":")[0],
    line=dict(color="green")
))
fig.update_layout(
    title=selected_output + " vs Leaf Biomass",
    xaxis_title="Leaf Biomass (kg/m²)",
    yaxis_title=y_label,
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# Optional equations
with st.expander("Show Equations"):
    st.latex(r"\text{Output}_1 = R \cdot \left(\frac{B}{D}\right) \cdot A")
    st.latex(r"\text{Output}_2 = R \cdot A \cdot B \cdot (t \cdot 3600) \cdot 0.01604")
    st.latex(r"\text{Output}_3 = \text{Output}_2 \cdot d \cdot H \cdot 1000 \cdot 10^{-6}")
    st.markdown("""
    - \( R \): Instantaneous oxidation rate  
    - \( A \): Active cellular density (fraction)  
    - \( B \): Green leaf biomass  
    - \( D \): Plant density  
    - \( t \): Stomatal opening (hours/day)  
    - \( d \): Growing days  
    - \( H \): Adoption area (hectares)
    """)

st.markdown("***Model by A. Mikaelyan | Department of Entomology and Plant Pathology, NCSU***")
