import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("Methane Oxidation Impact Model")

# --- Log-scale CH₄ Oxidation Rate Slider ---
log_min = float(-4)    # log10(0.0001)
log_max = float(-0.5)  # log10(0.3)
log_val = st.sidebar.slider(
    "Log₁₀ of Instantaneous CH₄ Oxidation Rate (mmol/L/s)",
    min_value=log_min,
    max_value=log_max,
    value=-1.5,
    step=0.1
)
ox_rate = 10 ** float(log_val)
st.sidebar.markdown(f"Selected Rate: **{ox_rate:.4e} mmol/L/s**")

# --- Other Parameters ---
active_density = st.sidebar.slider("Active Cellular Activity (%)", 0, 100, 10)
leaf_biomass = st.sidebar.slider("Green Leaf Biomass (kg/m²)", 0.1, 10.0, 1.0)
plant_density = st.sidebar.slider("Plant Density (plants/m²)", 0.1, 100.0, 10.0)
culture_vol_per_kg = st.sidebar.slider("Culture-equivalent Volume per kg Leaf (L/kg)", 0.001, 1.0, 0.05, step=0.005)
stomatal_open = st.sidebar.slider("Stomatal Opening Period (hours/day)", 0.0, 24.0, 12.0)
growing_days = st.sidebar.slider("Growing Days per Year", 0, 365, 200)
total_adoption = st.sidebar.slider("Total Adoption Area (ha)", 0.0, 5e9, 1e6)

# --- Constants ---
g_per_mmol = 0.01604  # g CH₄ per mmol
active_fraction = active_density / 100
culture_equiv_volume = leaf_biomass * culture_vol_per_kg  # L/m²

# --- Outputs ---
# Output 1: mmol / plant / sec
leaf_mass_per_plant = leaf_biomass / plant_density  # kg/plant
culture_vol_per_plant = leaf_mass_per_plant * culture_vol_per_kg  # L/plant
output1 = ox_rate * active_fraction * culture_vol_per_plant  # mmol/plant/sec

# Output 2: g / m² / day
output2 = ox_rate * active_fraction * culture_equiv_volume * (stomatal_open * 3600) * g_per_mmol

# Output 3: tonnes / year
output3 = output2 * growing_days * total_adoption * 1000 * 1e-6

# Display Metrics
st.subheader("Model Outputs")
st.metric("1. Per-plant Oxidation Rate", f"{output1:.4e} mmol/plant/s")
st.metric("2. Per-day Oxidation per m²", f"{output2:.4f} g/m²/day")
st.metric("3. Annual Global Oxidation", f"{output3:.2f} Tonnes/year")
if output3 > 1e6:
    st.markdown(f"**≈ {output3 / 1e6:.2f} Teragrams/year**")

# --- Output Selection for Plot ---
selected_output = st.radio("Choose Output to Plot vs. Leaf Biomass", 
                           ["Output 1: mmol/plant/sec", 
                            "Output 2: g/m²/day", 
                            "Output 3: Tonnes/year"])

# --- Plot vs Leaf Biomass ---
biomass_range = np.linspace(0.1, 10, 100)
y_vals = []

for B in biomass_range:
    V_eq = B * culture_vol_per_kg
    M_per_plant = B / plant_density
    V_per_plant = M_per_plant * culture_vol_per_kg

    if selected_output.startswith("Output 1"):
        val = ox_rate * active_fraction * V_per_plant
        y_label = "mmol/plant/s"
    elif selected_output.startswith("Output 2"):
        val = ox_rate * active_fraction * V_eq * (stomatal_open * 3600) * g_per_mmol
        y_label = "g CH₄/m²/day"
    else:
        val = ox_rate * active_fraction * V_eq * (stomatal_open * 3600) * g_per_mmol * growing_days * total_adoption * 1000 * 1e-6
        y_label = "Tonnes CH₄/year"
    y_vals.append(val)

# Clean up y_vals for plotting
y_vals = np.array(y_vals)
y_vals = np.where(y_vals > 0, y_vals, np.nan)  # avoid zeros if log scale is used

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=biomass_range,
    y=y_vals,
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
fig.update_yaxes(tickformat=".2e")  # Use scientific notation (e.g., 1.00e-04)

# Optional: log-scale y-axis for Output 3
if selected_output.startswith("Output 3"):
    fig.update_yaxes(type="log")

st.plotly_chart(fig, use_container_width=True)

# --- Equations ---
with st.expander("Show Equations"):
    st.latex(r"\text{Output}_1 = R \cdot A \cdot \left( \frac{B}{D} \cdot V_{\text{eq}} \right)")
    st.latex(r"\text{Output}_2 = R \cdot A \cdot (B \cdot V_{\text{eq}}) \cdot (t \cdot 3600) \cdot M_{\text{CH}_4}")
    st.latex(r"\text{Output}_3 = \text{Output}_2 \cdot d \cdot H \cdot 1000 \cdot 10^{-6}")
    st.markdown("""
    - \( R \): Methane oxidation rate (mmol/L/s)  
    - \( A \): Active cellular activity (fraction)  
    - \( B \): Leaf biomass (kg/m²)  
    - \( D \): Plant density (plants/m²)  
    - \( V_{eq} \): L of culture-equivalent volume per kg leaf biomass  
    - \( t \): Stomatal window (hr/day)  
    - \( d \): Growing days/year  
    - \( H \): Adoption area (ha)  
    - \( M_{CH_4} \): 0.01604 g/mmol
    """)

st.markdown("***Corrected Model by A. Mikaelyan | Entomology and Plant Pathology, NCSU***")
