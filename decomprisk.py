import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.title("Minimal Dynamic Choropleth")

# User input
val = st.slider("Adjust Risk Factor", 0, 100, 50)

# Sample countries and fake dynamic values
countries = ['USA', 'CAN', 'BRA', 'FRA', 'ZAF', 'AUS', 'CHN', 'IND', 'RUS', 'EGY']
base_values = np.array([10, 15, 30, 20, 25, 18, 22, 28, 35, 12])

# Modify values based on slider input
adjusted_values = base_values * (val / 50)  # scale relative to middle value

# Build dataframe
df = pd.DataFrame({
    'iso_alpha': countries,
    'risk': adjusted_values
})

# Create choropleth
fig = go.Figure(data=go.Choropleth(
    locations=df['iso_alpha'],
    z=df['risk'],
    locationmode='ISO-3',
    colorscale='RdYlGn_r',
    colorbar_title="Risk Level"
))

fig.update_layout(
    title="Dynamic Global Risk Map",
    geo=dict(showframe=False, showcoastlines=False)
)

st.plotly_chart(fig, use_container_width=True)
