import numpy as np
import pandas as pd
import plotly.graph_objects as go
import altair as alt
import streamlit as st

# Define base gut compartments
BASE_COMPARTS = {
    "P1": {"length": 3, "radius": 0.15},
    "P3": {"length": 8, "radius": 0.45},
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}

# Compute radial gradients
def radial_grad(radius, volume, enzyme_activity):
    r_rel = np.linspace(0, 1, 50)
    O2 = 100 * np.exp(-5 * (1 - r_rel)) / (1 + 0.3 * volume)
    H2 = 2 * enzyme_activity * (1 - np.exp(-5 * r_rel))
    return r_rel * radius, O2, H2

# Adjust gut compartments based on diet and selection
def adjust_compartments(recalcitrance, selection_pressure):
    comparts = BASE_COMPARTS.copy()
    comparts["P3"]["length"] *= (1 + 0.6 * recalcitrance * selection_pressure)
    comparts["P3"]["radius"] *= (1 + 0.4 * recalcitrance * selection_pressure)
    comparts["P5"]["length"] *= (1 - 0.3 * recalcitrance * selection_pressure)
    for comp in comparts:
        comparts[comp]["volume"] = np.pi * comparts[comp]["radius"]**2 * comparts[comp]["length"]
    return comparts

# Axial profiles
def axial_profiles(recalcitrance, selection_pressure, comparts):
    x = np.linspace(0, 1, 200)
    enzyme_activity = 1 + 0.5 * recalcitrance * selection_pressure
    pH = 7 + 3.5 * recalcitrance * np.exp(-4 * x) * selection_pressure
    O2 = 100 * np.exp(-5 * x) / (1 + 0.2 * comparts["P3"]["volume"])
    H2 = 2 * enzyme_activity * np.maximum(0, 1 - np.exp(-6 * (x - 0.2)))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh, enzyme_activity

# Streamlit inputs
st.sidebar.header("Evolutionary Parameters")
recalcitrance = st.sidebar.slider("Dietary Recalcitrance (0: Soil-like, 1: Wood-like)", 0.0, 1.0, 0.5)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)
var_map = st.sidebar.selectbox("3D Color Variable", ["O2", "H2", "pH", "Eh"])

# Model computation
comparts = adjust_compartments(recalcitrance, selection_pressure)
x, pH, O2_ax, H2_ax, Eh_ax, enzyme_activity = axial_profiles(recalcitrance, selection_pressure, comparts)
rad_data = {comp: radial_grad(d["radius"], d["volume"], enzyme_activity) for comp, d in comparts.items()}

# 3D gut visualization
fig = go.Figure()
x0 = 0
for comp, d in comparts.items():
    L, R = d["length"], d["radius"]
    r, O2_r, H2_r = rad_data[comp]
    slices = 30
    dx = L / slices
    for i in range(slices):
        xi = x0 + i * dx
        for j in range(len(r) - 1):
            theta = np.linspace(0, 2*np.pi, 30)
            x_vals, y_vals, z_vals = [], [], []
            for angle in theta:
                y_vals.append(r[j] * np.cos(angle))
                z_vals.append(r[j] * np.sin(angle))
                x_vals.append(xi)
            for angle in reversed(theta):
                y_vals.append(r[j+1] * np.cos(angle))
                z_vals.append(r[j+1] * np.sin(angle))
                x_vals.append(xi)
            surf_val = {"O2": O2_r[j], "H2": H2_r[j], "pH": pH[i], "Eh": Eh_ax[i]}.get(var_map, O2_r[j])
            fig.add_trace(go.Mesh3d(
                x=x_vals, y=y_vals, z=z_vals,
                intensity=[surf_val] * len(x_vals),
                colorscale='Viridis',
                showscale=False,
                opacity=0.85,
                hoverinfo='skip'
            ))
    x0 += L

fig.update_layout(
    scene=dict(
        xaxis_title="Axial Position (mm)",
        yaxis_title="Radial (Y)",
        zaxis_title="Radial (Z)",
        camera=dict(eye=dict(x=2.5, y=0.1, z=0.1)),
        aspectratio=dict(x=3, y=1, z=1)
    ),
    annotations=[
        dict(
            text=f"Diet Recalcitrance: {recalcitrance:.2f}",
            xref="paper", yref="paper", x=0.5, y=0.95,
            showarrow=False, font=dict(size=12, color="black")
        )
    ],
    margin=dict(l=0, r=0, t=50, b=0),
    height=600
)

st.header(f"3D Gut Model – {var_map}")
st.plotly_chart(fig, use_container_width=True)

# 2D radial profile (P3)
st.subheader("Radial Profile in P3 (Paunch)")
rv, O2_rad, H2_rad = rad_data["P3"]
radial_df = pd.DataFrame({"Radius (mm)": rv, "O₂ (µM)": O2_rad, "H₂ (µM)": H2_rad})
chart_o2 = alt.Chart(radial_df).mark_line(color="blue").encode(
    x=alt.X("Radius (mm)", title="Radius (mm)"),
    y=alt.Y("O₂ (µM)", title="Concentration (µM)")
).properties(title="O₂ and H₂ Radial Profiles")
chart_h2 = alt.Chart(radial_df).mark_line(color="red").encode(
    x="Radius (mm)", y="H₂ (µM)"
)
microoxic = alt.Chart(pd.DataFrame({"x": [0, comparts["P3"]["radius"]]})).mark_rect(opacity=0.2, color="blue").encode(
    x="x", x2=alt.value(comparts["P3"]["radius"]), y=alt.value(0), y2=alt.value(O2_rad.max())
)
st.altair_chart(microoxic + chart_o2 + chart_h2, use_container_width=True)

# Axial profiles
st.subheader("Axial Profiles")
def plot_line(y, col, title, ylab):
    df = pd.DataFrame({"Position": x, title: y})
    return alt.Chart(df).mark_line(color=col).encode(
        x=alt.X("Position", title="Normalized Axial Position"),
        y=alt.Y(title, title=ylab)
    ).properties(title=title)

charts = [
    plot_line(pH, "green", "pH", "pH"),
    plot_line(O2_ax, "blue", "O₂", "O₂ (µM)"),
    plot_line(H2_ax, "red", "H₂", "H₂ (µM)"),
    plot_line(Eh_ax, "gray", "Eh", "Eh (mV)")
]
for ch in charts:
    st.altair_chart(ch, use_container_width=True)
