import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import geopandas as gpd
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime

# Known termite species for extraction
known_species = [
    'eastern subterranean', 'formosan', 'west indian drywood',
    'dark southern subterranean', 'light southern subterranean', 'southeastern drywood',
    'reticulitermes flavipes', 'reticulitermes virginicus', 'reticulitermes hageni',
    'reticulitermes malletei', 'reticulitermes nelsonae'
]

# Sample initial data with pre-assigned species based on source analysis
data = {
    'county': ['Alamance', 'Alexander', 'Beaufort', 'Brunswick', 'Buncombe', 'Burke', 'Cumberland', 'Dare', 'Durham', 'Gaston', 'Guilford', 'Mecklenburg', 'New Hanover', 'Rutherford', 'Sampson', 'Wake'],
    'report_count': [1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3],
    'reports': [
        [{'link': 'https://www.youtube.com/watch?v=iGTUmm5AydI', 'species': 'Unknown'}],  # Alamance
        [{'link': 'https://qualitycontrolinc.com/termite-control-alexander-county-nc/termite-reports/', 'species': 'Unknown'}],  # Alexander
        [{'link': 'https://www.researchgate.net/publication/23233402', 'species': 'Reticulitermes flavipes, Reticulitermes hageni, Reticulitermes virginicus'}],  # Beaufort (using central NC proxy)
        [{'link': 'https://www.ncagr.gov/divisions/structural-pest-control-and-pesticides/structural/consumer-information/homeowners-guide-wood-destroying-insect-report', 'species': 'Unknown'},
         {'link': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/', 'species': 'Reticulitermes malletei, Reticulitermes flavipes'}],  # Brunswick
        [{'link': 'https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs', 'species': 'Unknown'}],  # Buncombe
        [{'link': 'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/', 'species': 'Unknown'},
         {'link': 'https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs', 'species': 'Unknown'}],  # Burke
        [{'link': 'https://www.researchgate.net/publication/23233402', 'species': 'Reticulitermes flavipes, Reticulitermes hageni, Reticulitermes virginicus'}],  # Cumberland
        [{'link': 'https://outerbanks-pestcontrol.com/category/termites/', 'species': 'Unknown'}],  # Dare
        [{'link': 'https://neusetermiteandpest.com/termite-treatment-in-durham-nc', 'species': 'Unknown'}],  # Durham
        [{'link': 'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/', 'species': 'Unknown'}],  # Gaston
        [{'link': 'https://www.go-forth.com/resource-center/let-s-chat-about-termites-in-greensboro/', 'species': 'Unknown'}],  # Guilford
        [{'link': 'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/', 'species': 'Unknown'}],  # Mecklenburg
        [{'link': 'https://www.researchgate.net/publication/23233402', 'species': 'Reticulitermes flavipes, Reticulitermes hageni, Reticulitermes virginicus'}],  # New Hanover
        [{'link': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/', 'species': 'Reticulitermes malletei, Reticulitermes flavipes'},
         {'link': 'https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs', 'species': 'Unknown'}],  # Rutherford
        [{'link': 'https://www.researchgate.net/publication/23233402', 'species': 'Reticulitermes flavipes, Reticulitermes hageni, Reticulitermes virginicus'}],  # Sampson
        [{'link': 'https://www.reddit.com/r/raleigh/comments/58ajs6/termites/', 'species': 'Unknown'},
         {'link': 'https://urbanentomology.tamu.edu/wp-content/uploads/sites/19/2018/07/Parman_and_Vargo_JEE_2008.pdf', 'species': 'Unknown'},
         {'link': 'https://content.ces.ncsu.edu/monitoring-management-of-eastern-subterranean-termites', 'species': 'Eastern Subterranean Termite (Reticulitermes flavipes)'}]  # Wake
    ]
}
df = pd.DataFrame(data)

# Load US counties GeoJSON from URL and filter for NC (STATEFP == '37')
geojson_url = 'https://gist.githubusercontent.com/sdwfrost/d1c73f91dd9d175998ed166eb216994a/raw/e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson'
gdf = gpd.read_file(geojson_url)
gdf = gdf[gdf['STATEFP'] == '37']  # Filter to North Carolina
gdf['county'] = gdf['NAME']  # Use the county name as is (title case)

# Merge data with GeoDataFrame
gdf = gdf.merge(df, on='county', how='left')

# Handle NaNs separately
gdf['report_count'] = gdf['report_count'].fillna(0)
gdf['reports'] = gdf['reports'].apply(lambda x: x if isinstance(x, list) else [])

# Create species summary column
gdf['species_summary'] = gdf['reports'].apply(lambda reports: ', '.join(sorted(set(r['species'] for r in reports if r['species'] != 'Unknown'))) if reports else 'None')

# Create popup HTML column
def generate_popup_html(row):
    html = f"<b>{row['county']}</b><br>Reports: {int(row['report_count'])}<br><ul>"
    for report in row['reports']:
        html += f"<li><a href='{report['link']}' target='_blank'>{report['link']}</a> ({report['species']})</li>"
    html += "</ul>"
    return html

gdf['popup_html'] = gdf.apply(generate_popup_html, axis=1)

# Function to search web for new reports and extract species
def trawl_for_reports():
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(f"Starting trawl at {datetime.now()}")
    global gdf
    query = "termite infestation North Carolina site:gov OR site:edu OR site:com -site:wikipedia.org"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(f"https://www.google.com/search?q={query}&num=20", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        new_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'url=' in href and 'termite' in href.lower():
                # Extract actual URL from Google redirect
                actual_url = href.split('url=')[1].split('&')[0]
                new_links.append(actual_url)
                # Fetch page content to extract species
                try:
                    page_response = requests.get(actual_url, headers=headers, timeout=5)
                    content = page_response.text.lower()
                    found_species = [s for s in known_species if s in content]
                    species_str = ', '.join(found_species) if found_species else 'Unknown'
                except Exception:
                    species_str = 'Unknown'
                # Parse for county (simple keyword match; improve with NLP)
                for county in gdf['county'].unique():
                    if county.lower() in actual_url.lower() or county.lower() in link.text.lower():
                        # Update GDF
                        idx = gdf[gdf['county'] == county].index[0]
                        gdf.at[idx, 'report_count'] += 1
                        gdf.at[idx, 'reports'].append({'link': actual_url, 'species': species_str})
                        # Update species_summary
                        gdf.at[idx, 'species_summary'] = ', '.join(sorted(set(r['species'] for r in gdf.at[idx, 'reports'] if r['species'] != 'Unknown'))) if gdf.at[idx, 'reports'] else 'None'
                        # Update popup_html
                        gdf.at[idx, 'popup_html'] = generate_popup_html(gdf.iloc[idx])
                        st.session_state.logs.append(f"Added report to {county}: {actual_url}")
        st.session_state.logs.append(f"Finished trawl at {datetime.now()}: Found {len(new_links)} potential new links.")
    except Exception as e:
        st.session_state.logs.append(f"Search error at {datetime.now()}: {e}")

# Background thread for daily trawling (after initial run)
def background_trawler():
    while True:
        time.sleep(86400)  # 24 hours
        trawl_for_reports()

# Start trawler thread and run initial trawl
if 'trawler_started' not in st.session_state:
    st.session_state['trawler_started'] = True
    # Run initial trawl immediately
    trawl_for_reports()
    # Start the background thread for subsequent daily trawls
    thread = threading.Thread(target=background_trawler, daemon=True)
    thread.start()

# Sidebar for trawling status
st.sidebar.title("Trawling Status")
if 'logs' not in st.session_state:
    st.session_state.logs = []
for log in st.session_state.logs[-10:]:  # Show last 10 logs to avoid overflow
    st.sidebar.write(log)

# Manual trawl button
if st.sidebar.button("Manual Trawl Now"):
    trawl_for_reports()

# Streamlit app
st.title("NC Termite Infestation Heatmap")

# Create Folium map
m = folium.Map(location=[35.5, -79.5], zoom_start=7)  # Center on NC

# Add choropleth
folium.Choropleth(
    geo_data=gdf,
    data=gdf,
    columns=['county', 'report_count'],
    key_on='feature.properties.NAME',
    fill_color='YlOrRd',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Report Count',
    nan_fill_color='white'
).add_to(m)

# Add tooltips (hover) and popups (click)
style_function = lambda x: {'fillOpacity': 0.0, 'weight': 0.1}
highlight_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'fillOpacity': 0.50, 'weight': 0.1}

folium.GeoJson(
    gdf,
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=['county', 'report_count', 'species_summary'],
        aliases=['County:', 'Reports:', 'Species:'],
        localize=True
    ),
    popup=folium.GeoJsonPopup(
        fields=['popup_html'],
        parse_html=True
    )
).add_to(m)

# Display map
folium_static(m, width=800, height=600)

# Auto-refresh every 60 seconds
time.sleep(60)
st.rerun()
