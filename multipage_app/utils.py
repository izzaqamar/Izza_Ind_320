import streamlit as st
import pymongo
import pandas as pd
import pandas as pd
import requests_cache
import openmeteo_requests
from retry_requests import retry
from datetime import date


# MongoDB connection
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()

@st.cache_data(ttl=600)
def get_production_data():
    database = client['ind320_production_db']
    collection = database['ind320_production_table_d4']
    items = list(collection.find())
    df = pd.DataFrame(items)
    if 'startTime' in df.columns:
        df['startTime'] = pd.to_datetime(df['startTime'])
    return df

@st.cache_data(ttl=600)
def get_consumption_data():
    database = client['ind320_production_db']
    collection = database['ind320_consumption_table']
    items = list(collection.find())
    df = pd.DataFrame(items)
    time_columns = ["startTime", "endTime"]
    for col in time_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


### METEOROLOGY DATA FROM OPEN METEO API ###

# City metadata
DATA = {
    'Oslo': {'PriceAreaCode': 'NO1', 'Longitude': 10.7461, 'Latitude': 59.9127},
    'Kristiansand': {'PriceAreaCode': 'NO2', 'Longitude': 7.9956, 'Latitude': 58.1467},
    'Trondheim': {'PriceAreaCode': 'NO3', 'Longitude': 10.3951, 'Latitude': 63.4305},
    'Tromsø': {'PriceAreaCode': 'NO4', 'Longitude': 18.9551, 'Latitude': 69.6489},
    'Bergen': {'PriceAreaCode': 'NO5', 'Longitude': 5.32415, 'Latitude': 60.39299},
}

# Setup Open-Meteo client once
_cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
_retry_session = retry(_cache_session, retries=5, backoff_factor=0.2)
_openmeteo = openmeteo_requests.Client(session=_retry_session)

@st.cache_data(show_spinner=False)
def api_call(coords, year):
    """Fetch hourly weather data for given coordinates and year."""
    lat, lon = coords
    start_date = date(year, 1, 1).strftime("%Y-%m-%d")
    end_date = date(year, 12, 31).strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m",
                   "wind_gusts_10m", "wind_direction_10m"],
        "models": "era5",
    }
    responses = _openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "precipitation": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
        "wind_gusts_10m": hourly.Variables(3).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(4).ValuesAsNumpy(),
    }

    df = pd.DataFrame(hourly_data)
    df['date'] = df['date'].dt.tz_localize(None)  # drop UTC
    return df


def get_coords_by_price_code(price_code):
    """Return (lat, lon) for a given PriceAreaCode."""
    for _, info in DATA.items():
        if info['PriceAreaCode'] == price_code:
            return info['Latitude'], info['Longitude']


def area_name(price_code):
    """Return city name for a given PriceAreaCode."""
    for city, info in DATA.items():
        if info['PriceAreaCode'] == price_code:
            return city


