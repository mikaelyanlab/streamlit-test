import numpy as np, pandas as pd, altair as alt, streamlit as st

# ───── CONSTANTS ─────────────────────────────────────────────────
BASE_RETENTION = 14.0   # placeholder, no longer used
DG_ACETATE     = 8.7e5
DEFAULT_RMET   = 8.0
COMPART = {"P1 (mixed)": 0.00, "P3 (paunch)": .35,
           "P4 (colon)": .70, "P5 (rectum)": 1.00}
WATER_DENSITY = 1.0     # mg/µL ≈ g/cm³ – simplifies volume calc

# ───── FUNCTIONS ─────────────────────────────────────────────────
def o2_solubility_uM_per_kPa(T):
    return 12.56 - 0.1667 * (T - 25)

def axial_profiles(H, T_ret, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = np.maximum(0, 100 * J_O2 * np.exp(-10 * x / (T_ret / BASE_RETENTION)))
    H2 = np.maximum(0, P_H2 * (1 - np.exp(-6 * (x - 0.2))))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return pd.DataFrame({"x": x, "pH": pH, "O2_uM": O2, "H2_kPa": H2, "Eh": Eh})

def radial_profile(O2_wall_uM, H2_core_kPa, pH_core, r_rel, k_r, sol_kPa_per_uM):
    O2_kPa = (O2_wall_uM * sol_kPa_per_uM) * np.exp(-k_r * (1 - r_rel))
    H2_kPa = H2_core_kPa * (1 - np.exp(-k_r * r_rel))
    pH     = pH_core - 0.5 * (1 - r_rel)
    return O2_kPa, H2_kPa, pH

def acetate_balance(P_H2, f_aceto, gut_mass_g, Mmg, Rdot, F_acet):
    A_prod = f_aceto * P_H2 * gut_mass_g
    E_need = Rdot * (Mmg / 1000)
    A_need = F_acet * E_need / DG_ACETATE * 1e6
    return A_prod, A_need

def compute_Tret(Mmg, GutFrac, FeedingRate, Digestibility, Motility):
    V_gut = Mmg * GutFrac / 1000  # mg → µL
    Q_flow = FeedingRate * Digestibility * Motility  # µg digesta per h → µL/h
    return V_gut / Q_flow if Q_flow > 0 else np.nan

# ───── STREAMLIT APP ─────────────────────────────────────────────
st.title("Termite gut simulator — mechanistic retention model")

with st.sidebar:
    st.header("Physiology & diet inputs")
    Mmg = st.slider("Body mass (mg)", 1, 200, 12)
    GutFrac = st.slider("Hindgut fraction of mass", 0.05, 0.5, 0.2)
    FeedingRate = st.slider("Feeding rate (mg/h)", 0.1, 50.0, 5.0)
    Digestibility = st.slider("Diet digestibility (%)", 0.2, 1.0, 0.6)
    Motility = st.slider("Motility factor", 0.1, 1.0, 0.5)

    st.markdown("----")
    H = st.slider("Humification H", 0.0, 1.0, 0.5)
    alpha = st.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
    tempC = st.slider("Temperature (°C)", 15, 40, 30)
    J_O2 = st.slider("O₂ influx (rel)", 0.0, 1.0, 0.3)
    P_H2 = st.slider("H₂ production (µmol/g/h)", 0.0, 8.0, 2.0)
    f_aceto = st.slider("Acetogen H₂ use", 0.0, 1.0, 0.8)
    Rdot = st.slider("Metabolic rate (J/g/h)", 0.5, 50.0, DEFAULT_RMET)
    Facet = st.slider("Fraction ATP from acetate", 0.5, 1.0, 0.9)
    radius_mm = st.slider("Gut radius (mm)", 0.1, 1.5, 0.5)
    k_r = st.slider("Radial decay rate", 1.0, 10.0, 5.0)

# ───── CALCULATIONS ─────────────────────────────────────────────
T_ret = compute_Tret(Mmg, GutFrac, FeedingRate, Digestibility, Motility)
st.sidebar.metric("Resulting T_ret (h)", f"{T_ret:.2f}")

xi, pH, O2_uM, H2_kPa, Eh = axial_profiles(H, T_ret, alpha, J_O2, P_H2)

sol = o2_solubility_uM_per_kPa(tempC)
uM_to_kPa = 1 / sol
O2_thr_kPa = 1 * uM_to_kPa

# Radial slice
r_rel = np.linspace(0, 1, 150)
μm = r_rel * radius_mm * 1000
comp = st.selectbox("Radial slice at", list(COMPART.keys()), index=1)
idx = int(COMPART[comp] * (len(xi) - 1))
core = pd.Series({"O2_uM": O2_uM[idx], "H2_kPa": H2_kPa[idx], "pH": pH[idx]})
O2k, H2k, pHr = radial_profile(core.O2_uM, core.H2_kPa, core.pH, r_rel, k_r, uM_to_kPa)
rad_df = pd.DataFrame({"μm": μm, "O2_kPa": O2k, "H2_kPa": H2k, "pH": pHr})
micro = rad_df[rad_df.O2_kPa > O2_thr_kPa]
r0, r1 = (micro.μm.min(), micro.μm.max()) if not micro.empty else (0, 0)

A_prod, A_need = acetate_balance(P_H2, f_aceto, 0.4 * Mmg / 1000, Mmg, Rdot, Facet)
energy_ok = A_prod >= A_need

# ───── PLOTS & METRICS ──────────────────────────────────────────
tab1, tab2 = st.tabs(["Axial profiles","Radial slice"])

with tab1:
    st.subheader("Axial variation")
    df_ax = pd.DataFrame({"x": xi, "pH": pH, "O2_uM": O2_uM, "H2_kPa": H2_kPa, "Eh": Eh})
    p1 = alt.Chart(df_ax).mark_line().encode(x='x', y=alt.Y('pH', title='pH')).properties(height=150)
    p2 = alt.Chart(df_ax).transform_calculate(O2_kPa='datum.O2_uM * %.5f'%uM_to_kPa).mark_line(color='black').encode(
        x='x', y=alt.Y('O2_kPa', title='O₂ (kPa)')
    ).properties(height=150)
    p3 = alt.Chart(df_ax).mark_line(color='green').encode(x='x', y=alt.Y('H2_kPa', title='H₂ (kPa)')).properties(height=150)
    p4 = alt.Chart(df_ax).mark_line(color='gray').encode(x='x', y=alt.Y('Eh', title='Eh (mV)')).properties(height=150)
    st.altair_chart(p1 & p2 & p3 & p4, use_container_width=True)

with tab2:
    st.subheader(f"Radial profiles at {comp}")
    shell = lambda y: alt.Chart(pd.DataFrame({"x":[r0],"x2":[r1],"y":[y[0]],"y2":[y[1]]})).mark_rect(
        opacity=.15, color='gray').encode(x='x', x2='x2', y='y', y2='y2')
    O2r = alt.Chart(rad_df).mark_line(color='black').encode(x='μm', y=alt.Y('O2_kPa',title='O₂ (kPa)'))
    H2r = alt.Chart(rad_df).mark_line(color='green',strokeDash=[6,4]).encode(x='μm', y=alt.Y('H2_kPa',title='H₂ (kPa)'))
    pHr = alt.Chart(rad_df).mark_line(color='purple').encode(x='μm', y=alt.Y('pH',title='pH'))
    pH_min, pH_max = rad_df["pH"].min()-0.1, rad_df["pH"].max()+0.1

    st.altair_chart(
        (shell([0, rad_df["O2_kPa"].max()*1.1]) + O2r)
        & (shell([0, rad_df["H2_kPa"].max()*1.1]) + H2r)
        & (shell([pH_min, pH_max]) + pHr),
        use_container_width=True
    )

# Summary
m1,m2,m3,m4 = st.columns(4)
m1.metric("T_ret (h)", f"{T_ret:.2f}")
m2.metric("O₂ shell δ", f"{r1:.0f} µm")
m3.metric("Acetate prod", f"{A_prod:.2f}")
m4.metric("Needed", f"{A_need:.2f}", delta=None if energy_ok else "⚠ short")

if energy_ok:
    st.success("✔ Energy budget satisfied")
else:
    st.error("✖ Shortfall: increase feeding, gut size, digestibility, motility, α, or H")

with st.expander("Download CSVs"):
    st.download_button("Axial", pd.DataFrame(df_ax).to_csv(index=False).encode(), "axial.csv", "text/csv")
    st.download_button("Radial", rad_df.to_csv(index=False).encode(), "radial.csv", "text/csv")
