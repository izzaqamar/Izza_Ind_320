import streamlit as st
import requests_cache
from retry_requests import retry
from datetime import date
import openmeteo_requests
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.fftpack import dct, idct
import plotly.graph_objects as go
import matplotlib.dates as mdates
from scipy.signal import stft


#Initializing the session state
if "selected_price_area" not in st.session_state:
    st.session_state.selected_price_area = 'NO1'
st.write("The analysis is for selected area:", (st.session_state.selected_price_area))
st.write("SESSION ID:", id(st.session_state))

data={
 'Oslo': {'PriceAreaCode': 'NO1', 'Longitude': 10.7461, 'Latitude': 59.9127},
 'Kristiansand': {'PriceAreaCode': 'NO2', 'Longitude': 7.9956, 'Latitude': 58.1467},
 'Trondheim': {'PriceAreaCode': 'NO3', 'Longitude': 10.3951, 'Latitude': 63.4305},
 'Tromsø': {'PriceAreaCode': 'NO4', 'Longitude': 18.9551, 'Latitude': 69.6489},
 'Bergen': {'PriceAreaCode': 'NO5', 'Longitude': 5.32415, 'Latitude': 60.39299}}

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def api_call(coords,year):
    Latitude,Longitude=coords
    start_date=date(year, 1, 1).strftime("%Y-%m-%d")
    end_date=date(year, 12, 31).strftime("%Y-%m-%d")
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": Latitude,
        "longitude": Longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"],
        "models": "era5",
    }
    responses = openmeteo.weather_api(url, params=params)
    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    st.write(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    #st.write(f"Elevation: {response.Elevation()} m asl")
    #st.write(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")
    #print(f"Response:{response}")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    hourly_wind_gusts_10m = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    #print("\nHourly_data\n", hourly_dataframe)
    return hourly_dataframe

#Returns (Latitude, Longitude) for a given PriceAreaCode.
def get_coords_by_price_code(selected_city_code):
    for _, info in data.items():
        if info['PriceAreaCode'] == selected_city_code:
            return info['Latitude'], info['Longitude']

# Only call API if data not already in session
if "df_city" not in st.session_state:
    selected_city_code = st.session_state.selected_price_area
    coords = get_coords_by_price_code(selected_city_code)
    year = 2021
    df_city = api_call(coords, year)
    
    # Dropping UTC
    df_city['date'] = df_city['date'].dt.tz_localize(None)
    # Save in session state
    st.session_state.df_city = df_city
else:
    # Retrieve from session state
    df_city = st.session_state.df_city

### TAB-1 FUNCTION ###

# Temperature outliers function using df_city
def temp_outliers(df_city, dct_cutoff_hours=168, n_std=3):
    # Original temperature converted to numpy array to pass to DCT
    temp = df_city['temperature_2m'].to_numpy(dtype=float)
    dates = pd.to_datetime(df_city['date'])

    # DCT type 2
    N = len(temp)
    temp_dct = dct(temp, type=2, norm='ortho')

    # Cutoff (default: weekly)
    k_cut = int(2 * N / dct_cutoff_hours)

    # High-pass filtering and SATV
    temp_dct_hp = temp_dct.copy()
    temp_dct_hp[:k_cut] = 0
    temp_satv = idct(temp_dct_hp, type=2, norm='ortho')

    # SATV robust SPC boundaries
    import scipy.stats as stats
    trim_proportion = 0.05
    trimmed_mean_val = stats.trim_mean(temp_satv, trim_proportion)
    sorted_data = np.sort(temp_satv)
    cut = int(trim_proportion * N)
    trimmed_std_val = np.std(sorted_data[cut:N-cut], ddof=0)

    upper_bound = trimmed_mean_val + n_std * trimmed_std_val
    lower_bound = trimmed_mean_val - n_std * trimmed_std_val

    outliers_mask = (temp_satv > upper_bound) | (temp_satv < lower_bound)

    temp_dct_low = temp_dct.copy()
    temp_dct_low[k_cut:] = 0  
    temp_lowfreq = idct(temp_dct_low, type=2, norm='ortho')

    upper_thresh_orig = temp_lowfreq + upper_bound
    lower_thresh_orig = temp_lowfreq + lower_bound

    #Plotting
    fig=go.Figure()
    
    #Plot temperature
    fig.add_trace(go.Scatter(x=dates,y=temp,
        mode='lines',name='Temperature',line=dict(color='royalblue')))
    
    # Scatter for outliers
    fig.add_trace(go.Scatter(x=dates[outliers_mask], y=temp[outliers_mask],
        mode='markers',name='Outliers',marker=dict(color='red', size=5)))
    
    # Upper threshold
    fig.add_trace(go.Scatter(x=dates,y=upper_thresh_orig,
        mode='lines',name='Upper SATV Boundary',
        line=dict(color='orange', dash='dashdot')))
    
    # Lower threshold
    fig.add_trace(go.Scatter(x=dates,y=lower_thresh_orig,
        mode='lines',name='Lower SATV Boundary',
        line=dict(color='orange', dash='dashdot')))
    
    # Layout
    fig.update_layout(title="Temperature with SATV-based Outliers",
        xaxis_title="Date",yaxis_title="Temperature (°C)",
        legend=dict(x=0.01, y=0.99),template='plotly_white',
        height=500,width=900)
    #Summary
    summary = f"""Summary 
    --Number of outliers: {np.sum(outliers_mask)}
    --Number of inliers: {N - np.sum(outliers_mask)}"""
    return fig,summary

### Function for TAB-2 ###
## DATA IMPORTING ##
#Production_elhub.csv
@st.cache_data
def read_data():
    production_df= pd.read_csv(r"production_elhub.csv",
        parse_dates=['endTime','startTime','lastUpdatedTime'],
        dtype={'priceArea': 'string', 'productionGroup': 'string'})
    return production_df
production_df=read_data()

def plot_hourly_spectrogram(priceArea='NO1', productionGroup='hydro',
                            window_length=168, window_overlap=84, cmap='viridis'):
    df_spectogram = production_df.copy()
    if priceArea is not None:
        df_spectogram = df_spectogram[df_spectogram['priceArea'] == priceArea]
    if productionGroup is not None:
        df_spectogram = df_spectogram[df_spectogram['productionGroup'] == productionGroup]
        
    df_spectogram = df_spectogram.set_index('startTime')
    data = df_spectogram["quantityKwh"].to_numpy()
    time_index = df_spectogram.index
    fs = 24      # samples per day

    # Compute STFT
    f, t, Zxx = stft(data, fs=fs, nperseg=window_length, noverlap=window_overlap)
    t_dates = time_index[0] + pd.to_timedelta(t, unit='D')
    magnitude = np.abs(Zxx)
    log_magnitude = np.log1p(magnitude)

    # Plot
    fig, axs = plt.subplots(2, 1, figsize=(14, 8))
    axs[0].plot(time_index, data)
    axs[0].set_xlim(time_index[0], time_index[-1])
    axs[0].set_ylabel('Quantity(kwh)')
    axs[0].set_title('Production Quantity Over Time')

    pcm1 = axs[1].pcolormesh(t_dates, f, log_magnitude, shading='gouraud', vmin=1, vmax=15, cmap=cmap)
    axs[1].set_ylabel('Frequency [Hz]')
    axs[1].set_xlabel('Date')
    axs[1].set_title('STFT Spectrogram')
    fig.colorbar(pcm1, ax=axs[1], label='Amplitude [log1p]')

    # Format x-axis with months
    axs[1].xaxis.set_major_locator(mdates.MonthLocator())
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(axs[1].xaxis.get_majorticklabels(), rotation=45)

    return fig


# Creating tabs 
tabs = st.tabs(["Tab-1","Tab-2"])
with tabs[0]:
    col1,col2=st.columns(2)
    with col1:
        n_std=st.slider("Select standard deviation", 1, 5, 3, step=1)
    with col2:
        #make a dict for weekly,monthly cutoff hours and pass here
        st.write('waiting to be completed')
    fig,summary = temp_outliers(df_city, dct_cutoff_hours=168, n_std=n_std)#default value is 3 from slider
    st.plotly_chart(fig, use_container_width=True,)
    st.text(summary)

with tabs[1]:
    st.write('This is new tab-2')
    st.title("Hourly Production Spectrogram")
    window_length = st.slider("Window length (hours)", 24, 336, 168, step=24)
    window_overlap = st.slider("Window overlap (hours)", 0, window_length - 1, 84, step=12)
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
    # Generate figure
    fig = plot_hourly_spectrogram(
    priceArea=selected_area,
    productionGroup=selected_group,
    window_length=window_length,
    window_overlap=window_overlap)

    # Display figure in Streamlit
    st.pyplot(fig)

