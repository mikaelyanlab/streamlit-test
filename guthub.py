import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import altair as alt

# Anatomical compartments (length mm, radius mm)
COMPARTS = {
    "P1": {"length": 3, "radius": 0.15},
    "P3": {"length": 8, "radius": 0.45},
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}
THETA_RES, Z_RES = 40, 40

def axial_profiles(H, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = 100 * J_O2 * np.exp(-5 * x)
    H2 = P_H2 * np.maximum(0, 1 - np.exp(-6 * (x - 0.2)))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

def radial_grad(R, k_r, O2_wall, H2_core):
    r_rel = np.linspace(0, 1, 50)
    O2 = O2_wall * np.exp(-k_r * (1 - r_rel))
    H2 = H2_core * (1 - np.exp(-k_r * r_rel))
    return r_rel * R, O2, H2

# Sidebar inputs
st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H", 0.0, 1.0, 0.5)
alpha = st.sidebar.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
J_O2 = st.sidebar.slider("O₂ influx", 0.0, 1.0, 0.3)
P_H2 = st.sidebar.slider("H₂ production", 0.0, 8.0, 2.0)
k_r = st.sidebar.slider("Radial decay kᵣ", 1.0, 15.0, 5.0)
var_map = st.sidebar.selectbox("Color map variable", ["O2", "H2"])

# Compute profiles
x, pH, O2_ax, H2_ax, Eh_ax = axial_profiles(H, alpha, J_O2, P_H2)
O2_wall, H2_core = J_O2 * 100, P_H2

# Pre-compute radial gradients
rad_data = {
    comp: radial_grad(d["radius"], k_r, O2_wall, H2_core)
    for comp, d in COMPARTS.items()
}

# 3D Gut with radial coloring
fig = go.Figure()
z0 = 0
for comp, d in COMPARTS.items():
    L, R = d["length"], d["radius"]
    z1 = z0 + L
    theta = np.linspace(0, 2*np.pi, THETA_RES)
    z_lin = np.linspace(z0, z1, Z_RES)
    TH, ZZ = np.meshgrid(theta, z_lin)
    X, Y = R * np.cos(TH), R * np.sin(TH)

    rv, Or, Hr = rad_data[comp]
    surf = Or if var_map == "O2" else Hr
    surf2d = np.tile(surf, (Z_RES, 1))

    fig.add_trace(go.Surface(
        x=X, y=Y, z=ZZ,
        surfacecolor=surf2d,
        cmin=surf.min(), cmax=surf.max(),
        colorscale="Viridis",
        showscale=(comp == "P1"),
        name=comp, opacity=0.8, hoverinfo="none"
    ))
    z0 = z1

fig.update_layout(
    scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_title="Axial (mm)"),
    margin=dict(l=0, r=0, t=30, b=0), height=600
)
st.header(f"3D Gut – Radial {var_map}")
st.plotly_chart(fig, use_container_width=True)

# 2D Radial slice (P3)
st.subheader("2D Radial slice – P3")
rv, Or, Hr = rad_data["P3"]
radial_df = pd.DataFrame({"r_mm": rv, "O₂": Or, "H₂": Hr})
chart_o2 = alt.Chart(radial_df).mark_line(color="blue").encode(x="r_mm", y="O₂")
chart_h2 = alt.Chart(radial_df).mark_line(color="red").encode(x="r_mm", y="H₂")
st.altair_chart(chart_o2 + chart_h2, use_container_width=True)

# Individual axial profiles — no transforms
st.subheader("Axial Profiles")
def plot_line(y, col, title, ylab):
    df = pd.DataFrame({"Position": x, title: y})
    return alt.Chart(df).mark_line(color=col).encode(x="Position", y=alt.Y(title, title=ylab))

charts = [
    plot_line(pH, "green", "pH", "pH"),
    plot_line(O2_ax, "blue", "O₂", "O₂"),
    plot_line(H2_ax, "red", "H₂", "H₂"),
    plot_line(Eh_ax, "gray", "Eh", "Eh")
]
for ch in charts:
    st.altair_chart(ch, use_container_width=True)
