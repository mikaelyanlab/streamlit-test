# app.py
# Decomposer Biodiversity Risk Model — v2 (time-series, uncertainty, DFI, payouts)

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass

st.set_page_config(page_title="Decomposer Biodiversity Risk Model (v2)", layout="wide")

# =========================
# Helpers & domain functions
# =========================

def moisture_response(theta, th_opt=0.35, th_bw=0.25):
    """Bell-shaped moisture response (0..1) centered at th_opt with bandwidth th_bw (FWHM-like)."""
    # Convert bandwidth to Gaussian sigma (FWHM≈2.355σ)
    sigma = (th_bw / 2.355)
    return np.exp(-((theta - th_opt) ** 2) / (2 * sigma ** 2))

def f_biodiversity(B, alpha=0.6, Kb=30):
    """Biodiversity multiplier, saturating with B (0..100)."""
    B = np.clip(B, 0.0, 100.0)
    return 1.0 + alpha * (B / (B + Kb + 1e-9))

def f_insect(I_idx, temp, theta, t_opt=28, t_min=10, th_min=0.12):
    """Simple gating for insect activity (0..1) with temperature/moisture thresholds; returns multiplier 1..1+I."""
    gate = (temp >= t_min) & (theta >= th_min)
    return 1.0 + (I_idx * gate.astype(float))

def k_rate(T, theta, B, I_idx, k0=0.03, Q10=2.0, th_opt=0.35, th_bw=0.25, alpha=0.6, Kb=30):
    """Daily decomposition rate constant (1/day)."""
    q10 = Q10 ** ((T - 20.0) / 10.0)
    return (
        k0
        * q10
        * moisture_response(theta, th_opt=th_opt, th_bw=th_bw)
        * f_biodiversity(B, alpha=alpha, Kb=Kb)
        * f_insect(I_idx, T, theta)
    )

def vpd_from_T_RH(T, RH):
    """Approximate Vapor Pressure Deficit (kPa) from Temperature (°C) and RH (%)."""
    # Tetens formula
    es = 0.6108 * np.exp((17.27 * T) / (T + 237.3))
    ea = es * (RH / 100.0)
    return np.maximum(es - ea, 0.0)

def fire_intensity_proxy(F, wind, T, theta):
    """Proxy for surface fire intensity: fuel^1.5 * wind factor * dryness factor."""
    F = np.maximum(F, 1e-6)
    phi_w = 1.0 + 0.04 * np.clip(wind, 0, 25)  # linear-ish wind effect
    dryness = 1.0 + np.clip((0.35 - theta), 0, 0.35) * 2.0  # drier → higher intensity
    heat = 1.0 + 0.02 * np.clip(T - 20.0, 0, 20)           # hotter → slightly higher
    return (F ** 1.5) * phi_w * dryness * heat

def usle_erosion(R, SOM, LS=1.2, C_base=0.3, P=1.0, F=None, theta=None, B=None):
    """
    USLE-style: A = R * K * LS * C * P
    K decreases with SOM; C decreases with mulch/cover (proxied by F, theta, B).
    """
    # Soil erodibility K: lower with higher SOM (toy relationship)
    K0 = 0.032
    K = K0 * np.exp(-2.0 * np.clip(SOM, 0, 0.1)/0.1)  # 0..0.1 SOM fraction (~0..10% by mass)
    # Cover C reduced by moisture, biodiversity, and surface mulch (inverse of exposed soil)
    if F is None: F = 20.0
    if theta is None: theta = 0.25
    if B is None: B = 50.0
    cover_bonus = 0.5 * (theta/0.35) + 0.5 * (B/100.0)  # 0..~1
    cover_bonus = np.clip(cover_bonus, 0, 1.2)
    mulch_effect = 1.0 / (1.0 + 0.02 * np.clip(F, 0, 50))  # more fuel = more surface litter → less erosion
    C = C_base * mulch_effect * (1.0 - 0.4 * cover_bonus)
    C = np.clip(C, 0.02, 0.5)
    return R * K * LS * C * P

