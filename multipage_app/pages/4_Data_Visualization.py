#importing the requirements
import calendar
import streamlit as st
import altair as alt
from datetime import date
import plotly.express as px


from utils import DATA,api_call, get_coords_by_price_code, area_name

st.markdown(" ## Weather Data Insights")
st.markdown(""" Explore normalized weather data from 2000-2024. Select price area, months and weather variables to visualize trends over time.""")

col1,col2=st.columns(2)
with col1:
    year = st.number_input("Select year",
            min_value=2000,
            max_value=2024,
            value=2021,
            step=1)
with col2:
# Let the user select a Price Area  by city name
    selected_price_area = st.selectbox("Select a Price Area:",
        options=[info["PriceAreaCode"] for info in DATA.values()],
        format_func=lambda code: area_name(code)) 
#year = 2021

# Get coordinates from utils
coords = get_coords_by_price_code(selected_price_area)

# Call the API
df= api_call(coords, year)

#Creating a slider to select months using their name
months = list(calendar.month_name)[1:]
month_range = st.select_slider('Select a range of months:',options=months,value=('January', 'January'))

#Finding all selected months from the slider
start_month = months.index(month_range[0])
end_month = months.index(month_range[1])
selected_months = months[start_month:end_month + 1]

#Creating a month name column from dataframe time column
df['time'] = (df['date'])
df['month'] = df['time'].dt.month_name()

#Converting wide format to long format data so its easy to use altair
columns = [column for column in df.columns if column not in ['time','month','date']]
df_melted = df.melt(id_vars=['time','month'],value_vars=columns,var_name='variable',value_name='value' )

#Filtering dataframe for selected months range
df_selected=df_melted[df_melted['month'].isin(selected_months)]

# Creating a selectbox of numeric columns
option = ["-- Select --"] + columns + ['All variables']
selected_option=st.selectbox('Choose weather variable:',option)



# Creating plot of all columns together
if selected_option == 'All variables':
    st.write(f"You selected: {selected_option}")
    st.text(" ")

    # Plotly line chart for all variables
    fig_all = px.line(
        df_selected,
        x="time",
        y="value",
        color="variable",
        title=f"Graph of {selected_option} over Year 2021",
        labels={
            "time": "Year 2021",
            "value": "Weather data over 2021",
            "variable": "Variables"
        }
    )
    fig_all.update_layout(width=800, height=400, hovermode="x unified")
    st.plotly_chart(fig_all, use_container_width=True)
    st.markdown('<span style="color:blue;">Hover over the chart to inspect specific values.</span>', unsafe_allow_html=True)

# Creating plot of each column
elif selected_option != "-- Select --":
    st.write(f"You selected: {selected_option}")
    st.text(" ")

    df_col = df_selected[df_selected['variable'] == selected_option]

    # Plotly line chart for single variable
    fig_col = px.line(
        df_col,
        x="time",
        y="value",
        color="variable",
        title=f"Graph of {selected_option} over Year 2021",
        labels={
            "time": "Year 2021",
            "value": selected_option,
            "variable": "Variable"
        }
    )
    fig_col.update_layout(width=800, height=400, hovermode="x unified")
    st.plotly_chart(fig_col, use_container_width=True)
    st.markdown('<span style="color:blue;">Hover over the chart to inspect specific values.</span>', unsafe_allow_html=True)

else:
    st.warning("Select a variable to see the chart.")
