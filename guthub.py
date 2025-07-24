import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go

# ── Constants ─────────────────────────────────────────────
DG_ACETATE = 8.7e5
DEFAULT_RMET = 8.0
COMPART = {"P1": 0.2, "P3": 0.3, "P4": 0.3, "P5": 0.2}

# ── Model functions ────────────────────────────────────────
def o2_solubility(T):
    return 12.56 - 0.1667 * (T - 25)

def axial_profiles(H, T_ret, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = np.maximum(0, 100 * J_O2 * np.exp(-10 * x / (T_ret if T_ret>0 else 14)/14))
    H2 = np.maximum(0, P_H2 * (1 - np.exp(-6 * (x - 0.2))))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

def acetate_balance(P_H2, f_aceto, gut_mass_g, Mmg, Rdot, Facet):
    A_prod = f_aceto * P_H2 * gut_mass_g
    E_need = Rdot * (Mmg / 1000)
    A_need = Facet * E_need / DG_ACETATE * 1e6
    return A_prod, A_need

# ── Streamlit UI ───────────────────────────────────────────
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

# ── Compute profiles ───────────────────────────────────────
x, pH, O2, H2, Eh = axial_profiles(H, T_ret, alpha, J_O2, P_H2)
sol = o2_solubility(tempC)
uM_to_kPa = 1 / sol

# ── Plotly 3D cylinders ────────────────────────────────────
st.header("🌐 3D Gut Cylinder Model (axial pH colored)")
fig = go.Figure()
z_start = 0
for comp, frac in COMPART.items():
    height = frac * 100
    z_mid = z_start + height / 2
    # Create cylinder mesh
    cyl = go.Mesh3d(
        x=[radius_mm*np.cos(t) for t in np.linspace(0, 2*np.pi, 30)]*2,
        y=[radius_mm*np.sin(t) for t in np.linspace(0, 2*np.pi, 30)]*2,
        z=[z_start]*30 + [z_start+height]*30,
        i=list(range(29)) + list(range(30,59)),
        j=list(range(1,30)) + list(range(31,60)),
        k=[30]*29 + [0]*29 + [59]*29 + [29]*29,
        intensity=[pH[int((z - z_start)/height*199)] for z in [z_start]*30 + [z_start+height]*30],
        colorscale="Viridis",
        showscale=(comp=="P1"),
        flatshading=True,
        name=comp
    )
    fig.add_trace(cyl)
    z_start += height

fig.update_layout(
    scene=dict(
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        zaxis_title="Gut axis",
        aspectratio=dict(x=1, y=1, z=1),
    ),
    margin=dict(r=0, l=0, b=0, t=30),
)
st.plotly_chart(fig, use_container_width=True)

# ── Fallback 2D plot ───────────────────────────────────────
df2 = pd.DataFrame({"x": x, "pH": pH, "O₂": O2*uM_to_kPa, "H₂": H2, "Eh": Eh})
st.header("2D Axial Profiles")
plot = alt.Chart(df2).transform_fold(
    ["pH","O₂","H₂","Eh"], as_=["metric","value"]
).mark_line().encode(x="x", y="value", color="metric")
st.altair_chart(plot, use_container_width=True)

# ── Acetate production vs need ─────────────────────────────
A_prod, A_need = acetate_balance(P_H2, f_aceto, 0.4*Mmg/1000, Mmg, Rdot, Facet)
ok = A_prod >= A_need
st.metric("Acetate prod vs needed", f"{A_prod:.2f} / {A_need:.2f} µmol/h",
          delta=None if ok else "⚠ short")
st.success("Energy OK ✔") if ok else st.error("Shortfall ✖")
