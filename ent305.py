import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------
# Streamlit setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Ammonia–Temperature Decomposition Dashboard", layout="wide")
st.title("🪰 Comparative Ammonia–Temperature Dashboard")

# ---------------------------------------------------------------
# File upload
# ---------------------------------------------------------------
uploaded_files = st.file_uploader("Upload one or more CSV files", type=["csv"], accept_multiple_files=True)

# Sidebar controls
with st.sidebar:
    st.header("Event Markers (Days from Egg Deposition)")
    derm_added_day = st.number_input("Dermestids added", value=4.0, step=0.5)
    derm_L2_day = st.number_input("Dermestid L2–L3 observed", value=12.0, step=0.5)
    eclosion_day = st.number_input("Fly eclosion", value=14.0, step=0.5)
    show_trendline = st.checkbox("Show LOESS trendline (requires statsmodels)", value=False)

# ---------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------
if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = pd.read_csv(file)
        df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").replace("°C", "C")
                      for c in df.columns]

        expected = ["Date/Time", "Ammonia_ppm", "Thermal_min_C", "Thermal_mean_C", "Thermal_max_C"]
        if not all(col in df.columns for col in expected):
            st.warning(f"⚠️ {file.name} missing expected columns.")
            continue

        df["Date/Time"] = pd.to_datetime(df["Date/Time"], errors="coerce")
        df = df.sort_values("Date/Time")
        df["source"] = file.name
        df["Thermal_range"] = (
            pd.to_numeric(df["Thermal_max_C"], errors="coerce")
            - pd.to_numeric(df["Thermal_min_C"], errors="coerce")
        )
        dfs.append(df)

    if not dfs:
        st.error("No valid datasets found.")
        st.stop()

    all_data = pd.concat(dfs, ignore_index=True)

    # -----------------------------------------------------------
    # Derived metrics: elapsed days, rolling means, slopes
    # -----------------------------------------------------------
    def add_rolls(g):
        g = g.sort_values("Date/Time").copy()
        t0 = g["Date/Time"].min()
        g["Elapsed_days"] = (g["Date/Time"] - t0).dt.total_seconds() / 86400.0
        g["NH3_roll12"] = g["Ammonia_ppm"].rolling(12, min_periods=6).mean()
        g["NH3_slope12"] = g["NH3_roll12"].diff() / 0.5  # per hour (30-min interval)
        g["Therm_roll12"] = g["Thermal_mean_C"].rolling(12, min_periods=6).mean()
        g["dThermal"] = g["Thermal_max_C"] - g["Thermal_min_C"]
        g["dThermal_roll12"] = g["dThermal"].rolling(12, min_periods=6).mean()
        return g

    all_data = all_data.groupby("source", group_keys=False).apply(add_rolls)

    # -----------------------------------------------------------
    # Event annotations
    # -----------------------------------------------------------
    event_lines = [
        {"day": 0.0, "label": "Eggs placed"},
        {"day": derm_added_day, "label": "Dermestids added"},
        {"day": derm_L2_day, "label": "Dermestid L2–L3"},
        {"day": eclosion_day, "label": "L. cuprina eclosion"},
        # Lucilia cuprina development
        {"day": 1.0, "label": "L1 hatch"},
        {"day": 3.5, "label": "L3 feeding peak"},
        {"day": 8.0, "label": "Pupation begins"},
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
    # Plot 1: Time-series (Ammonia + Thermal Mean)
    # -----------------------------------------------------------
    st.markdown("### 📈 Time Series: Ammonia vs Thermal Mean")
    fig1 = go.Figure()
    palette = px.colors.qualitative.Bold
    for i, (src, df) in enumerate(all_data.groupby("source")):
        color = palette[i % len(palette)]
        fig1.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Ammonia_ppm"],
            mode="lines", name=f"{src} – Ammonia",
            line=dict(color=color, width=2)))
        fig1.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Thermal_mean_C"],
            mode="lines", name=f"{src} – Thermal mean",
            line=dict(color=color, width=1, dash="dot")))

    for ev in event_lines:
        fig1.add_vline(x=ev["day"], line_width=1, line_dash="dot",
                       line_color="black", annotation_text=ev["label"],
                       annotation_position="top left")

    fig1.update_layout(xaxis_title="Elapsed Days", yaxis_title="Value", legend_title_text=None)
    st.plotly_chart(fig1, use_container_width=True)

    # -----------------------------------------------------------
    # Plot 2: Thermal envelope vs Ammonia
    # -----------------------------------------------------------
    st.markdown("### 🌡️ Thermal Envelope vs Ammonia Flux")
    fig2 = go.Figure()
    for i, (src, df) in enumerate(all_data.groupby("source")):
        base_color = palette[i % len(palette)]
        rgba = f"rgba({(i*50)%255}, {(i*100)%255}, {(i*150)%255}, 0.3)"
        fig2.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Thermal_range"],
            fill="tozeroy", mode="none",
            name=f"{src} – Thermal range",
            fillcolor=rgba))
        fig2.add_trace(go.Scatter(
            x=df["Elapsed_days"], y=df["Ammonia_ppm"] * 10,
            mode="lines", name=f"{src} – Ammonia (×10)",
            line=dict(color=base_color, width=2)))

    for ev in event_lines:
        fig2.add_vline(x=ev["day"], line_width=1, line_dash="dot",
                       line_color="black", annotation_text=ev["label"],
                       annotation_position="top left")

    fig2.update_layout(xaxis_title="Elapsed Days", yaxis_title="Thermal Range (°C)", legend_title_text=None)
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

    # -----------------------------------------------------------
    # Interpretation
    # -----------------------------------------------------------
    st.markdown("""
    **Interpretation Guide**

    - **Day 0–1:** microbial ignition — rising thermal mean, narrowing ΔThermal, ammonia begins to climb.  
    - **Day 1–3:** peak decay activity — ammonia spike + narrow ΔThermal = bloat/active phase.  
    - **Day 4:** *Dermestids introduced* → compare thermal and ammonia responses between chambers.  
    - **Day 5–7:** plateau; high larval biomass maintains internal heat.  
    - **Day 7–9:** *Pupation begins* — ammonia and thermal signals fall toward ambient.  
    - **Day 12:** *Dermestid L2–L3 larvae observed* — possible secondary flux.  
    - **Day 14:** *Fly eclosion* — system stabilized near ambient.
    """)

else:
    st.info("Upload one or more CSVs containing Date/Time, Ammonia (ppm), and Thermal min/mean/max (°C).")
