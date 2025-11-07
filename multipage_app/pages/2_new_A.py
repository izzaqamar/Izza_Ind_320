import streamlit as st
import matplotlib.dates as mdates
from scipy.signal import stft
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL

###Contains tab-1:STL analysis and tab-2:Spectrogram

#Production_elhub.csv
@st.cache_data
def read_data():
    production_df= pd.read_csv(r"production_elhub.csv",
        parse_dates=['endTime','startTime','lastUpdatedTime'],
        dtype={'priceArea': 'string', 'productionGroup': 'string'})
    return production_df
production_df=read_data()

st.title('Data from production-elhub.csv')

### TAB-1 FUNCTION ###

# Function for STL decomposition with Plotly
def stl_loess(production_df, priceArea='NO1', productionGroup='hydro', 
                     period=720, seasonal_smoother=723, trend_smoother=723, robust=True):
    
    # Filter dataframe
    df = production_df.copy()
    if priceArea is not None:
        df = df[df['priceArea'] == priceArea]
    if productionGroup is not None:
        df = df[df['productionGroup'] == productionGroup]

    # Set datetime index
    df = df.set_index('startTime')
    
    # Run STL
    stl = STL(df["quantityKwh"], period=period, seasonal=seasonal_smoother, 
              trend=trend_smoother, robust=robust)
    res = stl.fit()
        
    # Compute residual outliers (3-sigma rule)
    threshold = 3 * np.std(res.resid)
    outliers = (res.resid > threshold) | (res.resid < -threshold)
    
    # Prepare Plotly subplots: 4 rows, 1 column
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05,
                        subplot_titles=["Original", "Trend", "Seasonal", "Residual"])
    
    # Original
    fig.add_trace(go.Scatter(x=df.index, y=df["quantityKwh"], mode='lines', 
                             name='Original', line=dict(color='blue')), row=1, col=1)
    # Trend
    fig.add_trace(go.Scatter(x=df.index, y=res.trend, mode='lines', 
                             name='Trend', line=dict(color='orange')), row=2, col=1)
    # Seasonal
    fig.add_trace(go.Scatter(x=df.index, y=res.seasonal, mode='lines', 
                             name='Seasonal', line=dict(color='green')), row=3, col=1)
    # Residual
    fig.add_trace(go.Scatter(x=df.index, y=res.resid, mode='markers', 
                             name='Residual', marker=dict(size=2,color='coral')), row=4, col=1)
    
    fig.update_layout(height=900, width=900, title_text=f"STL Decomposition - {selected_area}, {selected_group}",
                      showlegend=False, template='plotly_white')
    
    #Information regarding STL decomposition
    info = { 
    "original":df["quantityKwh"].describe(),
    "trend_stats": res.trend.describe(),
    "seasonal_stats": res.seasonal.describe(),
    "residual_stats": res.resid.describe(),
    "num_residual_outliers": outliers.sum(),
    "data_length": len(df)}
    return fig, res,info

### Function for TAB-2 ###

#Defining function to compute spectogram 
def plot_spectrogram(priceArea='NO1', productionGroup='hydro',
                            window_length=168, window_overlap=84):
    df_spectogram = production_df.copy()
    if priceArea is not None:
        df_spectogram = df_spectogram[df_spectogram['priceArea'] == priceArea]
    if productionGroup is not None:
        df_spectogram = df_spectogram[df_spectogram['productionGroup'] == productionGroup]
        
    df_spectogram = df_spectogram.set_index('startTime')
    data = df_spectogram["quantityKwh"].to_numpy()
    time_index = df_spectogram.index
    fs = 24     

    # Compute STFT
    f, t, Zxx = stft(data, fs=fs, nperseg=window_length, noverlap=window_overlap)
    
    #For x-axis to be in proper time format
    t_dates = time_index[0] + pd.to_timedelta(t, unit='D')
    magnitude = np.abs(Zxx)
    log_magnitude = np.log1p(magnitude)

    #  Plotly subplots
    fig = make_subplots(rows=2, cols=1,
        shared_xaxes=True,vertical_spacing=0.08,
        subplot_titles=("Production Quantity Over Time", "STFT Spectrogram"))

    # Actual data plot
    fig.add_trace(go.Scatter(x=time_index, y=data, mode='lines', name='Quantity (kWh)'),
        row=1, col=1)

    # Spectrogram heatmap
    fig.add_trace(go.Heatmap(
            x=t_dates,y=f,z=log_magnitude,
            colorscale='Viridis',colorbar=dict(title='Amplitude')),
        row=2, col=1)

    # Update layout
    fig.update_layout(height=800,
        title_text='Production Data and STFT Spectrogram',)
    
    fig.update_xaxes(tickformat='%Y-%m',
        tickangle=45)
    
    fig.update_yaxes(title_text='Quantity (kWh)', row=1, col=1)
    fig.update_yaxes(title_text='Frequency [Hz]', row=2, col=1)
    
    return fig

st.write('Session state area:',st.session_state.selected_price_area)

#Coulmns common to both tabs to add UI elements
col1,col2=st.columns(2)
with col1:
    price_area=sorted(production_df['priceArea'].unique())
    default_area = st.session_state.selected_price_area
    #Add st.pills so user can update area from session state area.
    selected_area = st.pills("Select Price Area", price_area)
    if  selected_area==None:
        selected_area=default_area
    st.write('Selected area for this page only:',selected_area)
with col2:
    production_group=sorted(production_df['productionGroup'].unique())
    default_group='hydro'
    default_index_group=production_group.index(default_group) if default_group in production_group else 0
    #Add selectbox for user to select production group
    selected_group = st.selectbox("Select Production Group", production_group,index=default_index_group)


# Creating tabs 
tab1,tab2 = st.tabs(["Tab-1","Tab-2"])

with tab1:
    st.markdown("### STL Decomposition for Quantity(Kwh)")
    col1,col2=st.columns(2)
    with col1:
        # Input from user
        period_hours = st.number_input("Seasonal Period (hours)", 
        min_value=168,          # minimum 1 week
        max_value=2160,         #max 3 months
        value=720,             # default 1 month
        step=24 )              # step = 1 week
        seasonal_smoother = period_hours + 3   # adjust for better seasonal smoothing
        trend_smoother = period_hours + 3      # adjust for trend smoothing
        
    with col2:
        #User to select robust measure to see difference.Radio button with True as default
        selected_robust = st.radio("Select robust option:",[True, False],index=1  )

    #Function call
    fig1,res1,info=stl_loess(production_df, priceArea=selected_area, productionGroup=selected_group, 
                     period=period_hours, seasonal_smoother=seasonal_smoother, trend_smoother=trend_smoother, robust=selected_robust )
    st.plotly_chart(fig1, use_container_width=True)
    st.write('Summary',info)

with tab2:
    st.markdown("### Spectrogram for Production Quantity")
    #MAking column within tab to add UI elements
    col1,col2=st.columns(2)
    with col1:
        #Input from user
        window_length = st.number_input( "Window length (hours)",
        min_value=24,max_value=336,value=168,step=24)
    with col2:
        # Set a safe default for overlap
        default_overlap = min(84, window_length // 2)
        #Input from user
        window_overlap = st.number_input("Window overlap (hours)",min_value=0,
        max_value=window_length - 1,  # dynamically limits overlap to less than window length
        value=default_overlap,step=12)

    #Function call
    fig1 = plot_spectrogram(priceArea=selected_area,productionGroup=selected_group,window_length=window_length,window_overlap=window_overlap)
    # Display figure in Streamlit
    st.plotly_chart(fig1, use_container_width=True)
