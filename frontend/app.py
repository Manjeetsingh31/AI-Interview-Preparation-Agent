import streamlit as st
from utils.session import init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from utils.constants import APP_NAME, APP_ICON

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="auto",
)

init_session()
load_css()

if not st.session_state.logged_in:
    st.switch_page("pages/1_Login.py")
    st.stop()

st.switch_page("pages/2_Dashboard.py")
