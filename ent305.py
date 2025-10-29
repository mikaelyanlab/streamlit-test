import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------
# Streamlit setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Ammonia–Temperature Decomposition Dashboard", layout="wide")
st.title("🪰 Comparative Ammonia–Temperature Dashboard")

uploaded_files = st.file_uploader("Upload one or more CSV files", type=["csv"], accept_multiple_files=True)

# Sidebar controls ------------------------------------------------
with st.sidebar:
    st.header("Event Markers (Days from Egg Deposition)")
    eggs_day = st.number_input("Eggs placed", value=0.0, step=0.5)
    l1_day = st.number_input("L1 hatch", value=1.0, step=0.5)
    l3_day = st.number_input("L3 feeding peak", value=3.5, step=0.5)
    derm_added_day = st.number_input("Dermestids added", value=4.0, step=0.5)
    wandering_day = st.number_input("Wandering stage", value=4.6, step=0.5)
    pupation_day = st.number_input("Pupation begins", value=8.0, step=0.5)
    derm_larvae_day = st.number_input("Dermestid L2–L3", value=12.0, step=0.5)
    eclosion_day = st.number_input("Fly eclosion", value=14.0, step=0.5)
    show_trendline = st.checkbox("Show LOESS trendline (requires statsmodels)", value=False)
    st.markdown("---")
    st.markdown("**Thermal range** = Thermal_max – Thermal_min (°C). "
                "Small range = heat-buffered system; large range = ambient coupling.")

