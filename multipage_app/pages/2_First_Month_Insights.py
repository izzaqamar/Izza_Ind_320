import streamlit as st
import pandas as pd

st.title("🌦️ Weather Data Table ")

#csv_path = "open-meteo-subset.csv"

@st.cache_data
def read_data():
    open_meteo_df = pd.read_csv("open-meteo-subset.csv", parse_dates=['time'])
    open_meteo_df.set_index('time', inplace=True)
    return open_meteo_df

open_meteo_df= read_data()

first_month_df = open_meteo_df[(open_meteo_df.index.year == open_meteo_df.index[0].year) & (open_meteo_df.index.month == open_meteo_df.index[0].month)]

st.markdown("### 📊 Line Charts (First Month)")
for column in first_month_df.columns:
 with st.container():
    col1, col2 = st.columns([1, 4])
    with col1:
        col1.subheader(f"{column} over time")
        #st.header(f"{column} over time")
        #st.markdown(f"**{column}**")
    with col2:
        st.line_chart(first_month_df[column])