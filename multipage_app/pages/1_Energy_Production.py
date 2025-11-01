# mongodb.py
import streamlit as st
import pymongo
import pandas as pd
import plotly.express as px
import calendar

if "selected_price_area" not in st.session_state:
    st.session_state.selected_price_area = 'NO1'

st.write("The selected price area is :", (st.session_state.selected_price_area))
st.write("SESSION ID:", id(st.session_state))
#st.session_state.setdefault("selected_price_area", 'NO1')

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
#Getting the time in UTC format
mongodb_df['startTime'] = pd.to_datetime(mongodb_df['startTime'], utc=True)

st.markdown(" ## **Visualisations of data fetched from MongoDB**")

#Using st.columns to split view in 2 parts
col_left,col_right=st.columns(2)


# Callback function
def update_area():
    # This runs whenever radio selection changes
    st.session_state["selected_price_area"] = st.session_state["price_area_radio"]
    st.write(f"Session state updated to: {st.session_state['selected_price_area']}")

#For the left side containing pie plot
with col_left:
    st.subheader("A pie plot")
    st.write("") 
    st.write("View the total production of different energy groups for the year 2021 in the selected area.")
    
    price_areas = sorted(mongodb_df['priceArea'].unique())
    selected_price_area=st.radio("Select an area:",price_areas,key="price_area_radio",on_change=update_area)

    if selected_price_area:
        filtered_df_area=mongodb_df[mongodb_df["priceArea"]==selected_price_area]\
        .groupby("productionGroup").agg(total_production=("quantityKwh", "sum")).reset_index()
        
        #Creating a Plotly pie chart
        fig = px.pie(filtered_df_area,
            names="productionGroup",   
            values="total_production",  
            title=(f"Pie Plot of {selected_price_area} Production Quantity"))

        #Showing the figure
        fig.update_traces(textinfo='percent+label',textposition='outside',pull=[0.1, 0.1, 0],textfont_size=12)
        fig.update_layout(showlegend=True,margin=dict(t=50, b=50, l=50, r=50),width=700,height=700)
        #Displaying the pie chart
        st.plotly_chart(fig, use_container_width=True) 
    else:
        st.warning("Please select a price area to display the pie plot.")


#For the right side containing line plot
with col_right:
    st.subheader("A line plot")
    st.write("") 
    st.write("Visualize the production trends of selected production groups for the chosen area and month.")
    #Extracting all the production groups in a list
    production_groups=mongodb_df['productionGroup'].unique().tolist() 


    #Adding an st.pills to select multiple groups
    selected_group=st.pills("Select the production groups:",production_groups,selection_mode="multi")

    #Adding a month column extracted from startTime for easy filtering
    mongodb_df['month'] = mongodb_df['startTime'].dt.month_name()

    #Generating a list of month names using calendar.month_name
    months = list(calendar.month_name)[1:]  

    #Adding a selctbox to choose any month
    selected_month = st.selectbox("Select a month:", months)

    if selected_group:
        #Filtering data for selected price area,month and selected group and then grouping and aggregating accordingly
        filtered_df_month_group_area=mongodb_df[(mongodb_df["priceArea"]==selected_price_area)&(mongodb_df["productionGroup"].isin(selected_group))&(mongodb_df["month"]==selected_month)]
        grouped_df_month_group=filtered_df_month_group_area.groupby(["startTime","productionGroup"]).agg(total_production=("quantityKwh", "sum")).reset_index()
        
        #Plotting line chart using plotly
        fig = px.line(grouped_df_month_group,x='startTime',y='total_production',
            color='productionGroup',
            title=f"Energy Production in Area { selected_price_area} in {selected_month}",
            labels={'startTime': 'Time','total_production': 'Production (kWh)','productionGroup': 'Production Group'},template='plotly_white')

        #Customizing axes & layout
        fig.update_layout(width=1000,height=600,margin=dict(t=60, b=60, l=60, r=60),legend_title_text="Production Group")
        fig.update_xaxes(tickformat='%d-%m-%Y', tickangle=45)

        #Displaying chart in Streamlit
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one production group to display the line plot.")

#Using st.expander to show the source of data
with st.expander("See source of the data"):
    st.write("The data is taken from elhup api")
    st.markdown('[Visit the Elhub Energy Data API documentation for Price Areas](https://api.elhub.no/energy-data-api#/price-areas)',unsafe_allow_html=True)
