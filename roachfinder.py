import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Title of the app
st.title("Cockroach Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes cockroach-related violations from Wake County food inspection data on a map.
Data is sourced from local files. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: ~18-20% of Raleigh metro households reported cockroach sightings in recent surveys.
""")

# Initialize session state
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None

# Data upload section
st.subheader("Upload Data")
data_upload = st.file_uploader("Upload Food Inspections CSV/JSON", type=["csv", "json"])

if data_upload and st.session_state.merged_df is None:
    try:
        # Load the full dataset
        if data_upload.name.endswith('.json'):
            df = pd.json_normalize(json.load(data_upload))
        else:
            df = pd.read_csv(data_upload)
        st.write("Full Dataset columns:", df.columns.tolist())

        # Check for required columns and map them
        required_cols = {'HSISID': 'HSISID', 'DATE_': 'INSPECTDATE', 'DESCRIPTION': 'SHORTDESC', 'TYPE': 'COMMENTS'}
        missing_cols = [col for col in required_cols.values() if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {missing_cols}. Please ensure the dataset includes at least HSISID, DATE_, DESCRIPTION, and TYPE.")
            st.markdown("**Note**: The uploaded file lacks restaurant location data (e.g., NAME, ADDRESS1, X, Y). You may need to download a separate dataset or adjust the file from https://data-wake.opendata.arcgis.com/datasets/food-inspections to include these fields.")
            st.stop()

        # Rename columns to match expected format
        df_renamed = df.rename(columns=required_cols)
        df_renamed.columns = [f'attributes.{col}' if col != 'HSISID' else 'attributes.HSISID' for col in df_renamed.columns]
        st.write("Renamed DataFrame columns:", df_renamed.columns.tolist())

        # Since restaurant data (NAME, X, Y) is missing, use available data as-is
        st.session_state.merged_df = df_renamed.copy()

        # Filter for cockroach-related violations
        keywords = ['cockroach', 'roaches', 'pest', 'insect']
        mask = st.session_state.merged_df['attributes.COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
               st.session_state.merged_df['attributes.SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
        st.session_state.merged_df = st.session_state.merged_df[mask].copy()

        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded file: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Display summary
st.subheader("Summary")
if merged_df is not None and not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    # Use available columns for display
    st.dataframe(merged_df[['attributes.HSISID', 'attributes.INSPECTDATE', 'attributes.SHORTDESC', 'attributes.COMMENTS']].head(10))
else:
    st.warning("No cockroach-related violations found or data not uploaded yet. Please upload the Food Inspections file and ensure it includes required fields.")

# Create map (disabled due to missing coordinates)
if merged_df is not None and not merged_df.empty:
    if 'attributes.X' in merged_df.columns and 'attributes.Y' in merged_df.columns:
        # Drop rows with invalid coordinates
        merged_df = merged_df.dropna(subset=['attributes.X', 'attributes.Y'])
        merged_df = merged_df[(merged_df['attributes.X'] != 0) & (merged_df['attributes.Y'] != 0)]

        # Initialize map centered on Raleigh
        m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

        # Add markers
        for idx, row in merged_df.iterrows():
            popup_text = f"<b>HSISID: {row['attributes.HSISID']}</b><br>Date: {row['attributes.INSPECTDATE']}<br>Violation: {row['attributes.SHORTDESC']}<br>Comments: {row['attributes.COMMENTS']}"
            try:
                folium.Marker(
                    location=[row['attributes.Y'], row['attributes.X']],  # Y=latitude, X=longitude
                    popup=popup_text,
                    tooltip=row['attributes.HSISID']
                ).add_to(m)
            except Exception as e:
                st.warning(f"Skipping invalid marker for HSISID {row['attributes.HSISID']}: {str(e)}")

        st.subheader("Map of Infestations")
        folium_static(m)
    else:
        st.warning("Map not available. The uploaded file lacks location data (X, Y coordinates). Please download a dataset with restaurant locations from https://data-wake.opendata.arcgis.com/datasets/food-inspections or a related source.")
else:
    st.write("No data available for mapping. Please upload the Food Inspections file to proceed.")

# Date filter
st.subheader("Filters")
if merged_df is not None and 'attributes.INSPECTDATE' in merged_df.columns:
    try:
        merged_df['attributes.INSPECTDATE'] = pd.to_datetime(merged_df['attributes.INSPECTDATE'], errors='coerce')
        min_date = merged_df['attributes.INSPECTDATE'].min().date()
        max_date = merged_df['attributes.INSPECTDATE'].max().date()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input("Select date range", [min_date, max_date])
            filtered_df = merged_df[(merged_df['attributes.INSPECTDATE'].dt.date >= date_range[0]) & 
                                  (merged_df['attributes.INSPECTDATE'].dt.date <= date_range[1])]
            st.write(f"Filtered violations: {len(filtered_df)}")
            if not filtered_df.empty and 'attributes.X' in filtered_df.columns and 'attributes.Y' in filtered_df.columns:
                m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)
                for idx, row in filtered_df.iterrows():
                    popup_text = f"<b>HSISID: {row['attributes.HSISID']}</b><br>Date: {row['attributes.INSPECTDATE']}<br>Violation: {row['attributes.SHORTDESC']}<br>Comments: {row['attributes.COMMENTS']}"
                    try:
                        folium.Marker(
                            location=[row['attributes.Y'], row['attributes.X']],
                            popup=popup_text,
                            tooltip=row['attributes.HSISID']
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Skipping invalid marker for HSISID {row['attributes.HSISID']}: {str(e)}")
                st.subheader("Filtered Map")
                folium_static(m)
            else:
                st.write("Filtered map not available due to missing location data.")
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available or no data uploaded.")
