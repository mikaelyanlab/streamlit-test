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
restaurants_upload = st.file_uploader("Upload Restaurants CSV/JSON (from https://opendata.arcgis.com/datasets/1b9a4c2f8bc74a1e8e0e8dd46a4b0bb6_0.csv)", type=["csv", "json"])
violations_upload = st.file_uploader("Upload Violations (Food Inspections) CSV/JSON (from https://data-wake.opendata.arcgis.com/datasets/food-inspections)", type=["csv", "json"])

if restaurants_upload and violations_upload and st.session_state.merged_df is None:
    try:
        # Load restaurants data
        if restaurants_upload.name.endswith('.json'):
            restaurants_df = pd.json_normalize(json.load(restaurants_upload))
        else:
            restaurants_df = pd.read_csv(restaurants_upload)
        st.write("Restaurants DataFrame columns:", restaurants_df.columns.tolist())

        # Load violations data
        if violations_upload.name.endswith('.json'):
            violations_df = pd.json_normalize(json.load(violations_upload))
        else:
            violations_df = pd.read_csv(violations_upload)
        st.write("Violations DataFrame columns:", violations_df.columns.tolist())

        # Merge data on HSISID
        merged_df = violations_df.merge(restaurants_df[['HSISID', 'NAME', 'ADDRESS1', 'CITY', 'POSTALCODE', 'X', 'Y']], on='HSISID', how='left')
        st.write("Merged DataFrame columns:", merged_df.columns.tolist())

        # Filter for cockroach-related violations
        keywords = ['cockroach', 'roaches', 'pest', 'insect']
        mask = merged_df['DESCRIPTION'].str.contains('|'.join(keywords), case=False, na=False) | \
               merged_df['TYPE'].str.contains('|'.join(keywords), case=False, na=False)
        st.session_state.merged_df = merged_df[mask].copy()

        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded files: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Display summary
st.subheader("Summary")
if merged_df is not None and not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    st.dataframe(merged_df[['NAME', 'ADDRESS1', 'CITY', 'DATE_', 'DESCRIPTION', 'TYPE']].head(10))
else:
    st.warning("No cockroach-related violations found or data not uploaded yet. Please upload the files to proceed.")

# Create map
if merged_df is not None and not merged_df.empty:
    # Drop rows with invalid coordinates
    merged_df = merged_df.dropna(subset=['X', 'Y'])
    merged_df = merged_df[(merged_df['X'] != 0) & (merged_df['Y'] != 0)]

    # Initialize map centered on Raleigh
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['DATE_']}<br>Violation: {row['DESCRIPTION']}<br>Comments: {row['TYPE']}"
        try:
            folium.Marker(
                location=[row['Y'], row['X']],  # Y=latitude, X=longitude
                popup=popup_text,
                tooltip=row['NAME']
            ).add_to(m)
        except Exception as e:
            st.warning(f"Skipping invalid marker for {row['NAME']}: {str(e)}")

    st.subheader("Map of Infestations")
    folium_static(m)
else:
    st.write("No data available for mapping. Please upload the files to proceed.")

# Date filter
st.subheader("Filters")
if merged_df is not None and 'DATE_' in merged_df.columns:
    try:
        merged_df['DATE_'] = pd.to_datetime(merged_df['DATE_'], errors='coerce')
        min_date = merged_df['DATE_'].min().date()
        max_date = merged_df['DATE_'].max().date()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input("Select date range", [min_date, max_date])
            filtered_df = merged_df[(merged_df['DATE_'].dt.date >= date_range[0]) & 
                                  (merged_df['DATE_'].dt.date <= date_range[1])]
            st.write(f"Filtered violations: {len(filtered_df)}")
            if not filtered_df.empty:
                m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)
                for idx, row in filtered_df.iterrows():
                    popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['DATE_']}<br>Violation: {row['DESCRIPTION']}<br>Comments: {row['TYPE']}"
                    try:
                        folium.Marker(
                            location=[row['Y'], row['X']],
                            popup=popup_text,
                            tooltip=row['NAME']
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Skipping invalid marker for {row['NAME']}: {str(e)}")
                st.subheader("Filtered Map")
                folium_static(m)
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available or no data uploaded.")
