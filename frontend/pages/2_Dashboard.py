import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css, stat_card
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_progress_bar
from utils.constants import APP_NAME


st.set_page_config(page_title=f"Dashboard - {APP_NAME}", page_icon="📊", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)

with st.spinner("Loading dashboard..."):
    dashboard = api.get_dashboard()

if not dashboard:
    st.info("No dashboard data available yet. Start by uploading your resume!")
else:
    summary = dashboard.get("summary", {})
    stats = dashboard.get("statistics", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(stat_card("Resume", "Uploaded" if summary.get("resume_uploaded") else "Not Uploaded", color="info" if summary.get("resume_uploaded") else "warning"), unsafe_allow_html=True)
    with col2:
        score = summary.get("ats_score", "N/A")
        score_display = f"{score:.0f}" if isinstance(score, (int, float)) else "N/A"
        st.markdown(stat_card("ATS Score", score_display, color="success" if isinstance(score, (int, float)) and score >= 70 else "warning"), unsafe_allow_html=True)
    with col3:
        avg = summary.get("average_score", "N/A")
        avg_display = f"{avg:.0f}" if isinstance(avg, (int, float)) else "N/A"
        st.markdown(stat_card("Avg Score", avg_display, color="success" if isinstance(avg, (int, float)) and avg >= 70 else "warning"), unsafe_allow_html=True)
    with col4:
        sesh = summary.get("completed_sessions", 0)
        st.markdown(stat_card("Interviews", sesh, color="primary"), unsafe_allow_html=True)
    with col5:
        readiness = summary.get("overall_readiness_score", "N/A")
        rd = f"{readiness}%" if isinstance(readiness, (int, float)) else "N/A"
        st.markdown(stat_card("Readiness", rd, color="success" if isinstance(readiness, (int, float)) and readiness >= 70 else "warning"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Quick Actions", "⚡")
        actions = [
            ("📄 Upload Resume", "Resume", "pages/3_Resume.py", "Upload and analyze your resume"),
            ("🎯 ATS Analysis", "ATS", "pages/4_ATS.py", "Check your ATS score"),
            ("❓ Generate Questions", "Interview Questions", "pages/5_Interview_Questions.py", "Practice with tailored questions"),
            ("🎤 Mock Interview", "Mock Interview", "pages/6_Mock_Interview.py", "Start a practice interview"),
        ]
        for action_icon_label, action_page, action_path, action_desc in actions:
            if st.button(f"{action_icon_label}", key=f"action_{action_page}", use_container_width=True):
                st.switch_page(action_path)
            st.caption(action_desc)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Recent Activity", "🕐")
        timeline = stats.get("timeline", {})
        daily = timeline.get("daily", [])
        if daily:
            for entry in daily[-5:]:
                date = entry.get("date", entry.get("day", "Unknown"))
                sessions_count = entry.get("sessions", entry.get("count", 0))
                st.markdown(f"**{date}**: {sessions_count} session(s)")
        else:
            st.info("No recent activity yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Study Progress", "📚")
    study = stats.get("study", {})
    completion = study.get("completion_percentage") or 0
    render_progress_bar(completion, "Overall Study Completion")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Plans", study.get("total_plans", 0))
    with col2: st.metric("Active Plans", study.get("active_plans", 0))
    with col3: st.metric("Tasks Done", study.get("tasks_completed", 0))
    with col4: st.metric("Tasks Pending", study.get("tasks_pending", 0))
    st.markdown("</div>", unsafe_allow_html=True)
