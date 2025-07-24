import numpy as np, pandas as pd, altair as alt, streamlit as st

# —————— CONSTANTS —————————————————————————————
BASE_RETENTION = 14.0
DG_ACETATE     = 8.7e5
DEFAULT_RMET   = 8.0
COMPART = {"P1 (mixed)": 0.00, "P3 (paunch)": .35,
           "P4 (colon)": .70, "P5 (rectum)": 1.00}

# —————— MODEL FUNCTIONS —————————————————————————
def o2_solubility_uM_per_kPa(T):
    return 12.56 - 0.1667 * (T - 25)

def axial_profiles(H, T_ret, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2_uM = np.maximum(0, 100 * J_O2 * np.exp(-10 * x / (T_ret / BASE_RETENTION)))
    H2_kPa = np.maximum(0, P_H2 * (1 - np.exp(-6 * (x - 0.2))))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2_uM - 40 * H2_kPa
    return pd.DataFrame({"x": x, "pH": pH, "O2_uM": O2_uM, "H2_kPa": H2_kPa, "Eh": Eh})

def radial_profile(O2_wall_uM, H2_core_kPa, pH_core, r_rel, k_r, sol_kPa_per_uM):
    O2_kPa = (O2_wall_uM * sol_kPa_per_uM) * np.exp(-k_r * (1 - r_rel))
    H2_kPa = H2_core_kPa * (1 - np.exp(-k_r * r_rel))
    pH      = pH_core - 0.5 * (1 - r_rel)
    return O2_kPa, H2_kPa, pH

def acetate_balance(P_H2, f_aceto, gut_mass_g, Mmg, Rdot, Facet):
    A_prod = f_aceto * P_H2 * gut_mass_g
    E_need = Rdot * (Mmg / 1000)
    A_need = Facet * E_need / DG_ACETATE * 1e6
    return A_prod, A_need

def compute_Tret(Mmg, GutFrac, FeedingRate, Digestibility, Motility):
    V_gut = Mmg * GutFrac / 1000
    Q_flow = FeedingRate * Digestibility * Motility
    return V_gut / Q_flow if Q_flow > 0 else 0

# —————— APP UI ——————————————————————————————
st.title("Termite gut simulator — retention model fixed")

with st.sidebar:
    Mmg = st.slider("Body mass (mg)", 1, 200, 12)
    GutFrac = st.slider("Hindgut fraction", 0.05, 0.5, 0.2)
    FeedingRate = st.slider("Feeding rate (mg/h)", 0.1, 50.0, 5.0)
    Digestibility = st.slider("Digestibility", 0.2, 1.0, 0.6)
    Motility = st.slider("Motility", 0.1, 1.0, 0.5)
    H = st.slider("Humification H", 0.0, 1.0, 0.5)
    alpha = st.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
    tempC = st.slider("Temperature (°C)", 15, 40, 30)
    J_O2 = st.slider("O₂ influx", 0.0, 1.0, 0.3)
    P_H2 = st.slider("H₂ production", 0.0, 8.0, 2.0)
    f_aceto = st.slider("Acetogen H₂ use", 0.0, 1.0, 0.8)
    Rdot = st.slider("Metabolic rate (J/g/h)", 0.5, 50.0, DEFAULT_RMET)
    Facet = st.slider("ATP fraction", 0.5, 1.0, 0.9)
    radius_mm = st.slider("Gut radius (mm)", 0.1, 1.5, 0.5)
    k_r = st.slider("Radial decay rate", 1.0, 10.0, 5.0)

T_ret = compute_Tret(Mmg, GutFrac, FeedingRate, Digestibility, Motility)
st.sidebar.metric("T_ret (h)", f"{T_ret:.2f}")

# —————— COMPUTATION ————————————————————————————
df_ax = axial_profiles(H, T_ret, alpha, J_O2, P_H2)
sol = o2_solubility_uM_per_kPa(tempC)
uM_to_kPa = 1 / sol
O2_thr_kPa = uM_to_kPa

r_rel = np.linspace(0, 1, 150)
μm = r_rel * radius_mm * 1000
comp = st.selectbox("Radial slice at", list(COMPART.keys()), index=1)
idx = int(COMPART[comp] * (len(df_ax) - 1))
core = df_ax.iloc[idx]
O2k, H2k, pHr = radial_profile(core.O2_uM, core.H2_kPa, core.pH, r_rel, k_r, uM_to_kPa)
rad_df = pd.DataFrame({"μm": μm, "O2_kPa": O2k, "H2_kPa": H2k, "pH": pHr})
micro = rad_df[rad_df.O2_kPa > O2_thr_kPa]
r0, r1 = (micro.μm.min(), micro.μm.max()) if not micro.empty else (0, 0)

A_prod, A_need = acetate_balance(P_H2, f_aceto, 0.4 * Mmg / 1000, Mmg, Rdot, Facet)
energy_ok = A_prod >= A_need

# —————— PLOTTING ——————————————————————————————
tab1, tab2 = st.tabs(["Axial", "Radial"])

with tab1:
    st.subheader("Axial profiles")
    df_plot = df_ax.copy()
    df_plot["O2_kPa"] = df_plot.O2_uM * uM_to_kPa

    p1 = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('x', title='Axial position'),
        y=alt.Y('pH', title='pH')
    )
    p2 = alt.Chart(df_plot).mark_line(color='black').encode(
        x=alt.X('x', title='Axial position'),
        y=alt.Y('O2_kPa', title='O₂ (kPa)')
    )
    p3 = alt.Chart(df_plot).mark_line(color='green').encode(
        x=alt.X('x', title='Axial position'),
        y=alt.Y('H2_kPa', title='H₂ (kPa)')
    )
    p4 = alt.Chart(df_plot).mark_line(color='gray').encode(
        x=alt.X('x', title='Axial position'),
        y=alt.Y('Eh', title='Eh (mV)')
    )

    st.altair_chart((p1 & p2 & p3 & p4).resolve_axis(y='independent'), use_container_width=True)

