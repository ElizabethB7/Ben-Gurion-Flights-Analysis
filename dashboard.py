# import
import streamlit as st
import pandas as pd
import requests
from IPython.display import display
from datetime import datetime
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
import plotly.graph_objects as go
from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent="ben_gurion_dashboard")

# ETL(Extract, Transform, Load) Block:
@st.cache_data
def get_flight_data():
    # API - מאגר טיסות - EXTRACT
   
    resource_id = "e83f763b-b7d7-479e-b172-ae981ddc6de5"

    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}"

    # send requests to website and get response(code)
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"There is a problem: {response.status_code}")
        return None
    
    # parsing  the data we got
    data = response.json()
    
    # convert to DataFrame
    records = data['result']['records']
    df_flights = pd.DataFrame(records)
    
    #TRANSFORM

    # Rename columns to meaningful names
    df_flights = df_flights.rename(columns={
        '_id': 'id',
        'CHOPER': 'airline_code',
        'CHOPERD': 'airline_name',
        'CHFLTN': 'flight_number',
        'CHAORD': 'direction',
        'CHSTOL': 'scheduled_time',
        'CHPTOL': 'actual_time',
        'CHLOC1': 'airport_code',
        'CHLOC1D': 'airport_name',
        'CHLOC1TH': 'city_hebrew',
        'CHLOC1T': 'city_english',
        'CHLOC1CH': 'country_hebrew',
        'CHLOCCT': 'country_english',
        'CHTERM': 'terminal',
        'CHCINT': 'checkin_counters',
        'CHCKZN': 'checkin_zone',
        'CHRMINE': 'flight_status',
        'CHRMINH': 'flight_status_hebrew'
    }, errors='ignore')




    df_flights['terminal'] = pd.to_numeric(df_flights['terminal'], errors='coerce').astype('Int8')
    df_flights['flight_number'] = df_flights['flight_number'].astype(str)
    df_flights['scheduled_time'] = pd.to_datetime(df_flights['scheduled_time'])
    df_flights['actual_time'] = pd.to_datetime(df_flights['actual_time'])
    df_flights['terminal'] = pd.to_numeric(df_flights['terminal'], errors='coerce').astype('Int8')

    # missing values:
    # flights that are landing they are arrivel = mean no need to checkin so fill the empty to 'N/A'
    df_flights.loc[df_flights['direction'] == 'A', ['checkin_counters', 'checkin_zone']] = 'N/A'

    # flights that are leaving they are departure = means they do need to do check in so, if there is empty for any reason fill it as 'Missing'
    mask_missing_departures = (df_flights['direction'] == 'D') & (df_flights['checkin_counters'].isna())
    df_flights.loc[mask_missing_departures, ['checkin_counters', 'checkin_zone']] = 'Missing'
    #return to us the df - LOAD
    return df_flights


@st.cache_data(show_spinner=False, persist="disk")
def get_city_coords(city_name, country_name=None):
    query = f"{city_name}"
    if country_name and pd.notna(country_name):
        query += f", {country_name}"
    else:
        query += ", airport"
    try:
        location = geolocator.geocode(query, timeout=10)
        return (location.latitude, location.longitude) if location else (None, None)
    except:
        return (None, None)

def enrich_data(df):
    for index, row in df.iterrows():
        city = row['city_english']
        country = row['country_english']
        
        coords = get_city_coords(city, country)
        
        df.at[index, 'lat'] = coords[0]
        df.at[index, 'lon'] = coords[1]
    
    return df

# Fetch latest flight data
df_flights = get_flight_data()

# assign new columns - latitude and longitude
with st.spinner('Enriching map data...'):
    df_flights = enrich_data(df_flights)

# Filter for real-time flight data.
now = datetime.now()
today = now.date()

today_flight = df_flights[
    (df_flights['actual_time'].dt.date == today) &
    (df_flights['actual_time'] <= now)
]

# title
current_time = datetime.now().strftime("%H:%M")

st.markdown(f"""
    <h1 style='text-align: center;'>Ben Gurion Flights Real Time ✈️</h1>
    <h4 style='text-align: center;'>Last Update: {current_time}</h4>
""", unsafe_allow_html=True)
st.divider()

# BLOCK 1 - Shows the total flights, how many of the flights are departures, and how many are arrivals.
total = len(today_flight)
deps = len(today_flight[today_flight['direction'] == 'D'])
arrs = len(today_flight[today_flight['direction'] == 'A'])

html_card = f"""
<div style="
    background-color: #ffffff; 
    padding: 25px; 
    border-radius: 15px; 
    text-align: center; 
    border: 3px solid #1E88E5; 
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    font-family: sans-serif;">
    
    <h3 style="color: #6A5ACD; margin: 0;">Total Flights Today</h3>
    <h1 style="color: #000000; font-size: 60px; margin: 10px 0;">{total}</h1>
    
    <hr style="border: 1px solid #eee; margin: 20px 0;">
    
    <div style="display: flex; justify-content: space-around;">
        <div style="text-align: center;">
            <h4 style="color: #1E88E5; margin: 0;">Departures 🛫</h4>
            <h2 style="margin: 5px 0 0 0;">{deps}</h2>
        </div>
        <div style="text-align: center;">
            <h4 style="color: #FF9800; margin: 0;">Arrivals 🛬</h4>
            <h2 style="margin: 5px 0 0 0;">{arrs}</h2>
        </div>
    </div>
</div>
"""

components.html(html_card, height=260)

# map of the flight lines
st.subheader("Direction Of Popular Destinations:")

# remove duplicates destinations
unique_destinations = today_flight.dropna(subset=['lat', 'lon']).drop_duplicates(subset=['city_english'])

fig = go.Figure()

# Plot Ben Gurion Airport as origin
fig.add_trace(go.Scattermapbox(
    lat=[32.00], lon=[34.87],
    mode='markers',
    marker=dict(size=14, color='red', symbol='airport'),
    hoverinfo='text',
    text=['Ben Gurion Airport']
))

# Draw flight paths for all valid destinations
for i, row in unique_destinations.iterrows():
    fig.add_trace(go.Scattermapbox(
        mode='lines',
        lat=[32.00, row['lat']],
        lon=[34.87, row['lon']],
        line=dict(width=1.5, color='black'),
        opacity=0.5,
        hoverinfo='name',
        name=row['city_english']
    ))

fig.update_layout(
    mapbox=dict(
        style="open-street-map",  # This is free and doesn't require a token
        center=dict(lat=32.00, lon=34.87),
        zoom=1.5
    ),
    height=600,
    margin={"r":0,"t":0,"l":0,"b":0},
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# st.write(f"מספר הטיסות שנמצאו עם מיקום: {len(today_flight.dropna(subset=['lat', 'lon']))}")
