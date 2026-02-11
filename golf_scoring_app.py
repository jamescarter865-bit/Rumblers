# At top of app
import streamlit as st
st.set_page_config(layout="wide", page_title="Golf Rumble Scoring", initial_sidebar_state="collapsed")

# Hide hamburger & footer for cleaner mobile look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
