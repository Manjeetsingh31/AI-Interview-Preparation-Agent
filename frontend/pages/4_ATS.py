import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_tags, render_progress_bar, render_stat_card
from components.charts import bar_chart, pie_chart, gauge_chart
from utils.constants import APP_NAME


st.set_page_config(page_title=f"ATS - {APP_NAME}", page_icon="🎯", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>🎯 ATS Analysis</h1>", unsafe_allow_html=True)

resume_analysis_id = st.session_state.get("resume_analysis_id")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Run ATS Analysis", "🚀")
    if not resume_analysis_id:
        st.warning("No resume analysis found. Upload and analyze your resume first on the Resume page.")
    else:
        st.info(f"Using resume analysis: {resume_analysis_id[:8]}...")
        if st.button("Run ATS Analysis", type="primary", use_container_width=True):
            result = api.analyze_ats(resume_analysis_id)
            if result:
                st.success("ATS analysis complete!")
                st.session_state.ats_id = result.get("id")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("History", "📜")
    history = api.get_ats_history()
    if history:
        for item in history[:5]:
            score = item.get("overall_score", 0)
            st.markdown(f"**Score**: {score}/100 — {item.get('id', '')[:8]}...")
    else:
        st.info("No previous analyses.")
    st.markdown("</div>", unsafe_allow_html=True)

ats_id = st.session_state.get("ats_id")
if ats_id:
    ats_data = api.get_ats_score(ats_id)
    if ats_data:
        st.markdown("<br>", unsafe_allow_html=True)
        overall = ats_data.get("overall_score", 0)

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown(render_stat_card("Overall Score", overall, "/100", "success" if overall >= 70 else "warning"), unsafe_allow_html=True)
        with col2: st.markdown(render_stat_card("Structure", ats_data.get("resume_structure_score", "N/A"), "/100", "info"), unsafe_allow_html=True)
        with col3: st.markdown(render_stat_card("Grammar", ats_data.get("grammar_score", "N/A"), "/100", "info"), unsafe_allow_html=True)
        with col4: st.markdown(render_stat_card("Education", ats_data.get("education_score", "N/A"), "/100", "info"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Section Scores", "📊")
            section_scores = ats_data.get("section_scores", {})
            if section_scores:
                labels = []
                values = []
                for key, val in section_scores.items():
                    label = key.replace("_", " ").title()
                    score_val = val if isinstance(val, (int, float)) else (val.get("score", 0) if isinstance(val, dict) else 0)
                    labels.append(label)
                    values.append(score_val)
                bar_chart(labels, values, "Section-wise Scores")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Strengths", "✅")
            strengths = ats_data.get("strengths", [])
            if strengths:
                for s in strengths:
                    st.markdown(f"- {s}")
            else:
                st.info("No strengths identified.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Improvement Areas", "🔧")
            weaknesses = ats_data.get("weaknesses", [])
            if weaknesses:
                for w in weaknesses:
                    st.markdown(f"- {w}")
            else:
                st.info("No weaknesses identified.")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Missing Skills", "📋")
            missing_tech = ats_data.get("missing_technical_skills", [])
            missing_soft = ats_data.get("missing_soft_skills", [])
            missing_kw = ats_data.get("missing_keywords", [])
            if missing_tech:
                st.markdown("**Technical:**")
                render_tags(missing_tech)
            if missing_soft:
                st.markdown("**Soft:**")
                render_tags(missing_soft)
            if missing_kw:
                st.markdown("**Keywords:**")
                render_tags(missing_kw)
            if not any([missing_tech, missing_soft, missing_kw]):
                st.info("No missing skills identified.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Suggestions", "💡")
        suggestions = ats_data.get("improvement_suggestions", [])
        if suggestions:
            for s in suggestions:
                st.markdown(f"- {s}")
        else:
            st.info("No suggestions available.")
        st.markdown("</div>", unsafe_allow_html=True)
