import streamlit as st
import pandas as pd


if "df_city" not in st.session_state:
    st.warning('Select an area and run page new_A first')
    st.stop()  # stops execution of the rest of the script

df_city=st.session_state['df_city']
st.write('The selected area is:', st.session_state['selected_price_area'])


st.write("SESSION ID:", id(st.session_state))

st.markdown('<h1 style="color:blue;">🌦️ Weather Data </h1>', unsafe_allow_html=True)
#st.write('The downloaded data is for selected area :',df_city.head())

#Importing data
open_meteo_df= df_city=st.session_state['df_city']

#Time column to datetime format
#open_meteo_df['time']=pd.to_datetime(open_meteo_df['time'])

#Renaming the column as in previous task it was named time instead of date
open_meteo_df['time'] = (open_meteo_df['date'])

#Showing imported data as an editable table
#st.data_editor(open_meteo_df,hide_index=True)

#Filtering the dataframe for month of January
#df_jan=open_meteo_df[(open_meteo_df['time']>= '2020-01-01') & (open_meteo_df['time']<= '2020-01-31')]

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