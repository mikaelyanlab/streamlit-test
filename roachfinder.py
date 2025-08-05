import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
from io import StringIO
import json
import os

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

# Local file paths for saving/loading state
restaurants_file = "restaurants_cache.csv"
violations_file = "violations_cache.csv"

# Function to save DataFrame to CSV
def save_df_to_file(df, file_path):
    df.to_csv(file_path, index=False)

# Cache data loading with pagination and debugging
@st.cache_data
def load_data_from_api(base_url, layer_id, out_fields, token=None, max_requests=50):
    st.write(f"Attempting to load data from {base_url}{layer_id}/query")
    try:
        # Get total record count
        count_params = {
            'where': '1=1',
            'returnCountOnly': 'true',
            'f': 'json'
        }
        if token:
            count_params['token'] = token

        count_response = requests.get(base_url + str(layer_id) + '/query', params=count_params, headers=headers, timeout=10)
        count_response.raise_for_status()
        total_count = count_response.json().get('count', 0)
        st.write(f"Total records available: {total_count}")

        all_data = []
        offset = 0
        max_records = 2000  # As per MaxRecordCount
        requests_made = 0
        progress_bar = st.progress(0)

        while requests_made < max_requests:
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
            requests_made += 1
            progress_bar.progress(min(requests_made / max_requests, 1.0))

            if not data.get('exceededTransferLimit', False):
                st.write("No more data to fetch.")
                break

            if len(features) < max_records:
                st.write("Reached end of data chunk.")
                break

        if all_data:
            df = pd.json_normalize(all_data)
            st.write(f"Successfully loaded {len(df)} records out of {total_count}.")
            if len(df) < total_count:
                st.warning(f"Dataset truncated to {len(df)} records due to request limit. Consider using local files for full data.")
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

# Load from local cache if exists
if os.path.exists(restaurants_file) and os.path.exists(violations_file):
    restaurants_df = pd.read_csv(restaurants_file)
    violations_df = pd.read_csv(violations_file)
    st.success("Loaded data from local cache files to preserve state.")
else:
    # API URLs and fields
    base_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/"
    restaurants_df = load_data_from_api(base_url, 0, "HSISID,NAME,ADDRESS1,CITY,POSTALCODE,X,Y")
    violations_df = load_data_from_api(base_url, 2, "*")

    if restaurants_df is not None and violations_df is not None:
        # Save to local cache for future runs
        save_df_to_file(restaurants_df, restaurants_file)
        save_df_to_file(violations_df, violations_file)
        st.success("Data loaded from API and saved to local cache for future use.")

if restaurants_df is None or violations_df is None:
    restaurants_df, violations_df = load_local_data()
    if restaurants_df is None or violations_df is None:
        st.markdown("**Instructions**: Download data from https://data-wake.opendata.arcgis.com/datasets/food-inspections (CSV/JSON) and upload above, or obtain an API token from Wake County.")
        st.stop()

# Debug: Show available columns
st.write("Restaurants DataFrame columns:", restaurants_df.columns.tolist())
st.write("Violations DataFrame columns:", violations_df.columns.tolist())
st.write("Merged DataFrame columns:", merged_df.columns.tolist())

# Filter for cockroach-related violations incrementally
keywords = ['cockroach', 'roaches', 'pest', 'insect']
mask = violations_df['attributes.COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
       violations_df['attributes.SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
cockroach_viol = violations_df[mask]

# Merge with locations, selecting only necessary restaurant columns
merged_df = cockroach_viol.merge(restaurants_df[['attributes.HSISID', 'attributes.X', 'attributes.Y', 'attributes.NAME', 'attributes.ADDRESS1', 'attributes.CITY', 'attributes.POSTALCODE']], 
                                on='attributes.HSISID', how='left', suffixes=('_viol', '_rest'))

# Drop rows without valid coordinates with error handling
try:
    merged_df = merged_df.dropna(subset=['attributes.X', 'attributes.Y'])
    merged_df = merged_df[(merged_df['attributes.X'] != 0) & (merged_df['attributes.Y'] != 0)]
except KeyError as e:
    st.error(f"KeyError: Columns 'attributes.X' or 'attributes.Y' not found in merged DataFrame. Available columns: {merged_df.columns.tolist()}")
    st.stop()

# Rename coordinates for consistency
merged_df = merged_df.rename(columns={'attributes.X': 'X', 'attributes.Y': 'Y'})

# Display summary and map incrementally
st.subheader("Summary")
if not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    # Use correct column names based on merge suffixes
    st.dataframe(merged_df[['attributes.NAME', 'attributes.ADDRESS1', 'attributes.CITY',
                           'attributes.INSPECTDATE_viol', 'attributes.SHORTDESC_viol', 'attributes.COMMENTS_viol']].head(10))
else:
    st.warning("No cockroach-related violations found in the data.")

if not merged_df.empty:
    # Initialize map centered on Raleigh (lat, lon)
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['attributes.NAME']}</b><br>Address: {row['attributes.ADDRESS1']}, {row['attributes.CITY']}<br>Date: {row['attributes.INSPECTDATE_viol']}<br>Violation: {row['attributes.SHORTDESC_viol']}<br>Comments: {row['attributes.COMMENTS_viol']}"
        try:
            folium.Marker(
                location=[row['Y'], row['X']],  # Y=latitude, X=longitude
                popup=popup_text,
                tooltip=row['attributes.NAME']
            ).add_to(m)
        except Exception as e:
            st.warning(f"Skipping invalid marker for {row['attributes.NAME']}: {str(e)}")

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
                    popup_text = f"<b>{row['attributes.NAME']}</b><br>Address: {row['attributes.ADDRESS1']}, {row['attributes.CITY']}<br>Date: {row['attributes.INSPECTDATE_viol']}<br>Violation: {row['attributes.SHORTDESC_viol']}<br>Comments: {row['attributes.COMMENTS_viol']}"
                    try:
                        folium.Marker(
                            location=[row['Y'], row['X']],
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
    st.write("Inspection date data not available.")
