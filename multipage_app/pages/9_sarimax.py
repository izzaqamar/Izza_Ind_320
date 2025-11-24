import streamlit as st
import pandas as pd
import pymongo
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go

from utils import get_production_data, get_consumption_data


# STREAMLIT UI
st.header("Dynamic SARIMAX Forecasts for Energy Data(2021-2024)")

#  Dataset + Target type side by side
colA, colB = st.columns(2)
with colA:
    data_type = st.radio("Dataset",["Production", "Consumption"],index=None,   key="dataset_select")
with colB:
    target_type = st.selectbox("Target type",("Individual Forecasts (by Area/Group)", "Combined Forecast (Total Across Selection)"),
        key="target_select")

# Load data only if user selected dataset

if data_type is None:
    st.warning(" Please select either Production or Consumption to continue.")
    df, group_col = None, None
else:
    if data_type == "Production":
        df = get_production_data()
        group_col = "productionGroup"
    else:
        df = get_consumption_data()
        group_col = "consumptionGroup"

    st.success(f"{data_type} data loaded!")

    df['startTime'] = pd.to_datetime(df['startTime']).dt.tz_localize(None)
    df = df.sort_values("startTime").set_index("startTime")

    #  Filters and Exogenous variables side by side
    col1, col2 = st.columns(2)
    
    with col1:
        selected_price_area = st.multiselect("Select target Price area(s)", df["priceArea"].dropna().unique(), key="price_area_multiselect")
        selected_groups = st.multiselect(f"Selected target {group_col}(s)", df[group_col].dropna().unique(), key="group_multiselect")
    
    with col2:
        with st.expander("Exogenous Variables"):
            if data_type == "Production":
                exog_options = [g for g in df[group_col].dropna().unique() if g not in selected_groups] + ["Total Consumption"]
            else:
                exog_options = [g for g in df[group_col].dropna().unique() if g not in selected_groups] + ["Total Production"]
            selected_exog = st.multiselect("Optional exogenous vars", exog_options, key="exog_multiselect")

    #  Training window and Forecast horizon side by side
    min_date, max_date = df.index.min().date(), df.index.max().date()
    col3, col4 = st.columns(2)
    with col3:
        train_start = st.date_input("Train start", min_date, min_value=min_date, max_value=max_date, key="train_start_date")
        train_end = st.date_input("Train end", max_date, min_value=min_date, max_value=max_date, key="train_end_date")
        train_start_ts = pd.Timestamp(train_start)
        train_end_ts = pd.Timestamp(train_end) + pd.Timedelta(hours=23, minutes=59)
    with col4:
        forecast_option = st.selectbox("Forecast horizon",("24 hours", "1 week", "1 month", "3 months"),key="forecast_horizon_select")

    horizon_map = {"24 hours": 24, "1 week": 24*7, "1 month": 24*30, "3 months": 24*90}
    forecast_steps = horizon_map[forecast_option]

    #  SARIMAX parameters in expander 
    with st.expander("SARIMAX Parameters"):
        colP, colQ, colM = st.columns(3)
        with colP:
            p = st.number_input("AR (p)", min_value=0, value=1)
            d = st.number_input("Diff (d)", min_value=0, value=1)
            q = st.number_input("MA (q)", min_value=0, value=1)
        with colQ:
            P = st.number_input("Seasonal AR (P)", min_value=0, value=1)
            D = st.number_input("Seasonal Diff (D)", min_value=0, value=1)
            Q = st.number_input("Seasonal MA (Q)", min_value=0, value=1)
        with colM:
            m = st.number_input("Seasonal Period (m)", min_value=1, value=24)


    # FIT & FORECAST

