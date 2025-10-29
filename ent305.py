import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Ammonia–Temperature Comparative Dashboard", layout="wide")
st.title("🧪 Comparative Ammonia–Temperature Dashboard")

# --- Multi-file upload ---
uploaded_files = st.file_uploader(
    "Upload one or more CSV files", type=["csv"], accept_multiple_files=True
)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = pd.read_csv(file)
        # Normalize headers
        df.columns = [
            c.strip()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("°C", "C")
            for c in df.columns
        ]

        # Ensure expected columns exist
        expected = ["Ammonia_ppm", "Thermal_min_C", "Thermal_mean_C", "Thermal_max_C"]
        if not all(col in df.columns for col in expected):
            st.warning(f"⚠️ {file.name} missing expected columns.")
            continue

        # Convert and sort
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
    st.subheader("Data Preview")
    st.dataframe(all_data.head())

    # --- Correlation summary ---
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

    # --- Plot 1: Time-series comparison ---
    st.markdown("### 📈 Time Series: Ammonia vs Thermal Mean")
    fig = go.Figure()
    palette = px.colors.qualitative.Bold
    for i, (src, df) in enumerate(all_data.groupby("source")):
        color = palette[i % len(palette)]
        fig.add_trace(
            go.Scatter(
                x=df["Date/Time"],
                y=df["Ammonia_ppm"],
                mode="lines",
                name=f"{src} – Ammonia",
                line=dict(color=color, width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["Date/Time"],
                y=df["Thermal_mean_C"],
                mode="lines",
                name=f"{src} – Thermal mean",
                line=dict(color=color, width=1, dash="dot"),
            )
        )
    fig.update_layout(yaxis_title="Value", legend_title_text=None)
    st.plotly_chart(fig, use_container_width=True)

    # --- Plot 2: Thermal envelope + ammonia ---
    st.markdown("### 🌡️ Thermal Envelope vs Ammonia Flux")
    fig2 = go.Figure()
    for i, (src, df) in enumerate(all_data.groupby("source")):
        base_color = palette[i % len(palette)]
        # convert named color to rgba with opacity
        rgba = f"rgba({i*40 % 255}, {(i*90) % 255}, {(i*160) % 255}, 0.3)"
        fig2.add_trace(
            go.Scatter(
                x=df["Date/Time"],
                y=df["Thermal_range"],
                fill="tozeroy",
                mode="none",
                name=f"{src} – Thermal range",
                fillcolor=rgba,
            )
        )
        fig2.add_trace(
            go.Scatter(
                x=df["Date/Time"],
                y=df["Ammonia_ppm"] * 10,
                mode="lines",
                name=f"{src} – Ammonia (×10)",
                line=dict(color=base_color, width=2),
            )
        )
    fig2.update_layout(yaxis_title="Thermal Range (°C)", legend_title_text=None)
    st.plotly_chart(fig2, use_container_width=True)

    # --- Plot 3: Scatter comparison ---
    st.markdown("### 🔥 Scatter: Thermal Mean vs Ammonia (Chronological Gradient)")
    fig3 = px.scatter(
        all_data,
        x="Thermal_mean_C",
        y="Ammonia_ppm",
        color="Date/Time",
        facet_col="source",
        color_continuous_scale="Turbo",
        trendline="lowess",
    )
    fig3.update_layout(showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    # --- Interpretation ---
    st.markdown(
        """
    **Interpretation**
    - Compare how ammonia responds to heat buildup across conditions.
    - Observe if one system reaches thermal equilibrium faster (faster decay or lower moisture).
    - Shaded envelopes mark internal microbial heating phases.
    """
    )

else:
    st.info(
        "Upload one or more CSVs with columns for Date/Time, Ammonia (ppm), and Thermal min/mean/max (°C)."
    )
