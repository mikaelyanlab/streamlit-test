import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go
from scipy.interpolate import interp1d

# CONSTANTS
BASE_RETENTION, DG_ACETATE, DEFAULT_RMET = 14.0, 8.7e5, 8.0
COMPART_LETTERS = ['P1', 'P3', 'P4', 'P5']
COMPART_PROPORTIONS = {'P1':0.2, 'P3':0.3, 'P4':0.3, 'P5':0.2}

# FUNCTIONS
def compute_profiles(H, τ, T_ret, α, J_O2, P_H2):
    T = T_ret if T_ret>0 else τ*BASE_RETENTION
    xi = np.linspace(0,1,200)
    pH = 7 + 5*H*α/(α+1)*np.exp(-4*xi)
    O2 = np.maximum(0, 100*J_O2*np.exp(-10*xi/(T/BASE_RETENTION)))
    H2 = np.maximum(0, P_H2*(1-np.exp(-6*(xi-0.2))))
    Eh = -100 - 59*(pH-7) + 0.3*O2 - 40*H2
    return xi, pH, O2, H2, Eh

def acetate_balance(P_H2, f_aceto, Mmg, Rdot, Facet):
    A_prod = f_aceto * P_H2 * (0.4*Mmg/1000)
    A_need = Facet*Rdot*(Mmg/1000)/DG_ACETATE*1e6
    return A_prod, A_need

# STREAMLIT UI
st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H",0.0,1.0,0.3)
τ = st.sidebar.slider("Tau (× retention)",0.5,4.0,1.0)
T_ret=st.sidebar.number_input("Absolute T_ret (h, 0=use τ)",0.0,48.0,0.0)
α = st.sidebar.slider("Alkaline secretion α",0.0,10.0,5.0)
J_O2=st.sidebar.slider("O₂ influx",0.0,1.0,0.3)
P_H2=st.sidebar.slider("H₂ production",0.0,6.0,2.0)
f_aceto=st.sidebar.slider("Acetogen H₂ use",0.0,1.0,0.8)
Mmg=st.sidebar.slider("Body mass (mg)",1,50,12)
Rdot=st.sidebar.slider("Metabolic rate (J g⁻¹ h⁻¹)",0.5,25.0,DEFAULT_RMET)
Facet=st.sidebar.slider("Fraction ATP from acetate",0.7,1.0,0.9)

# Compute
xi, pH, O2, H2, Eh = compute_profiles(H, τ, T_ret, α, J_O2, P_H2)
A_prod, A_need = acetate_balance(P_H2, f_aceto, Mmg, Rdot, Facet)
energy_ok = A_prod>=A_need

# 3D MODEL
fig = go.Figure()
cumz = 0
for comp in COMPART_LETTERS:
    prop = COMPART_PROPORTIONS[comp]
    z0,z1 = cumz, cumz+prop
    cumz += prop
    interp = interp1d(xi, pH, 'linear')
    zmid = (z0+z1)/2
    val = interp((zmid)/(cumz))
    cyl = go.Cone # placeholder

# -- Simplify: Show only acetate metric and energy display
st.metric("Acetate produced vs needed", f"{A_prod:.2f} / {A_need:.2f} µmol/h",
           delta=None if energy_ok else "⚠ short")
if energy_ok: st.success("Energy budget met")
else: st.error("Shortfall – increase α, τ, or H")
