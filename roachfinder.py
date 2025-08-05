import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
from io import StringIO

# Title of the app
st.title("Cockroach Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes cockroach-related violations from Wake County food inspection data on a map.
Data is sourced from public ArcGIS services. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: In the Raleigh metro area, about 18-20% of households reported cockroach sightings in recent surveys.
""")

# Headers to mimic a browser request and avoid blocks
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Cache data loading with error handling
@st.cache_data
def load_data():
    try:
        # URL for Restaurants layer (locations)
        restaurants_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/0/query?where=1=1&outFields=HSISID,NAME,ADDRESS1,CITY,POSTALCODE,X,Y&f=csv"
        response = requests.get(restaurants_url, headers=headers)
        response.raise_for_status()
        restaurants_df = pd.read_csv(StringIO(response.text))
        
        # URL for Violations layer
        violations_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/2/query?where=1=1&outFields=*&f=csv"
        response = requests.get(violations_url, headers=headers)
        response.raise_for_status()
        violations_df = pd.read_csv(StringIO(response.text))
        
        return restaurants_df, violations_df
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}. The server may be temporarily unavailable or require authentication. Try again later or check the data source.")
        return None, None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

# Load data
restaurants_df, violations_df = load_data()

if restaurants_df is None or violations_df is None:
    st.stop()

# Filter for cockroach-related violations
keywords = ['cockroach', 'roaches', 'pest', 'insect']
mask = violations_df['COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
       violations_df['SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
cockroach_viol = violations_df[mask]

# Merge with locations
merged_df = cockroach_viol.merge(restaurants_df, on='HSISID', how='left')

# Drop rows without valid coordinates
merged_df = merged_df.dropna(subset=['X', 'Y'])
merged_df = merged_df[(merged_df['X'] != 0) & (merged_df['Y'] != 0)]  # Filter out invalid coords

# Display summary
st.subheader("Summary")
if not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    st.dataframe(merged_df[['NAME', 'ADDRESS1', 'CITY', 'INSPECTDATE', 'SHORTDESC', 'COMMENTS']].head(10))
else:
    st.warning("No cockroach-related violations found in the data.")

# Create map
if not merged_df.empty:
    # Initialize map centered on Raleigh (lat, lon)
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}"
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
    st.write("No data available for mapping.")

# Date filter
st.subheader("Filters")
if 'INSPECTDATE' in violations_df.columns:
    try:
        violations_df['INSPECTDATE'] = pd.to_datetime(violations_df['INSPECTDATE'], errors='coerce')
        min_date = violations_df['INSPECTDATE'].min().date()
        max_date = violations_df['INSPECTDATE'].max().date()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input("Select date range", [min_date, max_date])
            # Filter merged_df based on date range
            merged_df['INSPECTDATE'] = pd.to_datetime(merged_df['INSPECTDATE'], errors='coerce')
            filtered_df = merged_df[(merged_df['INSPECTDATE'].dt.date >= date_range[0]) & (merged_df['INSPECTDATE'].dt.date <= date_range[1])]
            st.write(f"Filtered violations: {len(filtered_df)}")
            # You can update the map or table with filtered_df here if desired
        else:
            st.write("Date data is incomplete.")
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available.")