def rainfall_erosivity(P):
    """Very simple daily erosivity index R from precipitation P (mm/day)."""
    # Heavier events drive erosivity; threshold at 10 mm
    return np.maximum(P - 10.0, 0.0) ** 1.2 / 10.0

# =========================
# Simulation core
# =========================

@dataclass
class SimParams:
    F0: float       # initial fuel (kg/m2)
    theta0: float   # initial soil moisture (0..1)
    SOM0: float     # initial soil organic matter (fraction of soil mass, 0..~0.1)
    B: float        # biodiversity index (0..100)
    I_idx: float    # insect activity scale (0..0.6)
    k0: float       # base decomposition rate (1/day)
    Q10: float      # temperature sensitivity
    Z: float        # bucket depth (m)
    FC: float       # field capacity (volumetric, 0..1)
    Rm: float       # daily mechanical removal/burn (kg/m2/day)

def simulate_once(T, P, RH, wind, L, ET, Qd, params: SimParams, dt=1.0):
    """
    Daily time-step simulation for fuel F, soil moisture theta, SOM, and derived risk metrics.
    """
    n = len(T)
    F = np.zeros(n); theta = np.zeros(n); SOM = np.zeros(n); kval = np.zeros(n)
    F[0] = params.F0; theta[0] = params.theta0; SOM[0] = params.SOM0

    for t in range(1, n):
        k = k_rate(T[t-1], theta[t-1], params.B, params.I_idx, k0=params.k0, Q10=params.Q10)
        kval[t-1] = k
        # Fuel dynamics: add litter, minus decay, minus removals
        F[t] = F[t-1] + L[t-1] * dt - k * F[t-1] * dt - params.Rm * dt
        F[t] = np.clip(F[t], 0.0, 100.0)

        # Simple bucket soil moisture
        dtheta = (P[t-1] - ET[t-1] - Qd[t-1]) / (params.Z * params.FC * 1000.0)  # mm to m^3/m^3
        theta[t] = np.clip(theta[t-1] + dtheta, 0.0, 0.6)

        # SOM accrual from decomposition (toy)
        SOM[t] = np.clip(SOM[t-1] + 0.08 * k * F[t-1] * dt / 1000.0, 0.0, 0.12)

    # final k
    kval[-1] = k_rate(T[-1], theta[-1], params.B, params.I_idx, k0=params.k0, Q10=params.Q10)

    # Derived metrics
    vpd = vpd_from_T_RH(T, RH)
    I_fire = fire_intensity_proxy(F, wind, T, theta)
    R = rainfall_erosivity(P)
    A_erosion = usle_erosion(R, SOM, F=F, theta=theta, B=params.B)

    out = pd.DataFrame({
        "day": np.arange(n),
        "T_C": T, "P_mm": P, "RH_%": RH, "Wind_ms": wind,
        "VPD_kPa": vpd,
        "Fuel_kgm2": F,
        "Theta_vwc": theta,
        "SOM_frac": SOM,
        "k_day": kval,
        "FireProxy": I_fire,
        "USLE_A": A_erosion
    })
    return out

def mc_run(n_draws, T, P, RH, wind, L, ET, Qd, base: SimParams, rng=42):
    """Monte Carlo: randomize key parameters and drivers to provide uncertainty bands."""
    r = np.random.default_rng(rng)
    results = []
    for _ in range(n_draws):
        p = SimParams(
            F0 = np.clip(r.normal(base.F0, 1.0), 1.0, 80.0),
            theta0 = np.clip(r.normal(base.theta0, 0.05), 0.05, 0.5),
            SOM0 = np.clip(r.normal(base.SOM0, 0.005), 0.0, 0.12),
            B = np.clip(r.normal(base.B, 5.0), 1.0, 100.0),
            I_idx = np.clip(r.normal(base.I_idx, 0.05), 0.0, 0.6),
            k0 = np.exp(r.normal(np.log(base.k0), 0.25)),
            Q10 = np.clip(r.normal(base.Q10, 0.3), 1.5, 2.8),
            Z = base.Z,
            FC = base.FC,
            Rm = np.clip(r.normal(base.Rm, 0.01), 0.0, 0.2)
        )
        # jitter drivers
        Tj = T + r.normal(0, 1.5, size=len(T))
        Pj = np.clip(P + r.normal(0, 2.0, size=len(P)), 0, None)
        RHj = np.clip(RH + r.normal(0, 4.0, size=len(RH)), 20, 100)
        windj = np.clip(wind + r.normal(0, 1.0, size=len(wind)), 0, None)
        Lj = np.clip(L * r.uniform(0.85, 1.15, size=len(L)), 0, None)
        ETj = np.clip(ET * r.uniform(0.85, 1.15, size=len(ET)), 0, None)
        Qdj = np.clip(Qd * r.uniform(0.85, 1.15, size=len(Qd)), 0, None)

        df = simulate_once(Tj, Pj, RHj, windj, Lj, ETj, Qdj, p)
        results.append(df)
    return results

