import streamlit as st
from utils.api import api
from utils.session import init_session, login
from utils.styles import load_css
from utils.constants import APP_NAME, APP_ICON


st.set_page_config(
    page_title=f"Login - {APP_NAME}",
    page_icon=APP_ICON,
    layout="centered",
)

init_session()
load_css()

if st.session_state.logged_in:
    st.switch_page("pages/2_Dashboard.py")
    st.stop()

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"<h1 style='text-align: center;'>{APP_ICON} {APP_NAME}</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Prepare smarter. Interview better.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    result = api.login(email, password)
                    if result:
                        login(email, result.get("user_id"), result.get("access_token"))
                        st.success("Login successful!")
                        st.rerun()

    with tab2:
        with st.form("register_form"):
            reg_email = st.text_input("Email", placeholder="Enter your email", key="reg_email")
            reg_password = st.text_input("Password", type="password", placeholder="Create a password (min 6 chars)", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")
            submitted_reg = st.form_submit_button("Register", type="primary", use_container_width=True)
            if submitted_reg:
                if not reg_email or not reg_password or not reg_confirm:
                    st.error("Please fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    result = api.register(reg_email, reg_password)
                    if result:
                        st.success("Registration successful! Please login.")