if st.button(" Fit SARIMAX Models and Forecasts"):

    # Individual Forecasts (by Area/Group)
   
    if target_type == "Individual Forecasts (by Area/Group)":
        for area in selected_price_area:
            for group in selected_groups:
                df_subset = df[(df["priceArea"] == area) & (df[group_col] == group)].copy()

                if df_subset.empty:
                    st.warning(f"No data for {area} - {group}")
                    continue

                # Restrict window
                df_train = df_subset[(df_subset.index >= train_start_ts) &
                                     (df_subset.index <= train_end_ts)]

                # Always reset to startTime as index
                df_train = df_train.reset_index().set_index("startTime").sort_index()

                if df_train.empty:
                    st.warning(f"No training data for {area} - {group} in selected window")
                    continue

                # Collapse to one series
                y_train = df_train["quantityKwh"].sort_index()

                # Enforce hourly frequency
                y_train = y_train.asfreq("h").ffill()

                # Build exogenous training matrix
                exog_train = pd.DataFrame(index=y_train.index)
                for exog in selected_exog:
                    if exog == "Total Consumption":
                        cons = get_consumption_data()
                        cons['startTime'] = pd.to_datetime(cons['startTime']).dt.tz_localize(None)
                        series = cons[cons["priceArea"] == area].groupby("startTime")["quantityKwh"].sum()
                    elif exog == "Total Production":
                        prod = get_production_data()
                        prod['startTime'] = pd.to_datetime(prod['startTime']).dt.tz_localize(None)
                        series = prod[prod["priceArea"] == area].groupby("startTime")["quantityKwh"].sum()
                    else:
                        series = df[(df[group_col] == exog) & (df["priceArea"] == area)]["quantityKwh"]
                        series.index = df[(df[group_col] == exog) & (df["priceArea"] == area)].index
                    exog_train[exog] = series.reindex(y_train.index).fillna(0)

                # Fit SARIMAX
                model = SARIMAX(
                    y_train,
                    exog=exog_train if not exog_train.empty else None,
                    order=(p, d, q),
                    seasonal_order=(P, D, Q, m),
                    trend="c",
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
                result = model.fit(disp=False)

                # Build exogenous future (repeat last observed values)
                if not exog_train.empty:
                    last_exog = exog_train.iloc[-1]
                    forecast_start = y_train.index[-1] + pd.Timedelta(hours=1)
                    forecast_index = pd.date_range(start=forecast_start, periods=forecast_steps, freq="h")
                    exog_future = pd.DataFrame([last_exog] * forecast_steps, index=forecast_index)
                else:
                    exog_future = None

                # Forecast
                forecast_obj = result.get_forecast(steps=forecast_steps, dynamic=True, exog=exog_future)
                forecast_mean = forecast_obj.predicted_mean
                conf_int = forecast_obj.conf_int()

                st.success(f"Forecast complete for {area} - {group}")

                # Plot
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=y_train.index, y=y_train.values,
                    mode='lines', name='Training Data', line=dict(color='blue')
                ))
                fig.add_trace(go.Scatter(
                    x=forecast_mean.index, y=forecast_mean.values,
                    mode='lines', name='Forecast', line=dict(color='orange')
                ))
                fig.add_trace(go.Scatter(
                    x=list(conf_int.index) + list(conf_int.index[::-1]),
                    y=list(conf_int.iloc[:, 1]) + list(conf_int.iloc[:, 0][::-1]),
                    fill='toself', fillcolor='rgba(255,165,0,0.3)',
                    line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip",
                    name="Confidence Interval"
                ))
                fig.update_layout(title=f"SARIMAX Forecast: {area} - {group}",
                                  xaxis_title="Time", yaxis_title="quantityKwh",
                                  template="plotly_white")

                st.plotly_chart(fig, use_container_width=True)


    # Combined Forecast (Total Across Selection)

    elif target_type == "Combined Forecast (Total Across Selection)":
        # Filter selection
        df_subset = df[
            (df["priceArea"].isin(selected_price_area)) &
            (df[group_col].isin(selected_groups))
        ].copy()

        if df_subset.empty:
            st.warning("No data for selected areas/groups")
            st.stop()

        # Restrict window
        df_train = df_subset[(df_subset.index >= train_start_ts) &
                             (df_subset.index <= train_end_ts)]

        # Always reset to startTime as index
        df_train = df_train.reset_index().set_index("startTime").sort_index()

        # Collapse all selected areas/groups into one combined series
        y_train = df_train.groupby("startTime")["quantityKwh"].sum().sort_index()

        # Enforce hourly frequency AFTER aggregation
        y_train = y_train.asfreq("h").fillna(0)

        if y_train.empty:
            st.warning("No training data in selected window")
            st.stop()

        # Fit SARIMAX (no exog for simplicity here)
        model = SARIMAX(
            y_train,
            order=(p, d, q),
            seasonal_order=(P, D, Q, m),
            trend="c",
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        result = model.fit(disp=False)

        # Forecast
        forecast_obj = result.get_forecast(steps=forecast_steps, dynamic=True)
        forecast_mean = forecast_obj.predicted_mean
        conf_int = forecast_obj.conf_int()

        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=y_train.index, y=y_train.values,
            mode='lines', name='Training Data', line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=forecast_mean.index, y=forecast_mean.values,
            mode='lines', name='Forecast', line=dict(color='orange')
        ))
        fig.add_trace(go.Scatter(
            x=list(conf_int.index) + list(conf_int.index[::-1]),
            y=list(conf_int.iloc[:, 1]) + list(conf_int.iloc[:, 0][::-1]),
            fill='toself', fillcolor='rgba(255,165,0,0.3)',
            line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip",
            name="Confidence Interval"
        ))
        fig.update_layout(title="SARIMAX Forecast: Aggregated selection (Summed)",
                          xaxis_title="Time", yaxis_title="quantityKwh",
                          template="plotly_white")

        st.plotly_chart(fig, use_container_width=True)