# =========================
# DFI + payouts
# =========================

def decomposer_functional_index(mass_loss_7d, respiration, enzyme_z, insect_activity):
    """
    Normalize to 0..1 then weighted sum.
    mass_loss_7d: fraction (0..1), e.g., 0.15 ~ healthy
    respiration: mg CO2-C g-1 d-1, e.g., 3.0 ~ healthy
    enzyme_z: Z-score composite (0..1)
    insect_activity: 0..1
    """
    m = np.clip(mass_loss_7d / 0.15, 0, 1)
    r = np.clip(respiration / 3.0, 0, 1)
    e = np.clip(enzyme_z, 0, 1)
    i = np.clip(insect_activity, 0, 1)
    return 0.35*m + 0.30*r + 0.20*e + 0.15*i

def payout_from_dfi(dfi, tier=(0.25, 0.50, 0.70), amounts=(1_000_000, 500_000, 200_000)):
    """
    Payout schedule: lower DFI under co-trigger → higher payout.
    Returns payout dollars given DFI and tiers.
    """
    if dfi < tier[0]: return amounts[0]
    if dfi < tier[1]: return amounts[1]
    if dfi < tier[2]: return amounts[2]
    return 0

# =========================
# Synthetic drivers or upload
# =========================

def synthetic_climate(n_days, climate="temperate", seed=0):
    r = np.random.default_rng(seed)
    day = np.arange(n_days)

    if climate == "arid":
        T = 28 + 7*np.sin(2*np.pi*day/90) + r.normal(0, 1.0, n_days)
        P = np.clip(r.gamma(1.2, 2.0, n_days), 0, None) # sparse rain
        RH = np.clip(30 + 10*np.sin(2*np.pi*day/60) + r.normal(0, 5, n_days), 15, 60)
        wind = np.clip(4 + r.normal(0, 1.0, n_days), 0, None)
    elif climate == "humid":
        T = 26 + 5*np.sin(2*np.pi*day/90) + r.normal(0, 1.0, n_days)
        P = np.clip(r.gamma(3.0, 4.0, n_days), 0, None)
        RH = np.clip(70 + 10*np.sin(2*np.pi*day/60) + r.normal(0, 5, n_days), 50, 100)
        wind = np.clip(2.5 + r.normal(0, 0.8, n_days), 0, None)
    else:  # temperate
        T = 20 + 8*np.sin(2*np.pi*day/90) + r.normal(0, 1.2, n_days)
        P = np.clip(r.gamma(2.0, 3.5, n_days), 0, None)
        RH = np.clip(55 + 12*np.sin(2*np.pi*day/60) + r.normal(0, 6, n_days), 30, 95)
        wind = np.clip(3 + r.normal(0, 1.0, n_days), 0, None)

    # Potential ET proxy from temperature & VPD
    vpd = vpd_from_T_RH(T, RH)
    ET = np.clip(1.2 + 0.12*T + 0.8*vpd + 0.2*wind, 0, None)  # mm/day
    Qd = np.clip(0.1 * np.maximum(P - 15, 0), 0, None)        # quick runoff
    # Litterfall based on climate
    if climate == "arid": L = np.full(n_days, 0.03)  # kg/m2/day
    elif climate == "humid": L = np.full(n_days, 0.06)
    else: L = np.full(n_days, 0.045)

    return T, P, RH, wind, L, ET, Qd

