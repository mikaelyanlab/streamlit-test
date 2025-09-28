# Heatmap preparation
all_results = []
for param, info in param_options.items():
    local_results = []
    for val in info["range"]:
        local_T = T if param != "T" else val
        local_expression_percent = expression_percent if param != "expression_percent" else val
        local_Vmax_ref = Vmax_ref if param != "Vmax_ref" else val
        local_Km_ref = Km_ref if param != "Km_ref" else val
        local_Pi = Pi if param != "Pi" else val
        local_g_s = g_s if param != "g_s" else val
        local_k_L_CH4 = k_L_CH4 if param != "k_L_CH4" else val
        local_k_L_O2 = k_L_O2 if param != "k_L_O2" else val
        local_C_atm = C_atm if param != "C_atm" else val
        local_O2_atm = O2_atm if param != "O2_atm" else val
        local_O2_init = H_0_O2 * np.exp(-0.02 * (local_T - 25)) * (1 - 0.01 * local_Pi) * (local_O2_atm / 100.0)
        local_C0 = [0.0001, 0.0001, local_O2_init]
        sol_local = solve_ivp(
            fun=lambda t, C: methane_oxidation(
                C, t, local_C_atm, local_O2_atm, local_g_s, local_Vmax_ref, local_Km_ref,
                local_Pi, local_T, local_k_L_CH4, local_k_L_O2, photosynthesis_on, local_expression_percent
            ),
            t_span=(time[0], time[-1]),
            y0=local_C0,
            t_eval=time,
            method='LSODA',
            rtol=1e-6,
            atol=1e-9
        ).y.T
        local_C_cyt_final = sol_local[-1, 0]
        local_Km_T = local_Km_ref * (1 + 0.02 * (local_T - 25))
        local_Vmax_T = local_Vmax_ref * (local_expression_percent / 100) * np.exp(-E_a / R * (1/(local_T + 273.15) - 1/T_ref))
        local_Vmax_osm = local_Vmax_T * np.exp(-0.02 * (local_Pi / 100))
        local_O2_cyt_final = sol_local[-1, 2]
        Km_O2_local = 0.001
        local_V_MMO_final = local_Vmax_osm * (local_C_cyt_final / (local_Km_T + local_C_cyt_final)) * \
                            (local_O2_cyt_final / (Km_O2_local + local_O2_cyt_final))
        local_results.append(local_V_MMO_final)
    df_param = pd.DataFrame({param: info["range"], "rate": local_results})
    df_param['rate_norm'] = (df_param['rate'] - df_param['rate'].min()) / \
                            (df_param['rate'].max() - df_param['rate'].min())
    all_results.append(df_param)
# Create heatmap matrix
heatmap_data = pd.concat(all_results, axis=1)
heatmap_matrix = np.array([df['rate_norm'].values for df in all_results]).T
# Ensure 20 points for x-axis
if heatmap_matrix.shape[1] != 20:
    heatmap_matrix = heatmap_matrix[:, :20]  # Truncate or pad to 20 if needed
# Heatmap plot
fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_matrix,
    x=[f"{i*5}%" for i in range(20)],  # 0% to 95% in 5% steps
    y=list(param_options.keys())[::-1],
    colorscale='Plasma',
    colorbar=dict(title="Normalized Rate")
))
fig_heatmap.update_layout(
    title="Sensitivity Heatmap Across Parameters",
    xaxis_title="Parameter Sweep (Percentile)",
    yaxis_title="Parameter",
    xaxis=dict(
        tickmode='array',
        tickvals=[i * 5 for i in range(0, 20, 5)],  # 0, 5, 10, ..., 95
        ticktext=["0%", "25%", "50%", "75%", "100%"]  # Map to 0-100% percentiles
    )
)
st.plotly_chart(fig_heatmap)
