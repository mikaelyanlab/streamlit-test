import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime
import random

# List of User-Agents for rotation to avoid blocking
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.864.48 Safari/537.36 Edg/91.0.864.48',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]

# Known termite species for extraction (expanded to include more genera and species)
known_species = [
    'eastern subterranean', 'formosan', 'west indian drywood',
    'dark southern subterranean', 'light southern subterranean', 'southeastern drywood',
    'reticulitermes flavipes', 'reticulitermes virginicus', 'reticulitermes hageni',
    'reticulitermes malletei', 'reticulitermes nelsonae',
    'coptotermes formosanus', 'formosan subterranean termite',
    'cryptotermes brevis', 'west indian powderpost termite',
    'incisitermes snyderi', 'incisitermes minor', 'eastern drywood termite',
    'kalotermes approximatus', 'dampwood termite', 'neotermes castaneus'
]

# Load US counties GeoJSON from URL and filter for NC (STATEFP == '37')
geojson_url = 'https://gist.githubusercontent.com/sdwfrost/d1c73f91dd9d175998ed166eb216994a/raw/e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson'
if 'gdf' not in st.session_state:
    gdf = gpd.read_file(geojson_url)
    gdf = gdf[gdf['STATEFP'] == '37']  # Filter to North Carolina
    gdf['county'] = gdf['NAME']  # Use the county name as is (title case)
    gdf['report_count'] = 0
    gdf['reports'] = [[] for _ in range(len(gdf))]
    gdf['species_summary'] = 'None'
    gdf['popup_html'] = gdf.apply(lambda row: f"<b>{row['county']}</b><br>Reports: 0<br><ul></ul>", axis=1)
    st.session_state.gdf = gdf
else:
    gdf = st.session_state.gdf

# Create popup HTML column
def generate_popup_html(row):
    html = f"<b>{row['county']}</b><br>Reports: {int(row['report_count'])}<br><ul>"
    for report in row['reports']:
        html += f"<li><a href='{report['link']}' target='_blank'>{report['link']}</a> ({report['species']})</li>"
    html += "</ul>"
    return html

# Function to search web for new reports and extract species using Bing with rotation and delay
def trawl_for_reports():
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(f"Starting trawl at {datetime.now()}")
    query = "termite infestation North Carolina site:gov OR site:edu OR site:com -site:wikipedia.org"
    headers = {'User-Agent': random.choice(user_agents)}
    try:
        response = requests.get(f"https://www.bing.com/search?q={requests.utils.quote(query)}&count=20", headers=headers)
        st.session_state.logs.append(f"Response Status: {response.status_code}")
        st.session_state.logs.append(f"Response Length: {len(response.text)}")
        st.session_state.logs.append(f"Response Preview: {response.text[:500]}...")
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('li', class_='b_algo')
        st.session_state.logs.append(f"Found {len(results)} raw 'b_algo' elements")
        new_links = []
        for result in results:
            time.sleep(1)  # Delay to avoid rate limiting
            h2 = result.find('h2')
            if h2:
                link_tag = h2.find('a')
                if link_tag:
                    actual_url = link_tag['href']
                    new_links.append(actual_url)
                    st.session_state.logs.append(f"Found link: {actual_url}")
                    snippet_tag = result.find('p')
                    snippet = snippet_tag.text.lower() if snippet_tag else ''
                    title = h2.text.lower()
                    found_species = [s for s in known_species if s in snippet or s in title]
                    species_str = ', '.join(found_species) if found_species else 'Unknown'
                    for county in gdf['county'].unique():
                        if county.lower() in actual_url.lower() or county.lower() in title or county.lower() in snippet:
                            idx = gdf[gdf['county'] == county].index[0]
                            gdf.at[idx, 'report_count'] += 1
                            gdf.at[idx, 'reports'].append({'link': actual_url, 'species': species_str})
                            gdf.at[idx, 'species_summary'] = ', '.join(sorted(set(r['species'] for r in gdf.at[idx, 'reports'] if r['species'] != 'Unknown'))) if gdf.at[idx, 'reports'] else 'None'
                            gdf.at[idx, 'popup_html'] = generate_popup_html(gdf.iloc[idx])
                            st.session_state.logs.append(f"Added report to {county}: {actual_url} (Species: {species_str})")
        st.session_state.logs.append(f"Finished trawl at {datetime.now()}: Found {len(new_links)} potential new links.")
        st.session_state.gdf = gdf  # Save updates back to session_state
    except Exception as e:
        st.session_state.logs.append(f"Search error at {datetime.now()}: {e}")

# Sidebar for trawling status (enhanced console)
st.sidebar.title("Trawling Console (Debug Logs)")
if 'logs' not in st.session_state:
    st.session_state.logs = []
for log in st.session_state.logs[-20:]:  # Show last 20 logs for more detail
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
st_folium(m, width=800, height=600, returned_objects=[])

# Auto-refresh every 60 seconds
time.sleep(60)
st.rerun()
