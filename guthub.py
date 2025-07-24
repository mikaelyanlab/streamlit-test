import numpy as np
import streamlit as st
import pandas as pd
import altair as alt

# Define base gut compartments with initial radii
BASE_COMPARTS = {
    "P1": {"radius": 0.15},
    "P3": {"radius": 0.45},  # Paunch
    "P4": {"radius": 0.30},
    "P5": {"radius": 0.15}
}

# Function to adjust radii based on humification
def adjust_radii(humification, selection_pressure):
    comparts = BASE_COMPARTS.copy()
    # Higher humification increases P3 radius, decreases P5 radius
    comparts["P3"]["radius"] *= (1 + 0.6 * humification * selection_pressure)
    comparts["P5"]["radius"] *= (1 - 0.3 * humification * selection_pressure)
    return comparts

# Function to compute axial profiles (simplified for gradients)
def axial_profiles(humification, selection_pressure):
    x = np.linspace(0, 1, 100)
    pH = 7 + 3.5 * humification * np.exp(-4 * x) * selection_pressure
    O2 = 100 * np.exp(-5 * x) / (1 + 0.2 * humification)
    H2 = 2 * humification * np.maximum(0, 1 - np.exp(-6 * (x - 0.2))) * selection_pressure
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

# Sidebar inputs
st.sidebar.header("Evolutionary Parameters")
humification = st.sidebar.slider("Humification (0: Low, 1: High)", 0.0, 1.0, 0.5)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)
var_map = st.sidebar.selectbox("Gradient Variable", ["O2", "H2", "pH", "Eh"])

# Compute adjusted radii and profiles
comparts = adjust_radii(humification, selection_pressure)
x, pH, O2, H2, Eh = axial_profiles(humification, selection_pressure)

# Create data for circle plots (using mean values for gradients)
plot_data = []
for comp, d in comparts.items():
    radius = d["radius"]
    # Use mean value of the selected variable for gradient
    value = {"O2": O2.mean(), "H2": H2.mean(), "pH": pH.mean(), "Eh": Eh.mean()}[var_map]
    plot_data.append({"Compartment": comp, "Radius": radius, "Value": value})

df = pd.DataFrame(plot_data)

# Plot four circles with gradients
base = alt.Chart(df).encode(
    x=alt.X("Compartment:N", title="Gut Compartment"),
    y=alt.value(0),
    size=alt.Size("Radius:Q", scale=alt.Scale(range=[100, 1000]), title="Cross-Section Area Proxy"),
    color=alt.Color("Value:Q", scale=alt.Scale(scheme="viridis"), title=f"{var_map} Gradient")
).mark_point(shape="circle")

# Add labels and adjust layout
chart = base.properties(
    width=150,
    height=200
).configure_axis(
    labelFontSize=12,
    titleFontSize=14
).configure_legend(
    titleFontSize=12,
    labelFontSize=10
)

# Display chart
st.header("Gut Cross-Sections")
st.altair_chart(chart, use_container_width=True)
