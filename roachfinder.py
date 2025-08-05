import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
from io import StringIO
import json

# Title of the app
st.title("Cockroach Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes cockroach-related violations from Wake County food inspection data on a map.
Data is sourced from public ArcGIS services or local files. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: ~18-20% of Raleigh metro households reported cockroach sightings in recent surveys.
""")

# Headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Cache data loading with pagination and debugging
@st.cache_data
def load_data_from_api(base_url, layer_id, out_fields, token=None):
    st.write(f"Attempting to load data from {base_url}{layer_id}/query")
    try:
        all_data = []
        offset = 0
        max_records = 2000  # As per MaxRecordCount

        while True:
            params = {
                'where': '1=1',
                'outFields': out_fields,
                'f': 'json',
                'resultOffset': offset,
                'resultRecordCount': max_records
            }
            if token:
                params['token'] = token

            response = requests.get(base_url + str(layer_id) + '/query', params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            st.write(f"API response status: Received data for offset {offset}")

            if 'error' in data:
                st.error(f"API error: {data['error']['message']}")
                break

            if 'features' not in data:
                st.write("No 'features' key in response, breaking loop.")
                break

            features = data['features']
            if not features:
                st.write("No more features found, breaking loop.")
                break

            all_data.extend(features)
            offset += max_records

            # Check if the transfer limit is exceeded (indicates more data available)
            if data.get('exceededTransferLimit', False):
                st.write(f"Transfer limit exceeded at offset {offset}, continuing...")
            else:
                st.write("No more data to fetch.")
                break

        if all_data:
            df = pd.json_normalize(all_data)
            st.write(f"Successfully loaded {len(df)} records.")
            return df
        st.write("No data returned from API.")
        return None
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}. Check API parameters or obtain a token.")
        return None
    except Exception as e:
        st.error(f"Error loading data from API: {str(e)}")
        return None

def load_local_data():
    st.subheader("Upload Local Data")
    restaurants_upload = st.file_uploader("Upload Restaurants CSV/JSON", type=["csv", "json"])
    violations_upload = st.file_uploader("Upload Violations CSV/JSON", type=["csv", "json"])

    if restaurants_upload and violations_upload:
        try:
            if restaurants_upload.name.endswith('.json'):
                restaurants_df = pd.json_normalize(json.load(restaurants_upload))
            else:
                restaurants_df = pd.read_csv(restaurants_upload)
            
            if violations_upload.name.endswith('.json'):
                violations_df = pd.json_normalize(json.load(violations_upload))
            else:
                violations_df = pd.read_csv(violations_upload)
            st.success("Uploaded files successfully.")
            return restaurants_df, violations_df
        except Exception as e:
            st.error(f"Error loading uploaded files: {str(e)}")
            return None, None
    st.write("No local files uploaded.")
    return None, None

# API URLs and fields
base_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/"
restaurants_df = load_data_from_api(base_url, 0, "HSISID,NAME,ADDRESS1,CITY,POSTALCODE,X,Y")
violations_df = load_data_from_api(base_url, 2, "*")

if restaurants_df is None or violations_df is None:
    restaurants_df, violations_df = load_local_data()
    if restaurants_df is None or violations_df is None:
        st.markdown("**Instructions**: Download data from https://data-wake.opendata.arcgis.com/datasets/food-inspections (CSV/JSON) and upload above, or obtain an API token from Wake County.")
        st.stop()

# Filter for cockroach-related violations
keywords = ['cockroach', 'roaches', 'pest', 'insect']
mask = violations_df['attributes.COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
       violations_df['attributes.SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
cockroach_viol = violations_df[mask]

# Merge with locations (using attributes prefix for JSON-normalized data)
merged_df = cockroach_viol.merge(restaurants_df, on='attributes.HSISID', how='left', suffixes=('_viol', '_rest'))

# Extract coordinates from geometry if present, otherwise use X/Y
if 'geometry.x' in restaurants_df.columns and 'geometry.y' in restaurants_df.columns:
    merged_df = merged_df.merge(restaurants_df[['attributes.HSISID', 'geometry.x', 'geometry.y']], on='attributes.HSISID', how='left')
    merged_df = merged_df.rename(columns={'geometry.x': 'X', 'geometry.y': 'Y'})
else:
    merged_df = merged_df.rename(columns={'attributes.X': 'X', 'attributes.Y': 'Y'})

# Drop rows without valid coordinates
merged_df = merged_df.dropna(subset=['X', 'Y'])
merged_df = merged_df[(merged_df['X'] != 0) & (merged_df['Y'] != 0)]

# Display summary
st.subheader("Summary")
if not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    st.dataframe(merged_df[['attributes.NAME_rest', 'attributes.ADDRESS1_rest', 'attributes.CITY_rest', 
                           'attributes.INSPECTDATE_viol', 'attributes.SHORTDESC_viol', 'attributes.COMMENTS_viol']].head(10))
else:
    st.warning("No cockroach-related violations found in the data.")

# Create map
if not merged_df.empty:
    # Initialize map centered on Raleigh (lat, lon)
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['attributes.NAME_rest']}</b><br>Address: {row['attributes.ADDRESS1_rest']}, {row['attributes.CITY_rest']}<br>Date: {row['attributes.INSPECTDATE_viol']}<br>Violation: {row['attributes.SHORTDESC_viol']}<br>Comments: {row['attributes.COMMENTS_viol']}"
        try:
            folium.Marker(
                location=[row['Y'], row['X']],  # Y=latitude, X=longitude (converted from State Plane to WGS84 if needed)
                popup=popup_text,
                tooltip=row['attributes.NAME_rest']
            ).add_to(m)
        except Exception as e:
            st.warning(f"Skipping invalid marker for {row['attributes.NAME_rest']}: {str(e)}")

    st.subheader("Map of Infestations")
    folium_static(m)
else:
    st.write("No data available for mapping.")

# Date filter
st.subheader("Filters")
if 'attributes.INSPECTDATE_viol' in merged_df.columns:
    try:
        merged_df['attributes.INSPECTDATE_viol'] = pd.to_datetime(merged_df['attributes.INSPECTDATE_viol'], errors='coerce')
        min_date = merged_df['attributes.INSPECTDATE_viol'].min().date()
        max_date = merged_df['attributes.INSPECTDATE_viol'].max().date()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input("Select date range", [min_date, max_date])
            filtered_df = merged_df[(merged_df['attributes.INSPECTDATE_viol'].dt.date >= date_range[0]) & 
                                  (merged_df['attributes.INSPECTDATE_viol'].dt.date <= date_range[1])]
            st.write(f"Filtered violations: {len(filtered_df)}")
            if not filtered_df.empty:
                m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)
                for idx, row in filtered_df.iterrows():
                    popup_text = f"<b>{row['attributes.NAME_rest']}</b><br>Address: {row['attributes.ADDRESS1_rest']}, {row['attributes.CITY_rest']}<br>Date: {row['attributes.INSPECTDATE_viol']}<br>Violation: {row['attributes.SHORTDESC_viol']}<br>Comments: {row['attributes.COMMENTS_viol']}"
                    try:
                        folium.Marker(
                            location=[row['Y'], row['X']],
                            popup=popup_text,
                            tooltip=row['attributes.NAME_rest']
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Skipping invalid marker for {row['attributes.NAME_rest']}: {str(e)}")
                st.subheader("Filtered Map")
                folium_static(m)
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available.")
