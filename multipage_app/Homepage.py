import streamlit as st
import os
import importlib.util
st.set_page_config(page_title="Multipage app", layout="wide")


def homepage():
    # Title
    st.markdown("<h1 style='color:#2E86C1;'>🌍 Energy & Weather Dashboard</h1>", unsafe_allow_html=True)

    # Intro
    st.markdown("""
    <p style='font-size:18px; color:black;'>
    Welcome to the Energy & Weather Dashboard!  
    This app helps to explore, analyze, and visualize energy production and weather data in one place.  
    <br><br>
    Energy data has been fetched from a <b>MongoDB database</b>, while weather data comes from the <b>Open-Meteo API</b>.
    </p>
    """, unsafe_allow_html=True)

    # Sections overview
    st.subheader("🔎 What you can do here")
    st.markdown("""
    - **Visualization** → Interactive graphs and maps to explore data.  
    - **Analysis** → Dive deeper into trends, anomalies, and seasonal patterns.  
    - **Forecasting** → Use models like SARIMAX to predict future energy production.  
    - **Cross-Domain** → Study correlations between weather and energy data.
    """)

    # Getting started guide
    st.subheader("📘 How to get started")
    st.markdown("""
    1. Explore **Visualization** pages to get an overview of data.  
       - The **Maps page** allows you to interactively select locations and view energy insights.  
    2. Check **Analysis** pages for Outliers/Anomalies detection and STL decomposition/Spectogram.  
    3. Use **Forecasting** to project future trends.  
    4. Finally, explore **Correlation** to see how weather impacts energy.
    """)

    # Tips
    st.subheader("💡 Tips")
    st.info("""
    - Navigation is grouped by **Energy**, **Weather**, and **Cross-Domain**.  
    - Use the sidebar to switch between sections, subsection and pages.  
    """)
    # Footer
    st.markdown("---")
    st.markdown("<p style='font-size:14px; color:gray;'> IZZA-IND-320 Semester Project • NMBU</p>", unsafe_allow_html=True)

# SIDE BAR NAVIGATION LAYOUT
# Hide default multipage navigation

st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

# Custom Sidebar
st.sidebar.title("Navigation")
PAGES = {
    "Homepage": None,
    "Energy": {
        "Visualization": {
            "Energy Production": "1_Energy_Production",
            "Maps": "6_maps"
        },
        "Analysis": {
            "STL/Spectogram": "2_STL_Spectogram"
        },
        "Forecasting": {
            "Forecast": "9_sarimax"
        }
    },
    "Weather": {
        "Visualization": {
            "Weather Insights": "4_Data_Visualization"
        },
        "Analysis": {
            "Outliers Anomalies": "5_Outliers_Anomalies",
            "Snow Drift": "7_snow_drift"
        }
    },
    "Cross-Domain": {
        "Correlation": {
            "Sliding Window Correlation": "8_correlation"
        }
    }
}

# Section selectbox
section_list = list(PAGES.keys())
section_default = st.session_state.get("section", "Homepage")
section_index = section_list.index(section_default) if section_default in section_list else 0
section = st.sidebar.selectbox("Section", section_list, index=section_index)
st.session_state["section"] = section

if section == "Homepage":
    page_name = "Homepage"
    subgroup = None
    st.session_state["page_name"] = page_name

else:
    # Subgroup selectbox
    subgroup_list = list(PAGES[section].keys())
    subgroup_default = st.session_state.get("subgroup", None)

    subgroup = st.sidebar.selectbox(
        "Subgroup",
        ["Select a subgroup"] + subgroup_list,
        index=0 if subgroup_default not in subgroup_list else subgroup_list.index(subgroup_default) + 1,
        placeholder="Select a subgroup"
    )

    # Stop until user selects a valid subgroup
    if subgroup not in subgroup_list:
        st.warning("👉 Please select a subgroup to continue.")
        st.stop()

    st.session_state["subgroup"] = subgroup


    # --- Page selectbox ---
    page_list = list(PAGES[section][subgroup].keys())
    page_default = st.session_state.get("page_name", None)

    page_name = st.sidebar.selectbox(
        "Page",
        ["Select a page"] + page_list,
        index=0 if page_default not in page_list else page_list.index(page_default) + 1,
        placeholder="Select a page"
    )

    # Stop until user selects a valid page
    if page_name not in page_list:
        st.warning("👉 Please select a page to continue.")
        st.stop()

    st.session_state["page_name"] = page_name


# Load page dynamically

def load_page(page_file):
    spec = importlib.util.spec_from_file_location("module.name", page_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

if page_name == "Homepage":
    homepage()
else:
    script_dir = os.path.dirname(__file__)
    page_file = os.path.join(script_dir, "pages", f"{PAGES[section][subgroup][page_name]}.py")
    if os.path.exists(page_file):
        load_page(page_file)
    else:
        st.error(f"Page file not found: {page_file}")

# Sidebar footer (updated)

st.sidebar.markdown("---")
if section == "Homepage":
    st.sidebar.markdown(f"**Current Section:** {section}  \n**Page:** {page_name}")
else:
    st.sidebar.markdown(f"**Current Section:** {section}  \n**Subgroup:** {subgroup}  \n**Page:** {page_name}")