with tab2:
    st.subheader(f"Radial slice at {comp}")
    shell = lambda y: alt.Chart(pd.DataFrame({"x":[r0],"x2":[r1],"y":[y[0]],"y2":[y[1]]})).mark_rect(
        opacity=0.15, color="gray"
    ).encode(x='x', x2='x2', y='y', y2='y2')
    O2r = alt.Chart(rad_df).mark_line(color='black').encode(x='μm', y='O2_kPa')
    H2r = alt.Chart(rad_df).mark_line(color='green', strokeDash=[6,4]).encode(x='μm', y='H2_kPa')
    pHr_chart = alt.Chart(rad_df).mark_line(color='purple').encode(x='μm', y='pH')

    st.altair_chart(
        (shell([0, rad_df.O2_kPa.max()*1.1]) + O2r)
        & (shell([0, rad_df.H2_kPa.max()*1.1]) + H2r)
        & (shell([rad_df.pH.min()-0.1, rad_df.pH.max()+0.1]) + pHr_chart),
        use_container_width=True
    )

# —————— METRICS ——————————————————————————————
c1, c2, c3, c4 = st.columns(4)
c1.metric("T_ret (h)", f"{T_ret:.2f}")
c2.metric("O₂ shell δ", f"{r1:.0f} µm")
c3.metric("Acetate prod", f"{A_prod:.2f}")
c4.metric("Needed", f"{A_need:.2f}", delta=None if energy_ok else "⚠ short")

if energy_ok:
    st.success("✔ Energy OK")
else:
    st.error("✖ Shortfall – adjust inputs accordingly")

with st.expander("Download CSVs"):
    st.download_button("Axial CSV", df_ax.to_csv(index=False).encode(), "axial.csv", "text/csv")
    st.download_button("Radial CSV", rad_df.to_csv(index=False).encode(), "radial.csv", "text/csv")
