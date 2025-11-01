import streamlit as st
import requests_cache

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.fftpack import dct, idct
import plotly.graph_objects as go
from sklearn.neighbors import LocalOutlierFactor
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL

if "df_city" not in st.session_state:
    st.warning('Select an area and run page new_A first')
    st.stop()  # stops execution of the rest of the script

df_city=st.session_state['df_city']

# Tabs 
tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])

#Function for TAB-1
    # --- Function ---
def precipitation_anomalies_plotly(df, outlier_proportion=0.01):
        # Ensure data is in 2D shape for LOF
        precipitation = [[x] for x in df['precipitation']]

        # Apply Local Outlier Factor
        lof = LocalOutlierFactor(n_neighbors=20, contamination=outlier_proportion)
        pred_labels = lof.fit_predict(precipitation)

        outliers = pred_labels == -1
        inliers = pred_labels == 1

        # Create Plotly figure
        fig = go.Figure()

        # Plot inliers
        fig.add_trace(go.Scatter(
            x=df['date'][inliers],
            y=df['precipitation'][inliers],
            mode='markers',
            name='Inliers',
            marker=dict(color='royalblue', size=6),
            hovertemplate='Date: %{x}<br>Precipitation: %{y:.2f} mm<extra></extra>'
        ))

        # Plot outliers
        fig.add_trace(go.Scatter(
            x=df['date'][outliers],
            y=df['precipitation'][outliers],
            mode='markers',
            name='Outliers',
            marker=dict(color='red', size=8, symbol='circle-open'),
            hovertemplate='Date: %{x}<br>Outlier: %{y:.2f} mm<extra></extra>'
        ))

        # Layout
        fig.update_layout(
            title="Precipitation Anomalies Detected by LOF",
            xaxis_title="Date",
            yaxis_title="Precipitation (mm)",
            template="plotly_white",
            hovermode="closest",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )

        # Summary
        summary = f"""**Summary**  
        - Proportion of outliers: {outlier_proportion}  
        - Number of inliers: {np.sum(inliers)}  
        - Number of outliers: {np.sum(outliers)}"""

        return fig, summary

#Function for TAB-2
#Production_elhub.csv
@st.cache_data
def read_data():
    production_df= pd.read_csv(r"production_elhub.csv",
        parse_dates=['endTime','startTime','lastUpdatedTime'],
        dtype={'priceArea': 'string', 'productionGroup': 'string'})
    return production_df
production_df=read_data()

# Function for STL decomposition with Plotly
def stl_loess_plotly(production_df, priceArea='NO1', productionGroup='hydro', 
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
                             name='Residual', marker=dict(size=2,color='lightcoral')), row=4, col=1)
    
    fig.update_layout(height=900, width=900, title_text=f"STL Decomposition - {selected_area}, {selected_group}",
                      showlegend=False, template='plotly_white')
    
    return fig, res


with tab1:
    st.title("Precipitation Anomaly Detection (LOF)")
    st.write('The selected area comes from page "Energy Production" area selector', st.session_state['selected_price_area'])
    
    outlier_proportion = st.slider("Select outlier proportion", 0.001, 0.1, 0.01, step=0.01)
    fig, summary = precipitation_anomalies_plotly(df_city, outlier_proportion)
    st.plotly_chart(fig, use_container_width=True,key='tab_1')
    st.markdown(summary)

with tab2:
    st.title("STL Decomposition with Plotly")
    col1, col2 = st.columns(2)
    with col1:
        price_area=sorted(production_df['priceArea'].unique())
        default_area = st.session_state.selected_price_area
        selected_area = st.pills("Select Price Area", price_area)
        st.write('Session state area',default_area)
        if  selected_area==None:
            selected_area=default_area
        st.write('Selected area after update:',selected_area)
    with col2:
        production_group=sorted(production_df['productionGroup'].unique())
        default_group='hydro'
        default_index_group=production_group.index(default_group) if default_group in production_group else 0
        selected_group = st.selectbox("Select Production Group", production_group,index=default_index_group)

    fig2,res2=stl_loess_plotly(production_df, priceArea=selected_area, productionGroup=selected_group )
    st.plotly_chart(fig2, use_container_width=True,key="tab_2")
    