import streamlit as st
import pandas as pd

st.markdown('<h1 style="color:blue;">🌦️ Weather Data Table</h1>', unsafe_allow_html=True)

#csv_path = "open-meteo-subset.csv"

@st.cache_data
def read_data():
    open_meteo_df = pd.read_csv("open-meteo-subset.csv")
    return open_meteo_df

#Importing data
open_meteo_df= read_data()

#Time column to datetime format
open_meteo_df['time']=pd.to_datetime(open_meteo_df['time'])

#Showing imported data as an editable table
st.data_editor(open_meteo_df,hide_index=True)

#Filtering the dataframe for month of January
df_jan=open_meteo_df[(open_meteo_df['time']>= '2020-01-01') & (open_meteo_df['time']<= '2020-01-31')]

#Creating a variables column and values excluding time
variables = [col for col in df_jan.columns if col != "time"]
values=[df_jan[col].tolist() for col in variables]

#Restructure our dataframe to use LineChartColumn
data_df=pd.DataFrame({'Weather Variable': variables, 'Values': values})

#Adding text
st.markdown('<span style="color:blue;">Linecharts display hourly changes for each weather variable during January 2020.</span>', unsafe_allow_html=True)

#Creating the intercative table
st.data_editor(data_df,column_config={"Values": st.column_config.LineChartColumn
                                      ('First Month Insights',
                                      help="Variable trend in January",color="blue")},hide_index=True)















