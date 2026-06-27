import json
import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_info_card
from components.charts import bar_chart, pie_chart
from utils.constants import APP_NAME


st.set_page_config(page_title=f"Resume - {APP_NAME}", page_icon="📄", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>📄 Resume Analysis</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Upload & Analyze", "Extracted Data"])

with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Upload Resume", "📤")
    uploaded_file = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"], key="resume_upload")
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > 10:
            st.error("File size exceeds 10 MB limit.")
        else:
            if st.button("Analyze Resume", type="primary", use_container_width=True):
                result = api.analyze_resume(file_bytes, uploaded_file.name)
                if result:
                    st.success("Resume analyzed successfully!")
                    st.session_state.resume_analysis_id = result.get("id")
                    st.session_state.resume_id = result.get("id")
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("resume_analysis_id"):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Last Analysis", "📋")
        st.info(f"Analysis ID: {st.session_state.resume_analysis_id}")
        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    analysis_id = st.session_state.get("resume_analysis_id")
    if not analysis_id:
        st.info("Please upload and analyze a resume first.")
    else:
        questions = api.get_questions_by_analysis(analysis_id)
        if not questions:
            st.info("No extracted data available. Upload a resume first.")
        else:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Skills", "🛠️")
            all_tags = set()
            for q in questions:
                for t in (q.get("tags") or []):
                    all_tags.add(t)
            if all_tags:
                tags_html = "".join(f"<span class='tag'>{t}</span>" for t in sorted(all_tags))
                st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='card'>", unsafe_allow_html=True)
render_section_header("Resume Summary", "📊")

ats_history = api.get_ats_history()
if ats_history:
    latest_ats = ats_history[0]
    score = latest_ats.get("overall_score", 0)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Latest ATS Score", f"{score}/100")
    with col2:
        if st.button("View Full ATS Analysis →", key="goto_ats"):
            st.switch_page("pages/4_ATS.py")
else:
    st.info("No ATS analysis yet. Go to the ATS page to analyze your resume.")
st.markdown("</div>", unsafe_allow_html=True)
