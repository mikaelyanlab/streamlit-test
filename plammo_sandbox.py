import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- Constants ---
E_a = 50e3  # J/mol for MMO; activation energy
E_a_MeOH = 45e3  # J/mol for methanol oxidation
R = 8.314  # Gas constant, J/mol/K
T_ref = 298.15  # Reference temperature, K
k_MeOH_ref = 0.00011  # 1/s at 25°C
H_0_CH4 = 1.4  # CH4 at 25°C, mmol/L/atm (Sander, 2015)
H_0_O2 = 1.3  # O2 at 25°C, mmol/L/atm (Sander, 2015)
g_s_ref = 0.2  # mol/m²/s; reference stomatal conductance

# --- V_MMO Computation ---
def compute_v_mmo(Vmax_ref, expression_percent, T, Pi, Km_ref, C_cyt, O2_cyt):
    T_K = T + 273.15
    T_opt = 308.15  # 35°C in Kelvin
    k_den = 0.01  # Denaturation rate constant
    Vmax_T = Vmax_ref * (expression_percent / 100.0) * \
             np.exp(-E_a / R * (1.0/T_K - 1.0/T_ref)) * \
             np.exp(-k_den * (T_K - T_opt)**2)
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100.0))
    Km_T = Km_ref * (1.0 + 0.02 * (T - 25.0))
    Km_O2 = 0.0001  # mmol/L

    # Prevent division by zero or negative values
    if Km_T <= 0 or C_cyt < 0 or O2_cyt < 0:
        return 0.0
    denom_ch4 = Km_T + C_cyt
    denom_o2 = Km_O2 + O2_cyt
    if denom_ch4 <= 0 or denom_o2 <= 0:
        return 0.0
    return Vmax * (C_cyt / denom_ch4) * (O2_cyt / denom_o2)

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                     k_L_CH4, k_L_O2, photosynthesis_on, expression_percent):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15

    # Henry’s constants with T and osmolarity adjustments
    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25.0)) * (1.0 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25.0)) * (1.0 - beta * Pi)

    # Partial pressures (atm)
    P_CH4 = C_atm / 1e6  # ppm -> fraction
    P_O2 = O2_atm / 100.0  # % -> fraction

    # Equilibrium concentrations at interface (mmol/L)
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2

    # Fluxes scaled by stomatal conductance
    g_s_scale = g_s / g_s_ref
    J_CH4 = k_L_CH4 * g_s_scale * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2 * g_s_scale * (O2_eq - O2_cyt)

    # MMO activity
    V_MMO = compute_v_mmo(Vmax_ref, expression_percent, T, Pi, Km_ref, C_cyt, O2_cyt)

    # Methanol oxidation rate
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1.0/T_K - 1.0/T_ref))

    # Photosynthetic O2 production
    O2_prod = 0.005 if photosynthesis_on else 0.0

    # ODEs
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    dO2_dt = J_O2 - V_MMO + O2_prod
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# --- Streamlit UI ---
st.title("Methane Oxidation Model (with Optional Photosynthetic O₂)")

# Sidebar inputs
st.sidebar.header("Atmosphere & Gas Transfer")
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
O2_atm = st.sidebar.slider("Atmospheric O₂ (%)", 1.0, 25.0, 21.0)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.05, 2.0, 0.5)
k_L_CH4 = st.sidebar.number_input("CH₄ Mass Transfer Coefficient (1/s)", min_value=0.0001, max_value=0.1, value=0.1, step=1e-6, format="%.6f")
k_L_O2 = st.sidebar.number_input("O₂ Mass Transfer Coefficient (1/s)", min_value=0.0001, max_value=0.1, value=0.1, step=1e-6, format="%.6f")

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of total protein)", 0.1, 20.0, 1.0, step=0.1)
Vmax_ref = st.sidebar.number_input("Vmax_ref (mmol·L_cyt⁻¹·s⁻¹)", min_value=0.001, max_value=0.5, value=0.01, step=1e-6, format="%.6f")
Km_ref = st.sidebar.number_input("Methane Affinity (Km_ref, mmol/L)", min_value=1e-6, max_value=0.005, value=0.001, step=1e-6, format="%.6f")

# Input validation
err = None
if Km_ref <= 0:
    err = "Km_ref must be > 0."
elif Vmax_ref <= 0:
    err = "Vmax_ref must be > 0."
elif k_L_CH4 <= 0 or k_L_O2 <= 0:
    err = "Mass transfer coefficients must be > 0."
elif O2_atm <= 0:
    err = "Atmospheric O₂ must be > 0."
elif C_atm <= 0:
    err = "Atmospheric CH₄ must be > 0."
