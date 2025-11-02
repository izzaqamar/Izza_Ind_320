import streamlit as st
import requests_cache
from retry_requests import retry
from datetime import date
import pandas as pd
import openmeteo_requests

#Initializing the session state
if "selected_price_area" not in st.session_state:
    st.session_state.selected_price_area = 'NO1'
    st.session_state.area_name = 'Oslo'

st.title('Data from Open-Meteo API')

data={
 'Oslo': {'PriceAreaCode': 'NO1', 'Longitude': 10.7461, 'Latitude': 59.9127},
 'Kristiansand': {'PriceAreaCode': 'NO2', 'Longitude': 7.9956, 'Latitude': 58.1467},
 'Trondheim': {'PriceAreaCode': 'NO3', 'Longitude': 10.3951, 'Latitude': 63.4305},
 'Tromsø': {'PriceAreaCode': 'NO4', 'Longitude': 18.9551, 'Latitude': 69.6489},
 'Bergen': {'PriceAreaCode': 'NO5', 'Longitude': 5.32415, 'Latitude': 60.39299}}

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def api_call(coords,year):
    Latitude,Longitude=coords
    start_date=date(year, 1, 1).strftime("%Y-%m-%d")
    end_date=date(year, 12, 31).strftime("%Y-%m-%d")
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": Latitude,
        "longitude": Longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"],
        "models": "era5",
    }
    responses = openmeteo.weather_api(url, params=params)
    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    hourly_wind_gusts_10m = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    #print("\nHourly_data\n", hourly_dataframe)
    return hourly_dataframe

#Returns (Latitude, Longitude) for a given PriceAreaCode.
def get_coords_by_price_code(selected_city_code):
    for _, info in data.items():
        if info['PriceAreaCode'] == selected_city_code:
            return info['Latitude'], info['Longitude']

# Only call API if data not already in session
if "df_city" not in st.session_state:
    #selected_city_code = st.session_state.selected_price_area
    coords = get_coords_by_price_code(st.session_state.selected_price_area)
    year = 2021
    df_city = api_call(coords, year)
    
    # Dropping UTC
    df_city['date'] = df_city['date'].dt.tz_localize(None)
    # Save in session state
    st.session_state.df_city = df_city


#To get the AREA NAME corresponding to selected city code
def area_name(selected_city_code):
    for city,info in data.items():
        if info['PriceAreaCode'] == selected_city_code:
            return city
st.session_state.area_name=area_name(st.session_state.selected_price_area)

st.write("Selected area:", (st.session_state.selected_price_area))
st.write('Area Name:',st.session_state.area_name)
st.markdown('<h1 style="color:blue;">🌦️ Weather Data </h1>', unsafe_allow_html=True)

#Importing data
open_meteo_df= st.session_state.df_city
#On rerun, month column (January)is added which is dropped
open_meteo_df.drop('month', axis=1, inplace=True, errors='ignore')
#Renaming the column as in previous task it was named time instead of date
open_meteo_df['time'] = (open_meteo_df['date'])

#Filtering for 2021 now as the year is updated for deliverable-3
df_jan=open_meteo_df[(open_meteo_df['time']>= '2021-01-01') & (open_meteo_df['time']<= '2021-01-31')]

#Creating a variables column and values excluding time
variables = [col for col in df_jan.columns if col != "time"and col != "date"]
values=[df_jan[col].tolist() for col in variables]

#Restructure our dataframe to use LineChartColumn
data_df=pd.DataFrame({'Weather Variable': variables, 'Values': values})

#Adding text
st.markdown('<span style="color:blue;">Linecharts display hourly changes for each weather variable for first month of 2021.</span>', unsafe_allow_html=True)

#Creating the intercative table
st.data_editor(data_df,column_config={"Values": st.column_config.LineChartColumn
                                      ('First Month Insights',
                                     help="Variable trend in January",color="blue")},hide_index=True)