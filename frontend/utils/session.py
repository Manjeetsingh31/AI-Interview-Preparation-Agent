import streamlit as st


def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "page" not in st.session_state:
        st.session_state.page = "Login"
    if "resume_id" not in st.session_state:
        st.session_state.resume_id = None
    if "resume_analysis_id" not in st.session_state:
        st.session_state.resume_analysis_id = None
    if "interview_session_id" not in st.session_state:
        st.session_state.interview_session_id = None
    if "ats_id" not in st.session_state:
        st.session_state.ats_id = None
    if "study_plan_id" not in st.session_state:
        st.session_state.study_plan_id = None


def check_auth():
    init_session()
    if not st.session_state.logged_in:
        st.switch_page("pages/1_Login.py")
        st.stop()


def login(email, user_id, token):
    st.session_state.logged_in = True
    st.session_state.user_email = email
    st.session_state.user_id = user_id
    st.session_state.token = token


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session()
