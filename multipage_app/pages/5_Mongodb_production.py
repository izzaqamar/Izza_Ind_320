# mongodb.py
import streamlit as st
import pymongo
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import plotly.express as px
import calendar

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()

# Pull data from the collection.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def get_data():
    database=client['ind320_production_db']
    collection=database['ind320_production_table']
    items = collection.find()
    items = list(items)
    return items

all_items = get_data()

# Convert to Pandas DataFrame
mongodb_df = pd.DataFrame(all_items)
#Getting the time in right format
mongodb_df['startTime'] = pd.to_datetime(mongodb_df['startTime'])

# Display first 5 rows
st.write("### Preview of data from MongoDB")
#st.dataframe(mongodb_df.head(5))

#Using st.columns to split view in 2 parts

col_left,col_right=st.columns(2)#,vertical_alignment="bottom")

#For the left side conatining pie plot
with col_left:
    st.header("A pie plot")
    price_areas = mongodb_df['priceArea'].unique().tolist()
    selected_price_area=st.radio("Select an area",price_areas)
    filtered_df_pie=mongodb_df[mongodb_df["priceArea"]==selected_price_area]\
    .groupby("productionGroup").agg(total_production=("quantityKwh", "sum")).reset_index()
    
    #Creating a Plotly pie chart
    fig = px.pie(filtered_df_pie,
        names="productionGroup",   
        values="total_production",  
        title="Pie Plot of Production Quantity")

    #Showing the figure
    fig.update_traces(textinfo='percent+label',textposition='outside',pull=[0.1, 0.1, 0],textfont_size=12)
    fig.update_layout(showlegend=True,margin=dict(t=50, b=50, l=50, r=50),width=700,height=700)
    #To display the pie chart
    st.plotly_chart(fig, use_container_width=True) 


#For the right side conatining line plot #Do we need to filter on selected price area for pie plot
with col_right:
    st.header("A line plot")
    #Extracting all the production groups in a list
    production_groups=mongodb_df['productionGroup'].unique().tolist() #if include price,then switch mongodb_df with price area df

    #Adding an st.pills to select multiple groups
    selected_group=st.pills("Production Groups",production_groups,selection_mode="multi")

    #Adding a month column extracted from startTime for easy filtering
    mongodb_df['month'] = mongodb_df['startTime'].dt.month_name()

    #Generating a list of month names using calendar.month_name
    months = list(calendar.month_name)[1:]  

    #Adding a seelctbox to choose any month
    selected_month = st.selectbox("Select a month:", months)

    #Filtering data for selected month and selected group and then grouping for line plot
    filtered_df_month_group=mongodb_df[(mongodb_df["productionGroup"].isin(selected_group))&(mongodb_df["month"]==selected_month)]
    grouped_df_month_group=filtered_df_month_group.groupby(["startTime","productionGroup"]).agg(total_production=("quantityKwh", "sum")).reset_index()
    
    #Plotting line chart using plotly
    fig = px.line(grouped_df_month_group,x='startTime',
        y='total_production',
        color='productionGroup',
        title=f"Energy Production Over Time in {selected_month}",
        labels={'startTime': 'Time','total_production': 'Production (kWh)','productionGroup': 'Production Group'}
        ,template='plotly_white')

    #Customizing axes & layout
    fig.update_layout(width=1000,height=600,margin=dict(t=60, b=60, l=60, r=60),legend_title_text="Production Group")
    fig.update_xaxes(tickformat='%Y-%m-%d %H:%M',tickangle=45)

    #Displaying chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)

with st.expander("See source of the data"):
    st.write("The data is take from elhup api")
    st.markdown('[Visit the Elhub Energy Data API documentation for Price Areas](https://api.elhub.no/energy-data-api#/price-areas)',
        unsafe_allow_html=True)