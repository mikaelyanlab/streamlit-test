import streamlit as st
import plotly.graph_objects as go

# Streamlit UI
st.title("Methane Emission & Livestock Growth Sankey Models")

# User-adjustable methane production slider
CH4 = st.sidebar.slider("Methane Production (g/day)", 50, 500, 250)

# Energy Flow Data
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Emission", "Net Energy", "Body Biomass", "Milk Production"]
energy_source = [0, 0, 0, 0, 0, 5, 5]  # Source indices
energy_target = [1, 2, 3, 4, 5, 6, 7]  # Target indices
energy_values = [100, 15, 50, CH4, 235, 50, 50]  # Fixed values with methane slider input

# Carbon Flow Data
carbon_labels = ["Dietary Carbon", "Fecal Carbon Loss", "Urinary Carbon Loss", "Methane Emission", "Carbon Retained in Biomass", "Carbon in Milk"]
carbon_source = [0, 0, 0, 0, 0]  # Source indices
carbon_target = [1, 2, 3, 4, 5]  # Target indices
carbon_values = [400, 50, CH4, 300, 150]  # Fixed values with methane slider input

# Ensure all lists are of the same length
assert len(energy_source) == len(energy_target) == len(energy_values)
assert len(carbon_source) == len(carbon_target) == len(carbon_values)

# Energy Sankey Diagram
energy_sankey = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=energy_labels,
        color="lightgray",
        font=dict(color="black", size=14)
    ),
    link=dict(
        source=energy_source,
        target=energy_target,
        value=energy_values,
    )
))
energy_sankey.update_layout(title_text="Energy Partitioning in Livestock", font_size=10)

# Carbon Sankey Diagram
carbon_sankey = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=carbon_labels,
        color="lightgray",
        font=dict(color="black", size=14)
    ),
    link=dict(
        source=carbon_source,
        target=carbon_target,
        value=carbon_values,
    )
))
carbon_sankey.update_layout(title_text="Carbon Partitioning in Livestock", font_size=10)

# Display both Sankey diagrams
st.plotly_chart(energy_sankey)
st.plotly_chart(carbon_sankey)

# Display Key Metrics
st.write(f"### Methane Production: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {energy_values[5]:.2f} MJ/day")
st.write(f"### Weight Gain: {energy_values[6]:.2f} kg/day")
st.write(f"### Milk Yield: {energy_values[7]:.2f} kg/day")