# ---------------------------------------------------------------
# Data processing ------------------------------------------------
if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = pd.read_csv(file)
        df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").replace("°C", "C")
                      for c in df.columns]

        expected = ["Date/Time", "Ammonia_ppm", "Thermal_min_C", "Thermal_mean_C", "Thermal_max_C"]
        if not all(col in df.columns for col in expected):
            st.warning(f"⚠️ {file.name} missing expected columns. Found: {list(df.columns)}")
            continue

        df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
        for col in ["Thermal_min_C", "Thermal_mean_C", "Thermal_max_C", "Ammonia_ppm"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["Thermal_range"] = df["Thermal_max_C"] - df["Thermal_min_C"]
        df.loc[df["Thermal_range"] > 15, "Thermal_range"] = np.nan

        df = df.sort_values("Date/Time").copy()
        df["source"] = file.name
        dfs.append(df)

    if not dfs:
        st.error("No valid datasets found.")
        st.stop()

    all_data = pd.concat(dfs, ignore_index=True)

    # Derived metrics --------------------------------------------
    def add_rolls(g):
        g = g.sort_values("Date/Time").copy()
        t0 = g["Date/Time"].min()
        g["Elapsed_days"] = (g["Date/Time"] - t0).dt.total_seconds() / 86400.0

        window = 12  # ~6 hours for 30 min intervals
        g["NH3_roll12"] = g["Ammonia_ppm"].rolling(window, min_periods=6).mean()
        g["NH3_slope12"] = g["NH3_roll12"].diff() / 0.5  # per hour
        g["Therm_roll12"] = g["Thermal_mean_C"].rolling(window, min_periods=6).mean()
        g["dThermal"] = g["Thermal_max_C"] - g["Thermal_min_C"]
        g["dThermal_roll12"] = g["dThermal"].rolling(window, min_periods=6).mean()
        return g

    all_data = all_data.groupby("source", group_keys=False).apply(add_rolls)

    # Event annotations ------------------------------------------
    event_lines = [
        {"day": eggs_day, "label": "Eggs placed"},
        {"day": l1_day, "label": "L1 hatch"},
        {"day": l3_day, "label": "L3 feeding peak"},
        {"day": derm_added_day, "label": "Dermestids added"},
        {"day": wandering_day, "label": "Wandering stage"},
        {"day": pupation_day, "label": "Pupation begins"},
        {"day": derm_larvae_day, "label": "Dermestid L2–L3"},
        {"day": eclosion_day, "label": "L. cuprina eclosion"},
    ]

    # -----------------------------------------------------------
    # Data preview
    # -----------------------------------------------------------
    st.subheader("Data Preview")
    st.dataframe(all_data.head())

    # -----------------------------------------------------------
    # Correlation summary
    # -----------------------------------------------------------
    st.markdown("### 🔗 Correlation Comparison (Ammonia vs Thermal Variables)")
    corr_list = []
    for src, df in all_data.groupby("source"):
        vals = {
            "Source": src,
            "Thermal min": df["Ammonia_ppm"].corr(df["Thermal_min_C"]),
            "Thermal mean": df["Ammonia_ppm"].corr(df["Thermal_mean_C"]),
            "Thermal max": df["Ammonia_ppm"].corr(df["Thermal_max_C"]),
        }
        corr_list.append(vals)
    corr_df = pd.DataFrame(corr_list)
    st.dataframe(corr_df.style.background_gradient(cmap="RdYlGn", axis=None))

    # -----------------------------------------------------------
    # Plot 1: Dual-axis (Ammonia vs Thermal Mean)
    # -----------------------------------------------------------
    st.markdown("### 📊 Dual-Axis Time Series: Ammonia (ppm) and Thermal Mean (°C)")
    fig_dual = go.Figure()
    palette = px.colors.qualitative.Bold

    for i, (src, df) in enumerate(all_data.groupby("source")):
        color = palette[i % len(palette)]
        fig_dual.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Thermal_mean_C"],
            mode="lines", name=f"{src} – Thermal mean (°C)",
            line=dict(color=color, dash="dot"), yaxis="y1"))
        fig_dual.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Ammonia_ppm"],
            mode="lines", name=f"{src} – Ammonia (ppm)",
            line=dict(color=color, width=2), yaxis="y2"))

    for ev in event_lines:
        fig_dual.add_vline(x=ev["day"], line_width=1, line_dash="dot",
                           line_color="black", annotation_text=ev["label"],
                           annotation_position="top left")

    fig_dual.update_layout(
        xaxis=dict(title="Elapsed Days"),
        yaxis=dict(title="Thermal Mean (°C)", side="left", range=[20, 30]),
        yaxis2=dict(title="Ammonia (ppm)", side="right", overlaying="y", range=[0, 10]),
        legend_title_text=None,
        template="plotly_white"
    )
    st.plotly_chart(fig_dual, use_container_width=True)

    # -----------------------------------------------------------
    # Plot 2: Thermal Envelope vs Ammonia
    # -----------------------------------------------------------
    st.markdown("### 🌡️ Thermal Envelope vs Ammonia Flux")
    fig2 = go.Figure()
    for i, (src, df) in enumerate(all_data.groupby("source")):
        base_color = palette[i % len(palette)]
        rgba = f"rgba({(i*50)%255}, {(i*100)%255}, {(i*150)%255}, 0.3)"
        fig2.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Thermal_range"],
            fill="tozeroy", mode="none",
            name=f"{src} – Thermal range (°C)",
            fillcolor=rgba))
        fig2.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Ammonia_ppm"],
            mode="lines", name=f"{src} – Ammonia (ppm)",
            line=dict(color=base_color, width=2)))

    for ev in event_lines:
        fig2.add_vline(x=ev["day"], line_width=1, line_dash="dot",
                       line_color="black", annotation_text=ev["label"],
                       annotation_position="top left")

    fig2.update_layout(xaxis_title="Elapsed Days", yaxis_title="Thermal Range (°C)",
                       legend_title_text=None, template="plotly_white")
    fig2.update_yaxes(range=[0, 15])
    st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------------------------------------
    # Plot 3: Scatter (Thermal mean vs Ammonia)
    # -----------------------------------------------------------
    st.markdown("### 🔥 Scatter: Thermal Mean vs Ammonia (Chronological Gradient)")
    trend_arg = "lowess" if show_trendline else None
    fig3 = px.scatter(
        all_data, x="Thermal_mean_C", y="Ammonia_ppm",
        color="Elapsed_days", facet_col="source",
        color_continuous_scale="Turbo", trendline=trend_arg)
    fig3.update_layout(coloraxis_colorbar_title="Elapsed Days")
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("Upload one or more CSVs containing Date/Time, Ammonia (ppm), and Thermal min/mean/max (°C).")
