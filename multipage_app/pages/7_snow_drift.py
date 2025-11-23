import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import openmeteo_requests
from datetime import date, datetime
import requests_cache
from retry_requests import retry
import plotly.express as px
import plotly.graph_objects as go

# Code source: Provided by Sir (IND-320)

# Setup Open-Meteo API client with cache and retry
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

st.set_page_config(page_title="Annual Snow Drift Analysis", layout="wide")

# Helper Functions 

def compute_Qupot(hourly_wind_speeds, dt=3600):
    return sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847

def sector_index(direction):
    return int(((direction + 11.25) % 360) // 22.5)

def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
    sectors = [0.0] * 16
    for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
        idx = sector_index(d)
        sectors[idx] += ((u ** 3.8) * dt) / 233847
    return sectors

def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds, dt=3600):
    Qupot = compute_Qupot(hourly_wind_speeds, dt)
    Qspot = 0.5 * T * Swe
    Srwe = theta * Swe
    if Qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall controlled"
    else:
        Qinf = Qupot
        control = "Wind controlled"
    Qt = Qinf * (1 - 0.14 ** (F / T))
    return {"Qupot (kg/m)": Qupot, "Qspot (kg/m)": Qspot, "Srwe (mm)": Srwe,
            "Qinf (kg/m)": Qinf, "Qt (kg/m)": Qt, "Control": control}

def compute_yearly_results(df, T, F, theta):
    results_list = []
    df['year'] = df['time'].dt.year
    years = sorted(df['year'].unique())
    for y in years:
        start = pd.Timestamp(year=y, month=7, day=1)
        end = pd.Timestamp(year=y+1, month=6, day=30, hour=23, minute=59)
        df_season = df[(df['time'] >= start) & (df['time'] <= end)]
        if df_season.empty:
            continue
        df_season = df_season.copy()
        df_season['Swe_hourly'] = df_season.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1
        )
        total_Swe = df_season['Swe_hourly'].sum()
        wind_speeds = df_season['wind_speed_10m'].tolist()
        result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
        result["snow_year"] = f"July {y} – June {y+1}"
        results_list.append(result)
    return pd.DataFrame(results_list)

def compute_average_sector(df):
    sectors_list = []
    df['year'] = df['time'].dt.year
    years = sorted(df['year'].unique())
    
    for y in years:
        start = pd.Timestamp(year=y, month=7, day=1)
        end = pd.Timestamp(year=y+1, month=6, day=30, hour=23, minute=59)
        
        df_season = df[(df['time'] >= start) & (df['time'] <= end)]
        if df_season.empty:
            continue
        
        df_season = df_season.copy()
        df_season['Swe_hourly'] = df_season.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1
        )
        ws = df_season['wind_speed_10m'].tolist()
        wdir = df_season['wind_direction_10m'].tolist()
        sectors_list.append(compute_sector_transport(ws, wdir))
    
    avg_sectors = np.mean(sectors_list, axis=0)
    return avg_sectors

