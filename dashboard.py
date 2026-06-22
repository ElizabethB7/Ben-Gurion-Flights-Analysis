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

df_flights = get_flight_data()

# 1
now = datetime.now()
today = now.date()

today_flight = df_flights[
    (df_flights['actual_time'].dt.date == today) &
    (df_flights['actual_time'] <= now)
]


st.markdown("<h1 style='text-align: center;'>Ben Gurion Flights Real Time ✈️</h1>", unsafe_allow_html=True)
st.divider() 

# BLOCK 1 
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