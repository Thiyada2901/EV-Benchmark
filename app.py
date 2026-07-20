%%writefile app.py
import streamlit as st
import pandas as pd
import numpy as np

# --- Set Streamlit Theme (Orange-White) ---
st.set_page_config(
    page_title="EV Benchmarking App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* Main background color */
    .stApp { background-color: #FFFFFF; } /* White */
    /* Sidebar background color */
    .st-emotion-cache-1ldk86k { background-color: #FFF0E0; } /* Light Peach */
    .st-emotion-cache-1ldk86k .st-emotion-cache-vk3370 { background-color: #FFDAB9; } /* Peach Puff for sidebar header */

    /* Primary button color (orange) */
    .stButton>button { background-color: #FFA500; color: white; border: none; }
    .stButton>button:hover { background-color: #FF8C00; color: white; }

    /* Text color */
    body { color: #333333; } /* Dark Grey */
    h1, h2, h3, h4, h5, h6 { color: #FF7F50; } /* Coral */

    /* Expander background */
    .streamlit-expanderHeader { background-color: #FFEFD5; } /* PapayaWhip */
    .streamlit-expanderContent { background-color: #FFFFFF; } /* White */

    /* Custom CSS for similarity badges */
    .similarity-badge {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        width: 42px; /* Adjust size as needed */
        height: 42px;
        border-radius: 50%;
        color: white;
        font-weight: bold;
        font-size: 0.85em;
        background-color: grey; /* Default */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .similarity-badge-green { background-color: #28a745; } /* Green */
    .similarity-badge-darkyellow { background-color: #ffc107; color: black; } /* Dark Yellow */
    .similarity-badge-lightyellow { background-color: #fff3cd; color: black; } /* Light Yellow */

    /* Custom CSS for smaller table font */
    .small-table{
        font-size:14px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Add Thanachart Insurance Logo to the top right of the title ---
col1, col2 = st.columns([0.8, 0.2]) # Adjust ratios as needed
with col1:
    st.title("EV benchmark for Thanachart insurance")
with col2:
    try:
        st.image('thanachart_logo.jpg', width=150)
    except FileNotFoundError:
        st.warning("Thanachart Insurance logo (thanachart_logo.jpg) not found. Please upload the image file.")

st.write("ค้นหารถยนต์ไฟฟ้าที่คล้ายคลึงกันตามคุณสมบัติที่คุณเลือก")

# --- Session State Initializations ---
# Page navigation
if "page" not in st.session_state:
    st.session_state["page"] = "result"

if "results" not in st.session_state:
    st.session_state["results"] = None

if "selected_car_index" not in st.session_state:
    st.session_state[