elif g_s <= 0:
    err = "Stomatal conductance must be > 0."
elif T < -273.15:
    err = "Temperature must be above -273.15°C."
if err:
    st.error(err)
    st.stop()

# Time and initial conditions
time = np.linspace(0, 50000, 5000)
O2_init = H_0_O2 * np.exp(-0.02 * (T - 25.0)) * (1.0 - 0.01 * Pi) * (O2_atm / 100.0)
C0 = [0.0001, 0.0001, O2_init]

# Solve ODEs
def wrapped_ode(t, C):
    return methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                            k_L_CH4, k_L_O2, photosynthesis_on, expression_percent)

sol = solve_ivp(
    fun=wrapped_ode,
    t_span=(time[0], time[-1]),
    y0=C0,
    t_eval=time,
    method="LSODA",
    rtol=1e-6,
    atol=1e-9
).y.T

# Time-series plots
fig_plots = make_subplots(
    rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
    subplot_titles=("Cytosolic CH₄", "Methanol (CH₃OH)", "Cytosolic O₂")
)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode="lines", name="Cytosolic CH₄"), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode="lines", name="Methanol (CH₃OH)"), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode="lines", name="Cytosolic O₂"), row=3, col=1)
fig_plots.update_layout(height=800, title_text="Concentration Dynamics Over Time", showlegend=False)
fig_plots.update_xaxes(title_text="Time (s)", row=3, col=1)
for r in (1, 2, 3):
    fig_plots.update_yaxes(title_text="Concentration (mmol/L)", row=r, col=1)

# Gauge for final V_MMO
C_cyt_final = sol[-1, 0]
O2_cyt_final = sol[-1, 2]
V_MMO_final = compute_v_mmo(Vmax_ref, expression_percent, T, Pi, Km_ref, C_cyt_final, O2_cyt_final)
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s", 'valueformat': '.10g'},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 1e-6]},
        'bar': {'color': "#ffcc00"},
        'steps': [{'range': [i*1e-7, (i+1)*1e-7], 'color': f"rgba(255,0,0,{0.1 + 0.1*i})"} for i in range(10)],
        'threshold': {'line': {'color': "black", 'width': 4}, 'value': V_MMO_final}
    }
))

# Display plots
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_plots, use_container_width=True)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

# --- Sensitivity Analysis ---
st.subheader("Sensitivity Analysis")
param_options = {
    "T": {"label": "Temperature (°C)", "range": np.linspace(5, 45, 200)},
    "expression_percent": {"label": "pMMO Expression (% of total protein)", "range": np.linspace(0.1, 20.0, 200)},
    "Vmax_ref": {"label": "Vmax_ref (mmol·L_cyt⁻¹·s⁻¹)", "range": np.linspace(0.001, 0.1, 200)},
    "Km_ref": {"label": "Methane Affinity (Km_ref, mmol/L)", "range": np.linspace(1e-6, 0.1, 200)},
    "Pi": {"label": "Cytosolic Osmolarity (%)", "range": np.linspace(0, 100, 200)},
    "g_s": {"label": "Stomatal Conductance (mol/m²/s)", "range": np.linspace(0.05, 2.0, 200)},
    "k_L_CH4": {"label": "CH₄ Mass Transfer Coefficient (1/s)", "range": np.linspace(0.0001, 0.1, 200)},
    "k_L_O2": {"label": "O₂ Mass Transfer Coefficient (1/s)", "range": np.linspace(0.0001, 0.1, 200)},
    "C_atm": {"label": "Atmospheric CH₄ (ppm)", "range": np.linspace(0.1, 10.0, 200)},
    "O2_atm": {"label": "Atmospheric O₂ (%)", "range": np.linspace(1.0, 25.0, 200)},
}

selected_param = st.selectbox(
    "Select Parameter to Sweep",
    list(param_options.keys()),
    format_func=lambda k: param_options[k]["label"]
)

