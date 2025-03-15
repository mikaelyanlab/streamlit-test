import streamlit as st
import plotly.graph_objects as go

# Streamlit UI
st.title("Methane Emission & Livestock Growth - Carbon Sankey Model")
st.sidebar.header("Adjust Methane Production")

# Single slider for Methane Production
CH4 = st.sidebar.slider("Methane Production (g/day)", 50, 500, 250)

# Carbon partitioning (values adjusted for debugging)
C_intake = 1000  # Total dietary carbon intake
C_feces = 400    # Carbon lost in feces
C_urine = 50     # Carbon lost in urine
C_methane = CH4  # Carbon lost as methane
C_biomass = 300  # Carbon retained in body mass
C_milk = 150     # Carbon in milk

# Carbon Sankey Diagram
carbon_labels = ["Dietary Carbon", "Fecal Carbon Loss", "Urinary Carbon Loss", "Methane Emission", "Carbon Retained in Biomass", "Carbon in Milk"]
carbon_source = [0, 0, 0, 0, 0]  # Source indices
carbon_target = [1, 2, 3, 4, 5]  # Target indices
carbon_values = [C_feces, C_urine, C_methane, C_biomass, C_milk]

# Ensure values are positive
carbon_values = [max(v, 0.01) for v in carbon_values]

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

# Display Carbon Sankey diagram
st.plotly_chart(carbon_sankey)

# Display Key Metrics
st.write(f"### Methane Production: {CH4:.2f} g/day")
