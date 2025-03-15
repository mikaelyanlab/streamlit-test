import streamlit as st
import plotly.graph_objects as go

# Streamlit UI
st.title("Methane Emission & Livestock Growth - Carbon Sankey Model")

# Hardcoded Carbon Partitioning Data (For Debugging)
carbon_labels = ["Dietary Carbon", "Fecal Carbon Loss", "Urinary Carbon Loss", "Methane Emission", "Carbon Retained in Biomass", "Carbon in Milk"]
carbon_source = [0, 0, 0, 0, 0]  # Source indices
carbon_target = [1, 2, 3, 4, 5]  # Target indices
carbon_values = [400, 50, 100, 300, 150]  # Fixed Values

# Debugging: Print lists before passing to Plotly
print("Carbon Sankey Debugging:")
print("Labels:", carbon_labels)
print("Sources:", carbon_source)
print("Targets:", carbon_target)
print("Values:", carbon_values)

# Ensure lists are properly formatted
assert len(carbon_source) == len(carbon_target) == len(carbon_values), "Mismatch in source, target, and values list lengths."
assert max(carbon_source + carbon_target) < len(carbon_labels), "Index in source/target exceeds label list."

# Ensure values are positive
carbon_values = [max(v, 0.01) for v in carbon_values]

# Create Static Carbon Sankey
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

# Debugging Step: If this works, we reintroduce dynamic CH4 step by step