# =========================
# UI
# =========================

st.title("Decomposer Biodiversity Risk Model — v2")
st.caption("Time-series decomposition → fuel/soil dynamics → fire & erosion risk, with Monte-Carlo uncertainty and parametric DFI payouts.")

col1, col2 = st.columns([1, 2.2])

with col1:
    st.subheader("Controls")
    climate = st.selectbox("Climate", ["arid", "temperate", "humid"], index=1)
    biome = st.selectbox("Biome (for LS, litter defaults)", ["Arid Deserts", "Temperate Forests", "Humid Tropics"], index=1)
    n_days = st.slider("Simulation Length (days)", 60, 365, 180, step=15)

    st.markdown("**Decomposer Function & Fuel**")
    B = st.slider("Biodiversity Index (0–100)", 0, 100, 60)
    I_idx = st.slider("Insect Activity Scale (0–0.6)", 0.0, 0.6, 0.25, 0.01)
    F0 = st.slider("Initial Fuel Load F₀ (kg/m²)", 2.0, 50.0, 20.0)
    theta0 = st.slider("Initial Soil Moisture θ₀ (v/v)", 0.05, 0.50, 0.25, 0.01)
    SOM0 = st.slider("Initial SOM (fraction, 0–0.12)", 0.00, 0.12, 0.04, 0.005)
    Rm = st.slider("Mgmt Removal R (kg/m²/day)", 0.00, 0.20, 0.00, 0.01)

    st.markdown("**Kinetics**")
    k0 = st.slider("Base k₀ (1/day)", 0.005, 0.10, 0.03, 0.001)
    Q10 = st.slider("Q10 (temp sensitivity)", 1.5, 2.8, 2.0, 0.1)

    st.markdown("**Soil Bucket**")
    Z = st.slider("Bucket Depth Z (m)", 0.1, 1.0, 0.3, 0.05)
    FC = st.slider("Field Capacity (v/v)", 0.15, 0.45, 0.30, 0.01)

    st.markdown("**Uncertainty**")
    n_mc = st.slider("Monte-Carlo Draws", 100, 1000, 400, 50)
    seed = st.number_input("Random Seed", value=42, step=1)

    st.markdown("**Economics**")
    $per_fire_unit = st.number_input("$/unit Fire Intensity (per ha)", value=2500, step=100)
    $per_ton_sed = st.number_input("$/ton Sediment (removal/impact)", value=40, step=5)
    area_ha = st.number_input("Project Area (ha)", value=10000, step=1000)

    st.markdown("**Parametric Index (DFI) & Payouts**")
    red_flag_vpd = st.slider("Red-Flag VPD (kPa) threshold", 1.0, 4.0, 2.0, 0.1)
    tier1, tier2, tier3 = st.columns(3)
    with tier1:
        dfi_t1 = st.number_input("DFI Tier 1 (<)", value=0.25, step=0.05, format="%.2f")
        pay1 = st.number_input("Payout Tier 1 ($)", value=1_000_000, step=100_000)
    with tier2:
        dfi_t2 = st.number_input("DFI Tier 2 (<)", value=0.50, step=0.05, format="%.2f")
        pay2 = st.number_input("Payout Tier 2 ($)", value=500_000, step=50_000)
    with tier3:
        dfi_t3 = st.number_input("DFI Tier 3 (<)", value=0.70, step=0.05, format="%.2f")
        pay3 = st.number_input("Payout Tier 3 ($)", value=200_000, step=25_000)

    st.markdown("---")
    st.markdown("**Optional: Upload Drivers**")
    st.caption("CSV with columns: day,T_C,P_mm,RH_%,Wind_ms,ET_mm,Q_mm,L_kgm2")
    upl = st.file_uploader("Upload climate/driver CSV (optional)", type=["csv"])

