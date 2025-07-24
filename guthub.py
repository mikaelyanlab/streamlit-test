import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go

# Constants
DG_ACETATE = 8.7e5
DEFAULT_RMET = 8.0
COMPART = {"P1": 0.2, "P3": 0.3, "P4": 0.3, "P5": 0.2}

def axial_profiles(H, T_ret, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = 100 * J_O2 * np.exp(-10 * x / max(T_ret, 1))
    H2 = P_H2 * (1 - np.exp(-6 * (x - 0.2)))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH.clip(0), O2.clip(0), H2.clip(0), Eh

# Sidebar inputs
st.sidebar.header("Gut & physiology")
H = st.sidebar.slider("Humification H", 0.0, 1.0, 0.5)
alpha = st.sidebar.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
J_O2 = st.sidebar.slider("O₂ influx", 0.0, 1.0, 0.3)
P_H2 = st.sidebar.slider("H₂ production", 0.0, 8.0, 2.0)
T_ret = st.sidebar.number_input("Retention time (h)", 1.0, 100.0, 14.0)
radius_mm = st.sidebar.slider("Gut radius (mm)", 0.1, 1.5, 0.5)

# Generate profiles
x, pH, O2, H2, Eh = axial_profiles(H, T_ret, alpha, J_O2, P_H2)

# ── 3D Gut Cylinder Plot ──
st.header("🌐 3D Gut Volume (colored by pH)")
z0 = 0
fig = go.Figure()
z_scale = 10

for comp, frac in COMPART.items():
    z1 = z0 + frac * z_scale
    theta = np.linspace(0, 2 * np.pi, 50)
    z_vals = np.linspace(z0, z1, 50)
    TH, ZZ = np.meshgrid(theta, z_vals)
    X = radius_mm * np.cos(TH)
    Y = radius_mm * np.sin(TH)
    Z = ZZ
    idx = ((ZZ - z0) / (z1 - z0) * (len(pH) - 1)).astype(int)
    color_vals = pH[idx]
    fig.add_trace(go.Surface(
        x=X, y=Y, z=Z, surfacecolor=color_vals,
        cmin=min(pH), cmax=max(pH),
        colorscale="Viridis", showscale=(comp == "P1"),
        hoverinfo="none"
    ))
    z0 = z1

fig.update_layout(
    scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(title="Axial")),
    margin=dict(l=0, r=0, t=40, b=0),
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# ── Combined 2D Axial Profiles ──
st.header("📈 Combined Axial Profiles")
df = pd.DataFrame({"Position": x, "pH": pH, "O2": O2, "H2": H2, "Eh": Eh})

base = alt.Chart(df).properties(width=700, height=200)

chart_pH = base.mark_line(color="blue").encode(x="Position", y=alt.Y("pH", title="pH"))
chart_O2 = base.mark_line(color="green").encode(x="Position", y=alt.Y("O2", title="O₂ (μM)"))
chart_H2 = base.mark_line(color="purple").encode(x="Position", y=alt.Y("H2", title="H₂ (kPa)"))
chart_Eh = base.mark_line(color="gray").encode(x="Position", y=alt.Y("Eh", title="Eh (mV)"))

st.altair_chart(chart_pH & chart_O2 & chart_H2 & chart_Eh, use_container_width=True)
