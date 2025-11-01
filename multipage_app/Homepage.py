import streamlit as st

st.set_page_config(page_title="Multipage app", layout="wide")
st.markdown('<h1 style="color:blue;">Weather Data App</h1>', unsafe_allow_html=True)
st.sidebar.success("Select a page above")

st.markdown("""<p style='font-size:18px; color:black;'>
   ☀️ Sunny days or 🌧️ rainy nights, let's explore the weather trends together! 🌦️</p>""", unsafe_allow_html=True)

