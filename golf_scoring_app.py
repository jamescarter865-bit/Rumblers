import streamlit as st
import pandas as pd

# These two blocks MUST come right here — after the imports, before ANY other st.something
st.set_page_config(
    layout="wide",
    page_title="Golf Rumble Scoring",
    initial_sidebar_state="collapsed"
)

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Now paste ALL the rest of your original code below this...
# (the def stableford_points(...), def strokes_on_hole(...), st.title(...), etc.)
