from pathlib import Path
import streamlit as st
from utils.constants import PAGE_ICONS, APP_NAME, APP_ICON
from utils.session import logout


PAGE_PATHS = {
    "Dashboard": "pages/2_Dashboard.py",
    "Resume": "pages/3_Resume.py",
    "ATS": "pages/4_ATS.py",
    "Interview Questions": "pages/5_Interview_Questions.py",
    "Mock Interview": "pages/6_Mock_Interview.py",
    "Evaluation": "pages/7_Evaluation.py",
    "Study Plan": "pages/8_Study_Plan.py",
    "Analytics": "pages/9_Analytics.py",
}


def _current_page_name():
    try:
        return st.session_state.get("current_page", "Dashboard")
    except Exception:
        return "Dashboard"


def render_sidebar():
    current = _current_page_name()

    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>{APP_ICON} {APP_NAME}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color: #334455;'>", unsafe_allow_html=True)

        st.markdown(f"<div style='color: #94A3B8; font-size: 0.8rem; padding: 0.5rem 0;'>Welcome, {st.session_state.get('user_email', 'User')}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color: #334455;'>", unsafe_allow_html=True)

        for page in PAGE_PATHS:
            icon = PAGE_ICONS.get(page, "📄")
            active = page == current
            if st.button(
                f"{icon} {page}",
                key=f"nav_{page}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state["current_page"] = page
                st.switch_page(PAGE_PATHS[page])


        st.markdown("<hr style='border-color: #334455;'>", unsafe_allow_html=True)

        if st.button("🚪 Logout", key="logout_btn", use_container_width=True, type="secondary"):
            logout()
            st.switch_page("pages/1_Login.py")
