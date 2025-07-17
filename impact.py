# Aram Mikaelyan, NCSU | Impact Layer Model for Methane Oxidation

import streamlit as st

st.title("Methane Oxidation Impact Model")
st.sidebar.header("Adjust Parameters")

# --- Sliders for Inputs ---
ox_rate = st.sidebar.slider("Instantaneous CH₄ Oxidation Rate (mmol/L/s)", 0.0, 10.0, 1.0)
active_density = st.sidebar.slider("Active Cellular Density (%)", 0, 100, 10)
leaf_biomass = st.sidebar.slider("Green Leaf Biomass (kg/m²)", 0.0, 10.0, 1.0)
plant_density = st.sidebar.slider("Plant Density (plants/m²)", 0.1, 100.0, 10.0)
stomatal_open = st.sidebar.slider("Stomatal Opening Period (hours/day)", 0.0, 24.0, 12.0)
growing_days = st.sidebar.slider("Growing Days per Year", 0, 365, 200)
total_adoption = st.sidebar.slider("Total Adoption Area (ha)", 0.0, 5e9, 1e6)

# --- Calculations ---
# Output 1: Per-plant oxidation rate (mmol/plant/s)
leaf_mass_per_plant = leaf_biomass / plant_density  # kg
active_mass_fraction = active_density / 100
output1 = ox_rate * leaf_mass_per_plant * active_mass_fraction

# Output 2: Per-day oxidation per m² (g/m²/day)
g_per_mmol = 0.01604  # g CH₄ per mmol
output2 = ox_rate * active_mass_fraction * leaf_biomass * (stomatal_open * 3600) * g_per_mmol

# Output 3: Global yearly oxidation (Tonnes/year)
output3 = output2 * growing_days * total_adoption * 1000 * 1e-6  # convert to tonnes

# --- Display Results ---
st.subheader("Model Outputs")
st.metric("1. Per-plant Oxidation Rate", f"{output1:.4e} mmol/plant/s")
st.metric("2. Per-day Oxidation per m²", f"{output2:.4f} g/m²/day")
st.metric("3. Annual Global Oxidation", f"{output3:.2f} Tonnes/year")

# Optional formatting based on scale
if output3 > 1e6:
    st.markdown(f"**≈ {output3 / 1e6:.2f} Teragrams/year**")

# --- Equations for reference ---
with st.expander("Show Equations Used"):
    st.latex(r"Output_1 = R \times \left(\frac{B}{D}\right) \times A")
    st.latex(r"Output_2 = R \times A \times B \times (t \times 3600) \times 0.01604")
    st.latex(r"Output_3 = Output_2 \times d \times H \times 1000 \times 10^{-6}")
    st.markdown("""
    Where:
    - R = CH₄ oxidation rate (mmol/L/s)  
    - A = active cellular density (%)  
    - B = leaf biomass (kg/m²)  
    - D = plant density (plants/m²)  
    - t = stomatal opening period (h/day)  
    - d = growing days  
    - H = adoption area (ha)
    """)

st.markdown("***Model by A. Mikaelyan | Department of Entomology and Plant Pathology, NCSU***")
