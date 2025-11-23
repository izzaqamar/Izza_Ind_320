import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
import folium
import geopandas as gpd
from shapely.geometry import Point
from streamlit_folium import st_folium
import numpy as np

from utils import get_production_data, get_consumption_data

# Load GeoJSON 
@st.cache_data
def load_geojson(path):
    gdf = gpd.read_file(path)
    gdf = gdf.to_crs(epsg=4326)
    return gdf

geojson_path = r"D:\NMBU\semester_1\IND-320\Izza_Ind_320\multipage_app\pages\maps_area.geojson"
gdf = load_geojson(geojson_path)

#Initialize session state for clicks
if "clicked_points" not in st.session_state:
    st.session_state.clicked_points = []
if "selected_area" not in st.session_state:
    st.session_state.selected_area = None
if "energy_type" not in st.session_state:
    st.session_state.energy_type = None



# Title
st.markdown(" ## Norwegian Elspot Price Areas (Energy Data 2021–2024)")
st.markdown("Click on the map to store coordinates and highlight the corresponding Price Area.")

# Columns for map and data type
col1, col2 = st.columns([2, 1])

#Base map (single instance) 
m = folium.Map(location=[65, 15], zoom_start=4)

# Add GeoJSON outlines
folium.GeoJson(
    gdf,
    name="Price Area Outlines",
    style_function=lambda feature: {
        'fillColor': 'transparent',
        'color': 'blue',
        'weight': 3,
        'fillOpacity': 0.0
    },
    tooltip=folium.GeoJsonTooltip(fields=["ElSpotOmr"], aliases=["Price Area"])
).add_to(m)

# Highlight selected Price Area
if st.session_state.selected_area:
    selected_gdf = gpd.GeoDataFrame(geometry=[st.session_state.selected_area], crs="EPSG:4326")
    folium.GeoJson(
        selected_gdf,
        name="Selected Area Outline",
        style_function=lambda feature: {
            'fillColor': 'transparent',
            'color': 'cyan',
            'weight': 5,
            'fillOpacity': 0.1
        }
    ).add_to(m)

# Add markers for stored points
for point in st.session_state.clicked_points:
    folium.Marker(
        location=[point["lat"], point["lon"]],
        popup=point["area"]
    ).add_to(m)

#Controls in right column
with col2:
    energy_type = st.radio("Select a data type to visualize on the choropleth map:", ["Energy Production", "Energy Consumption"], index=None)

    if energy_type:
        st.session_state.energy_type = energy_type
        # Load data based on selection
        if energy_type == "Energy Production":
            df = get_production_data()
            group_col = "productionGroup"
        else:
            df = get_consumption_data()
            group_col = "consumptionGroup"

        if not df.empty:
            available_groups = df[group_col].dropna().unique().tolist()
            selected_groups = st.multiselect("Select energy group(s)", options=available_groups, default=available_groups)
            group_df = df[df[group_col].isin(selected_groups)]

            if not group_df.empty:
                min_date = group_df["startTime"].min()
                max_date = group_df["startTime"].max()
                max_span_days = max((max_date - min_date).days, 1)

                days_interval = st.number_input(
                    "Enter time interval (days)",
                    min_value=1,
                    max_value=max_span_days,
                    value=min(30, max_span_days),
                    step=30 if max_span_days >= 30 else 1
                )
                end_date = max_date
                start_date = end_date - timedelta(days=int(days_interval))

                filtered_df = group_df[
                    (group_df["startTime"] >= start_date) &
                    (group_df["startTime"] <= end_date)
                ]
                st.write("Selected interval:", start_date, "to", end_date)
                if not filtered_df.empty:
                    mean_values = (
                        filtered_df.groupby("priceArea")["quantityKwh"]
                        .mean()
                        .reset_index()
                    )
                    gdf = gdf.copy()
                    gdf["join_key"] = gdf["ElSpotOmr"].str.replace(" ", "")
                    gdf = gdf.merge(mean_values, left_on="join_key", right_on="priceArea", how="left")

                    bins = list(np.linspace(mean_values["quantityKwh"].min(),
                                            mean_values["quantityKwh"].max(), 6))

                    folium.Choropleth(
                        geo_data=gdf,
                        name="Energy Choropleth",
                        data=mean_values,
                        columns=["priceArea", "quantityKwh"],
                        key_on="feature.properties.join_key",
                        fill_color="YlOrRd",
                        fill_opacity=0.6,
                        line_opacity=0.8,
                        legend_name="Mean Energy (kWh)",
                        nan_fill_color="transparent",
                        bins=bins,
                        legend_position="bottomright"
                    ).add_to(m)

                    folium.GeoJson(
                        gdf,
                        name="Price Area Tooltip",
                        style_function=lambda feature: {
                            'fillColor': 'transparent',
                            'color': 'blue',
                            'weight': 1,
                            'fillOpacity': 0.0
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=["ElSpotOmr", "quantityKwh"],
                            aliases=["Price Area", "Mean kWh"],
                            labels=True,
                            sticky=True,
                            style="background-color: white; color: #333; font-size: 12px; padding: 5px;"
                        )
                    ).add_to(m)

# Render map once in left column so we can add choropleth
with col1:
    map_data = st_folium(m, width=700, height=500)

    # Capture click
    if map_data and map_data.get("last_clicked"):
        latlon = map_data["last_clicked"]
        lat, lon = latlon["lat"], latlon["lng"]
        clicked_point = Point(lon, lat)

        match = gdf[gdf.contains(clicked_point)]
        area_name = match.iloc[0]["ElSpotOmr"] if not match.empty else "Outside defined areas"
        selected_geom = match.iloc[0].geometry if not match.empty else None

        st.session_state.clicked_points.append({"lat": lat, "lon": lon, "area": area_name})
        st.session_state.selected_area = selected_geom
        st.rerun()

    # Show clicked points
    if st.session_state.clicked_points:
        st.subheader("Clicked Coordinates and Areas")
        for i, pt in enumerate(st.session_state.clicked_points, 1):
            st.write(f"{i}. Latitude: {pt['lat']:.5f}, Longitude: {pt['lon']:.5f} → Area: **{pt['area']}**")