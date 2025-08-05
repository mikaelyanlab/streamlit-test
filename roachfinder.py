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

        # Extract unique restaurant data (deduplicated by HSISID)
        restaurant_cols = ['HSISID', 'NAME', 'ADDRESS1', 'CITY', 'POSTALCODE', 'X', 'Y']
        restaurants_df = df[restaurant_cols].drop_duplicates(subset=['HSISID'])
        restaurants_df.columns = [f'attributes.{col}' for col in restaurant_cols]
        st.write("Restaurants DataFrame columns:", restaurants_df.columns.tolist())

        # Keep all violation records
        violation_cols = [col for col in df.columns if col not in restaurant_cols or col == 'HSISID']
        violations_df = df[violation_cols]
        violations_df.columns = [f'attributes.{col}' if col != 'HSISID' else 'attributes.HSISID' for col in violation_cols]
        st.write("Violations DataFrame columns:", violations_df.columns.tolist())

        # Merge data on HSISID
        merged_df = violations_df.merge(restaurants_df, on='attributes.HSISID', how='left')
        st.write("Merged DataFrame columns:", merged_df.columns.tolist())

        # Filter for cockroach-related violations
        keywords = ['cockroach', 'roaches', 'pest', 'insect']
        mask = merged_df['attributes.COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
               merged_df['attributes.SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
        st.session_state.merged_df = merged_df[mask].copy()

        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded file: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Display summary
st.subheader("Summary")
if merged_df is not None and not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    st.dataframe(merged_df[['attributes.NAME', 'attributes.ADDRESS1', 'attributes.CITY',
                           'attributes.INSPECTDATE', 'attributes.SHORTDESC', 'attributes.COMMENTS']].head(10))
else:
    st.warning("No cockroach-related violations found or data not uploaded yet. Please upload the Food Inspections file.")

# Create map
if merged_df is not None and not merged_df.empty:
    # Drop rows with invalid coordinates
    merged_df = merged_df.dropna(subset=['attributes.X', 'attributes.Y'])
    merged_df = merged_df[(merged_df['attributes.X'] != 0) & (merged_df['attributes.Y'] != 0)]

    # Initialize map centered on Raleigh
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['attributes.NAME']}</b><br>Address: {row['attributes.ADDRESS1']}, {row['attributes.CITY']}<br>Date: {row['attributes.INSPECTDATE']}<br>Violation: {row['attributes.SHORTDESC']}<br>Comments: {row['attributes.COMMENTS']}"
        try:
            folium.Marker(
                location=[row['attributes.Y'], row['attributes.X']],  # Y=latitude, X=longitude
                popup=popup_text,
                tooltip=row['attributes.NAME']
            ).add_to(m)
        except Exception as e:
            st.warning(f"Skipping invalid marker for {row['attributes.NAME']}: {str(e)}")

    st.subheader("Map of Infestations")
    folium_static(m)
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
            if not filtered_df.empty:
                m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)
                for idx, row in filtered_df.iterrows():
                    popup_text = f"<b>{row['attributes.NAME']}</b><br>Address: {row['attributes.ADDRESS1']}, {row['attributes.CITY']}<br>Date: {row['attributes.INSPECTDATE']}<br>Violation: {row['attributes.SHORTDESC']}<br>Comments: {row['attributes.COMMENTS']}"
                    try:
                        folium.Marker(
                            location=[row['attributes.Y'], row['attributes.X']],
                            popup=popup_text,
                            tooltip=row['attributes.NAME']
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Skipping invalid marker for {row['attributes.NAME']}: {str(e)}")
                st.subheader("Filtered Map")
                folium_static(m)
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available or no data uploaded.")