with col2:
    st.subheader("Simulation & Results")

    # Drivers
    if upl is not None:
        drv = pd.read_csv(upl)
        # basic validation
        needed = ["day","T_C","P_mm","RH_%","Wind_ms","ET_mm","Q_mm","L_kgm2"]
        if not all(c in drv.columns for c in needed):
            st.error(f"CSV missing required columns: {set(needed)-set(drv.columns)}")
            st.stop()
        drv = drv.sort_values("day").reset_index(drop=True)
        if len(drv) < n_days:
            st.warning("Uploaded series shorter than n_days; truncating simulation.")
            n = len(drv)
        else:
            n = n_days
        T, P, RH, wind = drv["T_C"].values[:n], drv["P_mm"].values[:n], drv["RH_%"].values[:n], drv["Wind_ms"].values[:n]
        ET, Qd, L = drv["ET_mm"].values[:n], drv["Q_mm"].values[:n], drv["L_kgm2"].values[:n]
    else:
        T, P, RH, wind, L, ET, Qd = synthetic_climate(n_days, climate=climate, seed=seed)

    # Baseline (counterfactual) without decomposer enhancement: hold B=10, I=0, same mgmt
    base_params_cf = SimParams(F0=F0, theta0=theta0, SOM0=SOM0, B=10.0, I_idx=0.0, k0=k0, Q10=Q10, Z=Z, FC=FC, Rm=Rm)
    df_cf = simulate_once(T, P, RH, wind, L, ET, Qd, base_params_cf)

    # Scenario with selected B, I
    base_params = SimParams(F0=F0, theta0=theta0, SOM0=SOM0, B=B, I_idx=I_idx, k0=k0, Q10=Q10, Z=Z, FC=FC, Rm=Rm)
    df = simulate_once(T, P, RH, wind, L, ET, Qd, base_params)

    # Monte Carlo on scenario
    mc = mc_run(n_mc, T, P, RH, wind, L, ET, Qd, base_params, rng=seed)
    # Aggregate uncertainty bands
    def summarize_mc(mc_list, col):
        M = np.vstack([d[col].values for d in mc_list])
        return np.percentile(M, [5,50,95], axis=0)  # shape (3, n_days)

    qF = summarize_mc(mc, "Fuel_kgm2")
    qFire = summarize_mc(mc, "FireProxy")
    qA = summarize_mc(mc, "USLE_A")
    qTheta = summarize_mc(mc, "Theta_vwc")
    qSOM = summarize_mc(mc, "SOM_frac")

    # Risk reductions vs. baseline
    # Use last-day comparison and cumulative comparison
    fire_red_pct = 100.0 * (1.0 - df["FireProxy"].values / (df_cf["FireProxy"].values + 1e-9))
    eros_red = df_cf["USLE_A"].values - df["USLE_A"].values
    eros_red_pct = 100.0 * (eros_red / (df_cf["USLE_A"].values + 1e-9))

    # Economics (very simplified): sum over days, scale by area
    # For fire, convert proxy to cost units then take difference
    fire_cost_cf = df_cf["FireProxy"].sum() * ($per_fire_unit / 1e6) * area_ha
    fire_cost_sc = df["FireProxy"].sum() * ($per_fire_unit / 1e6) * area_ha
    fire_avoided = max(fire_cost_cf - fire_cost_sc, 0.0)

    # For erosion, convert USLE daily "A" proxy to tons/ha-day (toy) then to $/ton
    # Assume 1 unit A ≈ 0.5 ton/ha-day (placeholder)
    ton_per_A = 0.5
    sed_cf_tons = df_cf["USLE_A"].sum() * ton_per_A * area_ha
    sed_sc_tons = df["USLE_A"].sum() * ton_per_A * area_ha
    sed_avoided_tons = max(sed_cf_tons - sed_sc_tons, 0.0)
    erosion_avoided_$ = sed_avoided_tons * $per_ton_sed

    total_avoided = fire_avoided + erosion_avoided_$

    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.metric("Final Fuel (kg/m²)", f"{df['Fuel_kgm2'].iloc[-1]:.2f}")
        st.metric("Final θ (v/v)", f"{df['Theta_vwc'].iloc[-1]:.2f}")
    with colB:
        st.metric("Fire Proxy Reduction (median % last day)", f"{np.median(fire_red_pct[-7:]):.1f}")
        st.metric("Erosion Reduction (median % last day)", f"{np.median(eros_red_pct[-7:]):.1f}")
    with colC:
        st.metric("Avoided Fire Cost ($)", f"{fire_avoided:,.0f}")
        st.metric("Avoided Erosion Cost ($)", f"{erosion_avoided_$:,.0f}")
    with colD:
        st.metric("Total Avoided Loss ($)", f"{total_avoided:,.0f}")
        st.caption("Sum of avoided fire + erosion impacts (toy conversions).")

    # ===== Plots =====
    def band_plot(x, q, median_name, title, ylab):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=q[1], mode="lines", name=median_name, line=dict(color="#1f77b4", width=2)))
        fig.add_trace(go.Scatter(x=x, y=q[2], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=q[0], mode="lines", fill="tonexty", name="5–95% band",
                                 line=dict(width=0), fillcolor="rgba(31,119,180,0.2)"))
        fig.update_layout(title=title, xaxis_title="Day", yaxis_title=ylab, template="plotly_white")
        return fig

    st.markdown("### Uncertainty Bands")
    st.plotly_chart(band_plot(df["day"], qF, "Fuel (median)", "Fuel Load with Uncertainty", "kg/m²"), use_container_width=True)
    st.plotly_chart(band_plot(df["day"], qTheta, "Soil Moisture θ (median)", "Soil Moisture", "v/v"), use_container_width=True)
    st.plotly_chart(band_plot(df["day"], qFire, "Fire Proxy (median)", "Fire Intensity Proxy", "arb units"), use_container_width=True)
    st.plotly_chart(band_plot(df["day"], qA, "USLE A (median)", "Erosion Risk (USLE-like)", "arb units"), use_container_width=True)

    # Counterfactual vs Scenario comparison
    st.markdown("### Scenario vs Counterfactual (No Decomposer Boost)")
    comp = pd.DataFrame({
        "day": df["day"],
        "Fire_CF": df_cf["FireProxy"],
        "Fire_Sc": df["FireProxy"],
        "USLE_CF": df_cf["USLE_A"],
        "USLE_Sc": df["USLE_A"]
    })
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=comp["day"], y=comp["Fire_CF"], name="Fire CF", line=dict(color="#d62728")))
    fig2.add_trace(go.Scatter(x=comp["day"], y=comp["Fire_Sc"], name="Fire Scenario", line=dict(color="#2ca02c")))
    fig2.update_layout(title="Fire Proxy: Scenario vs Counterfactual", xaxis_title="Day", yaxis_title="arb units", template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=comp["day"], y=comp["USLE_CF"], name="USLE CF", line=dict(color="#9467bd")))
    fig3.add_trace(go.Scatter(x=comp["day"], y=comp["USLE_Sc"], name="USLE Scenario", line=dict(color="#8c564b")))
    fig3.update_layout(title="Erosion Risk: Scenario vs Counterfactual", xaxis_title="Day", yaxis_title="arb units", template="plotly_white")
    st.plotly_chart(fig3, use_container_width=True)

    # ===== DFI & Payouts (microcosm placeholder) =====
    st.markdown("### Decomposer Functional Index (DFI) & Parametric Payouts")

    st.caption("Provide rolling 7-day microcosm metrics (or use defaults).")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        mass_loss_7d = st.number_input("7-day litter mass loss (fraction)", value=0.12, min_value=0.0, max_value=1.0, step=0.01, format="%.2f")
    with c2:
        respiration = st.number_input("Respiration (mg CO₂-C g⁻¹ d⁻¹)", value=2.5, step=0.1, format="%.2f")
    with c3:
        enzyme_z = st.number_input("Enzyme composite Z (0..1)", value=0.6, min_value=0.0, max_value=1.0, step=0.05)
    with c4:
        insect_act = st.number_input("Insect activity (0..1)", value=0.5, min_value=0.0, max_value=1.0, step=0.05)

    dfi = decomposer_functional_index(mass_loss_7d, respiration, enzyme_z, insect_act)
    st.metric("DFI (0–1)", f"{dfi:.2f}")

    # Red-flag co-trigger based on current climate (use last 3 days VPD & wind)
    vpd_last = df["VPD_kPa"].tail(3).mean()
    wind_last = df["Wind_ms"].tail(3).mean()
    red_flag = (vpd_last >= red_flag_vpd) or (wind_last >= 8.0)

    payout = 0
    if red_flag:
        payout = payout_from_dfi(dfi, tier=(dfi_t1, dfi_t2, dfi_t3), amounts=(pay1, pay2, pay3))

    st.write(f"**Red-flag condition?** {'🟥 YES' if red_flag else '⬜ NO'}  |  3-day mean VPD = {vpd_last:.2f} kPa, wind = {wind_last:.1f} m/s")
    st.metric("Parametric Payout ($)", f"{payout:,.0f}")

    # ===== Downloads (CSV summaries) =====
    st.markdown("### Downloads")
    summary = {
        "climate": climate,
        "biome": biome,
        "days": n_days,
        "B": B,
        "I_idx": I_idx,
        "F0": F0,
        "theta0": theta0,
        "SOM0": SOM0,
        "Rm": Rm,
        "k0": k0,
        "Q10": Q10,
        "Z": Z,
        "FC": FC,
        "MC_draws": n_mc,
        "Avoided_Fire_$": fire_avoided,
        "Avoided_Erosion_$": erosion_avoided_$,
        "Total_Avoided_$": total_avoided,
        "DFI": dfi,
        "RedFlag": red_flag,
        "Payout_$": payout
    }
    sum_df = pd.DataFrame([summary])
    st.download_button("Download Summary CSV", data=sum_df.to_csv(index=False), file_name="summary.csv", mime="text/csv")

    # Export full time series (scenario & counterfactual)
    df_out = df.copy()
    for c in ["FireProxy","USLE_A","Fuel_kgm2","Theta_vwc","SOM_frac","k_day"]:
        df_out[f"{c}_CF"] = df_cf[c].values
    st.download_button("Download Timeseries CSV", data=df_out.to_csv(index=False), file_name="timeseries.csv", mime="text/csv")

    # Minimal “term sheet” text
    term_lines = [
        "Decomposer Functional Index (DFI) Parametric Cover — Draft Term Sheet",
        f"Climate/biome: {climate}/{biome}",
        f"Simulation window: {n_days} days; MC draws: {n_mc}",
        f"Triggers: DFI tiers {dfi_t1:.2f}/{dfi_t2:.2f}/{dfi_t3:.2f} with red-flag VPD ≥ {red_flag_vpd:.2f} kPa or wind ≥ 8 m/s",
        f"Payouts: ${pay1:,} / ${pay2:,} / ${pay3:,} (decreasing with higher DFI)",
        f"Current DFI: {dfi:.2f}; Red-flag now: {red_flag}; Indicative payout: ${payout:,}",
        f"Avoided losses (toy): Fire ${fire_avoided:,.0f}, Erosion ${erosion_avoided_$:,.0f}, Total ${total_avoided:,.0f}",
        "Data: DFI from 7-day microcosm metrics (mass loss, respiration, enzyme Z, insect activity).",
        "Auditability: sensor QC, immutable logs, open calculations.",
    ]
    term_blob = "\n".join(term_lines)
    st.download_button("Download Draft Term Sheet (txt)", data=term_blob, file_name="term_sheet.txt", mime="text/plain")

# ===== Footer notes =====
st.markdown("---")
st.caption(
    "Notes: This is a research/education model. Fire & erosion conversions are placeholders; calibrate with local data. "
    "Plug in ERA5/NASA POWER/SoilGrids drivers where indicated and use Bayesian updating from microcosm streams to refine k0,Q10,α."
)
