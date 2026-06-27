import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_stat_card, render_tags
from components.charts import radar_chart, bar_chart, pie_chart
from utils.constants import APP_NAME


st.set_page_config(page_title=f"Evaluation - {APP_NAME}", page_icon="📝", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>📝 Interview Evaluation</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Generate Evaluation", "View Evaluations", "Analytics"])

with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Generate Evaluation", "🆕")
    session_id = st.text_input("Interview Session ID", placeholder="Enter the session ID to evaluate", key="eval_session_id")
    if st.button("Generate Evaluation", type="primary", use_container_width=True) and session_id:
        result = api.generate_evaluation(session_id)
        if result:
            st.success("Evaluation generated successfully!")
            st.session_state.latest_evaluation = result
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("All Evaluations", "📋")
    evaluations = api.get_evaluations()
    if evaluations:
        for ev in evaluations[:10]:
            score = ev.get("overall_score", 0)
            decision = ev.get("hire_decision", "N/A")
            color = "success" if score >= 70 else "warning" if score >= 40 else "danger"
            st.markdown(f"**Session**: {ev.get('session_id', '')[:8]}... | **Score**: {score}/100 | **Decision**: {decision}")
            with st.expander("Details"):
                cols = st.columns(3)
                with cols[0]: st.metric("Technical", ev.get("technical_score", "N/A"))
                with cols[1]: st.metric("Communication", ev.get("communication_score", "N/A"))
                with cols[2]: st.metric("Problem Solving", ev.get("problem_solving_score", "N/A"))
                if ev.get("strengths"):
                    st.markdown("**Strengths:**")
                    for s in ev["strengths"]:
                        st.markdown(f"- {s}")
                if ev.get("weaknesses"):
                    st.markdown("**Weaknesses:**")
                    for w in ev["weaknesses"]:
                        st.markdown(f"- {w}")
                if ev.get("improvement_suggestions"):
                    st.markdown("**Suggestions:**")
                    for sg in ev["improvement_suggestions"]:
                        st.markdown(f"- {sg}")
                if ev.get("evaluation_summary"):
                    st.markdown(f"**Summary:** {ev['evaluation_summary']}")
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    else:
        st.info("No evaluations found. Generate one first.")
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Evaluation Statistics", "📊")
    stats = api.get_evaluation_statistics()
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total Evaluations", stats.get("total_evaluations", 0))
        with col2: st.metric("Avg Overall", f"{stats.get('average_overall_score', 0):.0f}%" if stats.get("average_overall_score") else "N/A")
        with col3: st.metric("Improvement Rate", f"{stats.get('improvement_rate', 0):.0f}%" if stats.get("improvement_rate") else "N/A")

        radar_data = {
            "Technical": stats.get("average_technical_score") or 0,
            "Communication": stats.get("average_communication_score") or 0,
            "Problem Solving": stats.get("average_problem_solving_score") or 0,
            "Confidence": stats.get("average_confidence_score") or 0,
            "Behavioral": stats.get("average_behavioral_score") or 0,
        }
        radar_chart(list(radar_data.keys()), list(radar_data.values()), "Average Scores by Dimension")

        col1, col2 = st.columns(2)
        with col1:
            strengths = stats.get("most_common_strengths", [])
            if strengths:
                st.markdown("**Common Strengths:**")
                for s in strengths[:5]:
                    st.markdown(f"- {s}")
        with col2:
            weaknesses = stats.get("most_common_weaknesses", [])
            if weaknesses:
                st.markdown("**Common Weaknesses:**")
                for w in weaknesses[:5]:
                    st.markdown(f"- {w}")
    else:
        st.info("No statistics available yet.")
    st.markdown("</div>", unsafe_allow_html=True)