if st.button("Run Sensitivity Analysis"):
    # Single-parameter sweep (line plot)
    info = param_options[selected_param]
    vals = info["range"]
    line_results = []
    for v in vals:
        local = dict(T=T, expression_percent=expression_percent, Vmax_ref=Vmax_ref,
                     Km_ref=Km_ref, Pi=Pi, g_s=g_s, k_L_CH4=k_L_CH4, k_L_O2=k_L_O2,
                     C_atm=C_atm, O2_atm=O2_atm)
        local[selected_param] = v
        O2_init_local = H_0_O2 * np.exp(-0.02 * (local["T"] - 25.0)) * (1.0 - 0.01 * local["Pi"]) * (local["O2_atm"] / 100.0)
        C0_local = [0.0001, 0.0001, O2_init_local]
        sol_local = solve_ivp(
            fun=lambda t, C: methane_oxidation(
                C, t, local["C_atm"], local["O2_atm"], local["g_s"],
                local["Vmax_ref"], local["Km_ref"], local["Pi"], local["T"],
                local["k_L_CH4"], local["k_L_O2"], photosynthesis_on, local["expression_percent"]
            ),
            t_span=(time[0], time[-1]),
            y0=C0_local, t_eval=time, method="LSODA", rtol=1e-6, atol=1e-9
        ).y.T
        C_cyt_f = sol_local[-1, 0]
        O2_cyt_f = sol_local[-1, 2]
        V_MMO_f_loc = compute_v_mmo(local["Vmax_ref"], local["expression_percent"], local["T"],
                                    local["Pi"], local["Km_ref"], C_cyt_f, O2_cyt_f)
        line_results.append((v, V_MMO_f_loc))

    df_line = pd.DataFrame(line_results, columns=[info["label"], "Final CH₄ Oxidation Rate (mmol/L/s)"])
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_line[info["label"]],
                                  y=df_line["Final CH₄ Oxidation Rate (mmol/L/s)"],
                                  mode="lines+markers"))
    fig_line.update_layout(
        title=f"Sensitivity: {info['label']} vs. Final CH₄ Oxidation Rate",
        xaxis_title=info["label"],
        yaxis_title="mmol/L/s"
    )
    st.plotly_chart(fig_line)

    # CSV download
    st.download_button(
        "Download CSV",
        df_line.to_csv(index=False).encode("utf-8"),
        "sensitivity_analysis.csv",
        "text/csv"
    )

    # Heatmap across all parameters
    all_results = []
    for param, pinfo in param_options.items():
        local_vals = []
        for v in pinfo["range"]:
            local = dict(T=T, expression_percent=expression_percent, Vmax_ref=Vmax_ref,
                         Km_ref=Km_ref, Pi=Pi, g_s=g_s, k_L_CH4=k_L_CH4, k_L_O2=k_L_O2,
                         C_atm=C_atm, O2_atm=O2_atm)
            local[param] = v
            O2_init_local = H_0_O2 * np.exp(-0.02 * (local["T"] - 25.0)) * (1.0 - 0.01 * local["Pi"]) * (local["O2_atm"] / 100.0)
            C0_local = [0.0001, 0.0001, O2_init_local]
            sol_local = solve_ivp(
                fun=lambda t, C: methane_oxidation(
                    C, t, local["C_atm"], local["O2_atm"], local["g_s"],
                    local["Vmax_ref"], local["Km_ref"], local["Pi"], local["T"],
                    local["k_L_CH4"], local["k_L_O2"], photosynthesis_on, local["expression_percent"]
                ),
                t_span=(time[0], time[-1]),
                y0=C0_local, t_eval=time, method="LSODA", rtol=1e-6, atol=1e-9
            ).y.T
            C_cyt_f = sol_local[-1, 0]
            O2_cyt_f = sol_local[-1, 2]
            V_MMO_f_loc = compute_v_mmo(local["Vmax_ref"], local["expression_percent"], local["T"],
                                        local["Pi"], local["Km_ref"], C_cyt_f, O2_cyt_f)
            local_vals.append(V_MMO_f_loc)
        df_param = pd.DataFrame({"value": pinfo["range"], "rate": local_vals})
        rmin, rmax = df_param["rate"].min(), df_param["rate"].max()
        df_param["rate_norm"] = 0.0 if rmax == rmin else (df_param["rate"] - rmin) / (rmax - rmin)
        all_results.append(df_param)

    # Heatmap matrix
    y_labels = [param_options[k]["label"] for k in param_options.keys()]
    heatmap_matrix = np.vstack([df_param["rate_norm"].to_numpy() for df_param in all_results])
    x_vals = np.linspace(0, 100, heatmap_matrix.shape[1])
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_matrix,
        x=x_vals,
        y=y_labels,
        colorscale="Plasma",
        colorbar=dict(title="Normalized Rate"),
        zsmooth=False
    ))
    fig_heatmap.update_layout(
        title="Sensitivity Heatmap Across Parameters",
        xaxis_title="Parameter Sweep (Percentile)",
        yaxis_title="Parameter",
        xaxis=dict(tickmode="array", tickvals=[x_vals[0], x_vals[-1]], ticktext=["0%", "100%"])
    )
    st.plotly_chart(fig_heatmap)

# Footer
st.markdown("***Mikaelyan A. and Hornstein E.D., in prep.***")