def plot_rose_plotly(avg_sector_values, overall_avg):
    num_sectors = 16
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    
    values_tonnes = np.array(avg_sector_values) / 1000.0
    
    fig = go.Figure(go.Barpolar(
        r=values_tonnes,
        theta=np.arange(0, 360, 360/num_sectors),
        width=[360/num_sectors]*num_sectors,
        marker_color='skyblue',
        marker_line_color='black',
        marker_line_width=1,
        opacity=0.8
    ))
    
    fig.update_layout(
        title=f"Average Directional Distribution of Snow Transport<br>Overall Average Qt: {overall_avg/1000:.1f} tonnes/m",
        polar=dict(
            angularaxis=dict(
                tickmode='array',
                tickvals=np.arange(0, 360, 22.5),
                ticktext=directions,
                direction='clockwise',
                rotation=90
            ),
            radialaxis=dict(title='Qt (tonnes/m)')
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

#API Call for 1 July to 30 June
@st.cache_data(show_spinner=False)
def get_weather_api(lat, lon, year):
    start_date = f"{year}-07-01"
    end_date = f"{year+1}-06-30"
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m","wind_gusts_10m", "wind_direction_10m"],
        "models": "era5"
    }
    response = openmeteo.weather_api(url, params=params)[0]
    hourly = response.Hourly()
    
    hourly_data = {
        "time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True).tz_convert(None),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True).tz_convert(None),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "precipitation": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
        "wind_gusts_10m": hourly.Variables(3).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(4).ValuesAsNumpy(),
    }

    df = pd.DataFrame(hourly_data)
    return df

# STREAMLIT UI

st.title("Snow Drift Analysis ")

if "clicked_points" not in st.session_state or not st.session_state.clicked_points:
    st.warning("Please select a point on the map first.")
    if st.button("➡️ Go to Maps Page"):
        st.session_state["section"] = "Energy"
        st.session_state["subgroup"] = "Visualization"
        st.session_state["page_name"] = "Maps"
        st.rerun()
    
else:
    last_point = st.session_state.clicked_points[-1]
    lat = last_point["lat"]
    lon = last_point["lon"]

    year_range = st.slider("Select year range for analysis (start years):",  
                           min_value=2000, max_value=2024, value=(2010, 2012))

    snow_data_list = []
    for y in range(year_range[0], year_range[1]):
        df_year = get_weather_api(lat, lon, y)
        snow_data_list.append(df_year)
        st.success(f"Data for snow year {y}-{y+1} loaded successfully")
    
    if snow_data_list:
        df_all = pd.concat(snow_data_list, ignore_index=True)

        T = 3000
        F = 30000
        theta = 0.5

        # YEARLY SNOW DRIFT
        yearly_results = compute_yearly_results(df_all, T, F, theta)

        st.subheader("Snow Drift per Year")
        yearly_results_display = yearly_results[["snow_year", "Qt (kg/m)", "Control"]].copy()
        yearly_results_display["Qt (tonnes/m)"] = yearly_results_display["Qt (kg/m)"] / 1000

        fig = px.bar(
            yearly_results_display,
            x="snow_year",
            y="Qt (tonnes/m)",
            text="Qt (tonnes/m)",
            title="Snow Drift per Year",
            labels={"snow_year": "Snow Year", "Qt (tonnes/m)": "Qt (tonnes/m)"}
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        y_max = yearly_results_display["Qt (tonnes/m)"].max() * 1.1 
        fig.update_yaxes(range=[0, y_max])
        st.plotly_chart(fig, use_container_width=False)

        # MONTHLY SNOW DRIFT (COMBINED)
        def compute_monthly_results(df, T, F, theta):
            df = df.copy()
            df["month"] = df["time"].dt.month
            df["year"] = df["time"].dt.year

            df["snow_season_year"] = df.apply(
                lambda r: r["year"] - 1 if r["month"] <= 6 else r["year"], axis=1)

            monthly_results = []

            for (season_year, month), df_month in df.groupby(["snow_season_year", "month"]):
                df_month = df_month.copy()
                df_month["Swe_hourly"] = df_month.apply(
                    lambda row: row["precipitation"] if row["temperature_2m"] < 1 else 0,
                    axis=1)
                total_Swe = df_month["Swe_hourly"].sum()
                wind_speeds = df_month["wind_speed_10m"].tolist()
                result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)

                month_name = pd.to_datetime(str(month), format="%m").strftime("%B")
                result["Period"] = f"{month_name} {season_year}"
                result["Qt (tonnes/m)"] = result["Qt (kg/m)"] / 1000
                result["Type"] = "Monthly"

                monthly_results.append(result)

            return pd.DataFrame(monthly_results)

        monthly_results = compute_monthly_results(df_all, T, F, theta)

        # Prepare yearly drift for combined plot
        yearly_for_combined = yearly_results_display.rename(
            columns={"snow_year": "Period", "Qt (tonnes/m)": "Qt (tonnes/m)"}
        )[["Period", "Qt (tonnes/m)"]].copy()
        yearly_for_combined["Type"] = "Yearly"

        # Combine
        combined_df = pd.concat([
            yearly_for_combined,
            monthly_results[["Period", "Qt (tonnes/m)", "Type"]]
        ])

        # Sort in correct chronological order
        def sorter(period):
            try:
                parts = period.split()
                if len(parts) == 3:
                    # "July year start – June year end"
                    return pd.to_datetime(parts[1], format="%Y")
                else:
                    return pd.to_datetime(f"{parts[0]} 1 {parts[1]}")
            except:
                return pd.Timestamp.now()

        combined_df["SortIndex"] = combined_df["Period"].apply(sorter)
        combined_df = combined_df.sort_values("SortIndex")

        # Combined plot
        st.subheader(f" Monthly + Yearly Snow Drift for Year Range {year_range}")
        fig_combined = px.bar(
            combined_df,
            x="Period",
            y="Qt (tonnes/m)",
            color="Type",
            barmode="group",
            title="Monthly + Yearly Snow Drift",
            labels={"Period": "Time Period", "Qt (tonnes/m)": "Qt (tonnes/m)"})
        fig_combined.update_layout(xaxis=dict(tickangle=45))
        st.plotly_chart(fig_combined, use_container_width=True)

        # WIND ROSE
        avg_sectors = compute_average_sector(df_all)
        overall_avg = yearly_results["Qt (kg/m)"].mean()

        st.subheader("Average Directional Distribution (Wind Rose)")
        plot_rose_plotly(avg_sectors, overall_avg)
