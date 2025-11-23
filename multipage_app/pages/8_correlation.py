import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import openmeteo_requests
from datetime import date, datetime, timedelta
import pymongo
import requests_cache
from retry_requests import retry
import plotly.graph_objects as go


from utils import api_call,get_production_data, get_consumption_data

#  STREAMLIT UI 
st.header("Sliding window correlation")

# Check if map click exists
if "clicked_points" not in st.session_state or not st.session_state.clicked_points:
    st.warning("Please select a point on the map first.")
    if st.button("➡️ Go to Maps Page"):
        st.session_state["section"] = "Energy"
        st.session_state["subgroup"] = "Visualization"
        st.session_state["page_name"] = "Maps"
        st.rerun()
    st.stop()

# Use the last clicked coordinate
last_point = st.session_state.clicked_points[-1]
lat = last_point["lat"]
lon = last_point["lon"]
# Wrap lat/lon into a tuple
coords = (lat, lon)

st.info(f"Selected location: {lat:.4f}, {lon:.4f}")

# Choose a year
year = st.number_input("Select year for weather retrieval",
    min_value=2021,max_value=2024,value=2021)

# Fetch weather data
with st.spinner("Fetching weather data... (cached if previously loaded)"):
    df_weather = api_call(coords, year)
    df_weather.set_index('date', inplace=True)
    df_weather.sort_index(inplace=True)
    st.success(f"Weather data successfully loaded from API for {year}!")

# Dataset selection 
col1, col2 = st.columns([1, 1])
with col1:
    data_type = st.radio("Select dataset to analyze",options=["Production", "Consumption"],index=None)

    if data_type is None:
        st.warning("Please select either Production or Consumption to continue.")
        st.stop()

    if data_type == "Production":
        df_energy = get_production_data()
        st.success("Production data loaded!")
    elif data_type == "Consumption":
        df_energy = get_consumption_data()
        st.success("Consumption data loaded!")

# Ensure time column is datetime and set as index
df_energy['startTime'] = pd.to_datetime(df_energy['startTime'])
df_energy.set_index('startTime', inplace=True)

# Filter for the selected year
df_energy_year = df_energy[df_energy.index.year == year]

# Align datasets by common timestamps
common_times = df_weather.index.intersection(df_energy_year.index)
df_weather_aligned = df_weather.loc[common_times]
df_energy_aligned = df_energy_year.loc[common_times]

with col2:
    weather_col = st.selectbox("Select weather variable", options=df_weather_aligned.columns.tolist())
    energy_col = 'quantityKwh'

# Sliding-window correlation with lag 
st.subheader("Sliding Window Correlation with Lag")

unit = st.selectbox("Select window unit", ["Hours", "Days"])

colA, colB = st.columns(2)
with colA:
    if unit == "Hours":
        window_size_input = st.slider("Select sliding window size (hours)", 1, 168, 24)
        window_size_hours = window_size_input
    elif unit == "Days":
        window_size_input = st.slider("Select sliding window size (days)", 1, 30, 7)
        window_size_hours = window_size_input * 24

with colB:
    if unit == "Hours":
        lag_input = st.slider("Select lag (hours)", -72, 72, 0)
        lag_hours = lag_input
    elif unit == "Days":
        lag_input = st.slider("Select lag (days)", -7, 7, 0)
        lag_hours = lag_input * 24

# Apply lag
df_energy_lagged = df_energy_aligned[energy_col].copy().shift(lag_hours)

# Compute sliding-window correlation
swc = df_weather_aligned[weather_col].rolling(window_size_hours, center=True).corr(df_energy_lagged)

# Plot SWC
fig = go.Figure()
fig.add_trace(go.Scatter(x=swc.index, y=swc, mode='lines', name=f'SWC (lag={lag_hours}h)'))
fig.update_layout(
    title=f"Sliding-window correlation ({window_size_hours}h) between {weather_col} and {energy_col} (lag={lag_hours}h)",
    xaxis_title="Time",yaxis_title="Correlation",yaxis=dict(range=[-1, 1]))
st.plotly_chart(fig, use_container_width=True)