import streamlit as st
import pandas as pd
import numpy as np
from scipy.fftpack import dct, idct
import plotly.graph_objects as go
from sklearn.neighbors import LocalOutlierFactor
import scipy.stats as stats

from utils import DATA,api_call, get_coords_by_price_code, area_name

st.markdown(' ## Outlier and Anomaly Detection in Weather Data ')
st.text('This page presents temperature values that fall outside expected ranges and ' \
'precipitation patterns that deviate from typical conditions. Select year (2000-2024) and area to explore')

col_a,col_b=st.columns(2)
with col_a:
    year = st.number_input(
        "Select year",
        min_value=2000,
        max_value=2024,
        value=2021,
        step=1)

with col_b:
# Let the user select a Price Area by city name
    selected_price_area = st.selectbox("Select a Price Area:",
        options=[info["PriceAreaCode"] for info in DATA.values()],
        format_func=lambda code: area_name(code) )


# Get coordinates from utils
coords = get_coords_by_price_code(selected_price_area)

# Call the API
df_city = api_call(coords, year)

#Contains tab-1: Temp-Outlier/SPC analysis   tab-2:Precipitation-Anomaly/LOF analysis
# Tabs 
tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])

### TAB-1 FUNCTION ###

# Temperature outliers function using df_city
# dct_cutoff_hours: Default for weekly values
def temp_outliers(df_city, dct_cutoff_hours=168, n_std=3):
    # Original temperature converted to numpy array to pass to DCT
    temp = df_city['temperature_2m'].to_numpy(dtype=float)
    dates = pd.to_datetime(df_city['date'])

    # DCT type 2
    N = len(temp)
    temp_dct = dct(temp, type=2, norm='ortho')

    # Computing sampling interval automatically from timestamps
    sampling_interval_hours = (dates[1] - dates[0]).total_seconds() / 3600.0

    # Cutoff index mapping
    k_cut = int((N * sampling_interval_hours) / dct_cutoff_hours)

    # High-pass filtering and SATV
    temp_dct_hp = temp_dct.copy()
    temp_dct_hp[:k_cut] = 0
    temp_satv = idct(temp_dct_hp, type=2, norm='ortho')

    # Robust statistics using MAD
    median_val = np.median(temp_satv)
    mad = np.median(np.abs(temp_satv - median_val))
    robust_std_val = 1.4826 * mad

    # SPC boundaries
    upper_bound = median_val + n_std * robust_std_val
    lower_bound = median_val - n_std * robust_std_val

    # Identify outliers beyond the SPC boundaries
    outliers_mask = (temp_satv > upper_bound) | (temp_satv < lower_bound)

    # Low frequency DCT to plot boundaries
    temp_dct_low = temp_dct.copy()
    temp_dct_low[k_cut:] = 0
    temp_lowfreq = idct(temp_dct_low, type=2, norm='ortho')

    upper_thresh_orig = temp_lowfreq + upper_bound
    lower_thresh_orig = temp_lowfreq + lower_bound

    # Plotting
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=temp,
        mode='lines', name='Temperature', line=dict(color='royalblue')))
    fig.add_trace(go.Scatter(x=dates[outliers_mask], y=temp[outliers_mask],
        mode='markers', name='Outliers', marker=dict(color='red', size=5)))
    fig.add_trace(go.Scatter(x=dates, y=upper_thresh_orig,
        mode='lines', name='Upper SPC Boundary',
        line=dict(color='orange', dash='dashdot')))
    fig.add_trace(go.Scatter(x=dates, y=lower_thresh_orig,
        mode='lines', name='Lower SPC Boundary',
        line=dict(color='orange', dash='dashdot')))

    fig.update_layout(title="Temperature with SPC Outliers (MAD-based)",
        xaxis_title="Date", yaxis_title="Temperature (°C)",
        legend=dict(x=0.01, y=0.99), template='plotly_white',
        height=500, width=900)

    # Summary
    summary = f"""**Summary**  
    - Number of inliers: {N - np.sum(outliers_mask)}  
    - Number of outliers: {np.sum(outliers_mask)}"""

    return fig, summary


#Function for TAB-2
    # Define function for anoamilies in precipiation 
    #Keeps local seasonality effects when n= 10--30

def precipitation_anomalies(df,n_neighbors=20, outlier_proportion=0.01):
        # Data is in 2D shape for LOF
        precipitation = [[x] for x in df['precipitation']]

        # Apply Local Outlier Factor
        lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=outlier_proportion)
        pred_labels = lof.fit_predict(precipitation)

        outliers = pred_labels == -1
        inliers = pred_labels == 1

        # Create Plotly figure
        fig = go.Figure()

        # Plot inliers
        fig.add_trace(go.Scatter(x=df['date'][inliers], y=df['precipitation'][inliers],
            mode='markers',name='Inliers',marker=dict(color='royalblue', size=6),
            hovertemplate='Date: %{x}<br>Precipitation: %{y:.2f} mm<extra></extra>'))

        # Plot outliers
        fig.add_trace(go.Scatter(x=df['date'][outliers],y=df['precipitation'][outliers],
            mode='markers',name='Outliers',marker=dict(color='red', size=8, symbol='circle-open'),
            hovertemplate='Date: %{x}<br>Outlier: %{y:.2f} mm<extra></extra>'))

        # Layout
        fig.update_layout(title="Precipitation Anomalies Detected by LOF",xaxis_title="Date",
            yaxis_title="Precipitation (mm)",template="plotly_white",
            hovermode="closest",legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))

        # Summary
        summary = f"""**Summary**  
        - Proportion of outliers: {outlier_proportion}  
        - Number of inliers: {np.sum(inliers)}  
        - Number of outliers: {np.sum(outliers)}"""
        return fig, summary

with tab1:
    st.markdown('### Temperature Outliers (SATV)')
    col1,col2=st.columns(2)
    with col1:
        #Add a number input UI element to select standard deviation
        n_std=st.number_input("Select standard deviation:",min_value= 1, max_value=5,value= 3, step=1)
    with col2:
        #Add a number input UI element to select cutoff period
        cutoff_hours = st.number_input("Select cutoff period (hours):",
        min_value=24,max_value=2160,   # up to ~3 months
        value=168,         # default = 1 week
        step=24)           # change in 1-day increments

    #Call function
    fig,summary = temp_outliers(df_city, dct_cutoff_hours=cutoff_hours, n_std=n_std) #default value is 3 from slider
    st.plotly_chart(fig, use_container_width=True,)
    st.write(summary)

with tab2:
    st.markdown("### Precipitation Anomaly Detection (LOF)")
    col1,col2=st.columns(2)
    with col1:
        #Add a slider to select outlier proportion
        outlier_proportion = st.slider("Select outlier proportion:", 0.001, 0.1, 0.01, step=0.01)
    with col2:
        #Add a slider to select n_neighbors
        n_neighbors=st.slider("Select number of neighbors:",10,40,20,step=5)
    #Call function
    fig, summary = precipitation_anomalies(df_city,n_neighbors, outlier_proportion)
    st.plotly_chart(fig, use_container_width=True,key='tab_1')
    st.write(summary)

