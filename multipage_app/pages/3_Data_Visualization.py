import pandas as pd
import calendar
import streamlit as st
import altair as alt

st.markdown('<h1 style="color:blue;">Weather Data Visualization Dashboard</h1>', 
    unsafe_allow_html=True)
st.markdown(""" Explore normalized weather data from 2020. Select months and weather variables to visualize trends over time.""")


#Reading data
@st.cache_data
def read_data():
    open_meteo_df = pd.read_csv("open-meteo-subset.csv", parse_dates=['time'])
    return open_meteo_df
df= read_data()

#Creating a slider to select months using their name
months = list(calendar.month_name)[1:]
month_range = st.select_slider('Select a range of months:',options=months,value=('January', 'January'))

#Finding all selected months from the slider
start_month = months.index(month_range[0])
end_month = months.index(month_range[1])
selected_months = months[start_month:end_month + 1]

#Creating a month name column from dataframe time column
df['month'] = df['time'].dt.month_name()

#Converting wide format to long format data so its easy to use altair
columns=[column for column in df.columns if column not in ['time','month']]
df_melted = df.melt(id_vars=['time','month'],value_vars=columns,var_name='variable',value_name='value' )

#Filtering dataframe for selected months range
df_selected=df_melted[df_melted['month'].isin(selected_months)]

# Creating a selectbox of numeric columns
option = ["-- Select --"] + columns + ['All variables']
selected_option=st.selectbox('Choose weather variable:',option)

#Creating plot of all columns together
if selected_option == 'All variables':
    st.write(f"You selected: {selected_option}")
    st.text(" ")
    graph_all=alt.Chart(df_selected).mark_line().encode(
        x=alt.X('time:T',title='Year 2020'),
        y=alt.Y('value:Q',title='Weather data over 2020'),
        color=alt.Color('variable:N', title='Variables'),
        tooltip=['time:T', 'value:Q']).properties( width=800,height=400,title= f'Graph of {selected_option} over Year 2020').interactive()
    st.altair_chart(graph_all, use_container_width=True)
    st.markdown('<span style="color:blue;">Hover over the chart to inspect specific values.</span>', unsafe_allow_html=True)

#Creating plot of each column
elif selected_option != "-- Select --":
    st.write(f"You selected: {selected_option}")
    st.text(" ")
    df_col = df_selected[df_selected['variable'] == selected_option]
    graph_col=alt.Chart(df_col).mark_line().encode(
    x=alt.X('time:T', title='Year 2020'),
    y=alt.Y('value:Q',title=selected_option),
    color=alt.Color('variable:N', title='Variable'),
    tooltip=['time:T', 'value:Q']).properties( width=800,height=400,title= f'Graph of {selected_option} over Year 2020').interactive()
    st.altair_chart(graph_col, use_container_width=True)
    st.markdown('<span style="color:blue;">Hover over the chart to inspect specific values.</span>', unsafe_allow_html=True)
else:
   st.warning("Select a variable to see the chart.") 
        
