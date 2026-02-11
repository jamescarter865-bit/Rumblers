import streamlit as st
import pandas as pd

# Mobile-friendly settings - MUST come right after import, before any st.title etc.
st.set_page_config(
    layout="wide",
    page_title="Golf Rumble Scoring",
    initial_sidebar_state="collapsed"
)

# Hide extra Streamlit stuff for cleaner mobile look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Now the rest of your original code...
# Function to calculate Stableford points for a hole
def stableford_points(gross_score, par, strokes_received):
    ...
