import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go

# ── Constants ──
DG_ACETATE = 8.7e5
DEFAULT_RMET = 8.0
COMPART = {"P1": 0.2, "P3": 0.3, "P4": 0.3, "P5": 0.2}
CYL_STEPS = 30  # resolution of cylinder

# ── Model functions ──
def o2_solubility(T):
    return 12.56 - 0.1667 * (T - 25)

def axial_profiles(H, T_ret, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = np.maximum(0, 100 * J_O2 * np.exp(-10 * x / T_ret))
    H2 = np.maximum(0, P_H2 * (1 - np.exp(-6 * (x - 0.2))))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

def acetate_balance(P_H2, f_aceto, gut_mass_g, Mmg, Rdot, Facet):
    A_prod = f_aceto * P_H2 * gut_mass_g
    E_need = Rdot * (Mmg / 1000)
    A_need = Facet * E_need / DG_ACETATE * 1e6
    return A_prod, A_need

# ── UI Inputs ──
st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H", 0.0, 1.0, 0.5)
alpha = st.sidebar.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
tempC = st.sidebar.slider("Temperature (°C)", 15, 40, 30)
J_O2 = st.sidebar.slider("O₂ influx", 0.0, 1.0, 0.3)
P_H2 = st.sidebar.slider("H₂ production", 0.0, 8.0, 2.0)
f_aceto = st.sidebar.slider("Acetogen H₂ use", 0.0, 1.0, 0.8)
Mmg = st.sidebar.slider("Body mass (mg)", 1, 200, 12)
Rdot = st.sidebar.slider("Metabolic rate (J/g/h)", 0.5, 50.0, DEFAULT_RMET)
Facet = st.sidebar.slider("ATP fraction", 0.5, 1.0, 0.9)
radius_mm = st.sidebar.slider("Gut radius (mm)", 0.1, 1.5, 0.5)
T_ret = st.sidebar.number_input("Retention time (h)", 1.0, 100.0, 14.0)

# ── Computation ──
x, pH, O2, H2, Eh = axial_profiles(H, T_ret, alpha, J_O2, P_H2)
sol = o2_solubility(tempC)
uM_to_kPa = 1 / sol

# ── 3D Cylinder Plotly ──
st.header("🌐 3D Gut Cylinder Model (axial pH)")
fig = go.Figure()
z_start = 0.0

theta = np.linspace(0, 2 * np.pi, CYL_STEPS)
circle_x = np.cos(theta)
circle_y = np.sin(theta)

for comp, frac in COMPART.items():
    height = frac * 10  # scaling for visualization
    for side in ("bottom", "top"):
        z = z_start if side == "bottom" else z_start + height
        zs = np.full(CYL_STEPS, z)
        fig.add_trace(go.Scatter3d(
            x=radius_mm * circle_x,
            y=radius_mm * circle_y,
            z=zs,
            mode='lines',
            line=dict(color='gray', width=2),
            showlegend=False
        ))
    # surface mesh
    surface_x = []
    surface_y = []
    surface_z = []
    surface_color = []
    for i, t in enumerate(theta):
        for z in np.linspace(z_start, z_start + height, 20):
            surface_x.append(radius_mm * np.cos(t))
            surface_y.append(radius_mm * np.sin(t))
            surface_z.append(z)
            xi = int((z - z_start) / height * (len(pH)-1))
            surface_color.append(pH[xi])
    fig.add_trace(go.Mesh3d(
        x=surface_x, y=surface_y, z=surface_z,
        intensity=surface_color,
        colorscale='Viridis',
        opacity=0.7,
        showscale=(comp == "P5"),
        name=comp
    ))
    z_start += height

fig.update_layout(
    scene=dict(xaxis=dict(title="X (mm)"),
               yaxis=dict(title="Y (mm)"),
               zaxis=dict(title="Gut axis")),
    margin=dict(r=0, l=0, b=0, t=0),
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# ── 2D Plot ──
df2 = pd.DataFrame({"x": x, "pH": pH, "O₂": O2, "H₂": H2, "Eh": Eh})
st.header("2D Axial Profiles")
p = alt.Chart(df2).transform_fold(
    ["pH", "O₂", "H₂", "Eh"], as_=["metric", "value"]
).mark_line().encode(x="x", y="value", color="metric")
st.altair_chart(p, use_container_width=True)

# ── Acetate Metrics ──
A_prod, A_need = acetate_balance(P_H2, f_aceto, 0.4*Mmg/1000, Mmg, Rdot, Facet)
ok = A_prod >= A_need
st.metric("Acetate prod vs needed", f"{A_prod:.2f} / {A_need:.2f} µmol/h",
          delta=None if ok else "⚠ short")
ok and st.success("✔ Energy OK") or st.error("✖ Shortfall")
