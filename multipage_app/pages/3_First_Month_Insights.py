import streamlit as st
import requests_cache
from retry_requests import retry
from datetime import date
import pandas as pd
import openmeteo_requests


## REMOVE THIS PAGE ###
from utils import api_call, get_coords_by_price_code, area_name

#Initializing the session state
if "selected_price_area" not in st.session_state:
    st.session_state.selected_price_area = 'NO1'
    st.session_state.area_name = 'Oslo'

st.title('Data from Open-Meteo API')

# Only call API if data not already in session
if "df_city" not in st.session_state:
    #selected_city_code = st.session_state.selected_price_area
    coords = get_coords_by_price_code(st.session_state.selected_price_area)
    year = 2021
    df_city = api_call(coords, year)
    
    # Dropping UTC
    #df_city['date'] = df_city['date'].dt.tz_localize(None)
    # Save in session state
    st.session_state.df_city = df_city
else:
    # Use existing data from session state
    df_city = st.session_state.df_city

#To get the AREA NAME corresponding to selected city code

st.session_state.area_name=area_name(st.session_state.selected_price_area)

st.write("Selected area from session state:", (st.session_state.selected_price_area))
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