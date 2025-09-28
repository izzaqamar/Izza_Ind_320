import streamlit as st

# Set full width layout and hide Streamlit UI
st.set_page_config(layout="wide")

# CSS for styling (centered text, larger font, animation)
st.markdown("""
    <style>
    body {
        background-color: #111;
        color: white;
    }
    .center {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 90vh;
        font-size: 5em;
        font-weight: bold;
        color: white;
        text-shadow: 2px 2px 10px #1E90FF;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    </style>

    <div class="center">
        🚧...Stay Tuned...🚀
    </div>
""", unsafe_allow_html=True)