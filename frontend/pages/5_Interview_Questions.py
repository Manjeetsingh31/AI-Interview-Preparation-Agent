import json
import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_tags
from utils.constants import APP_NAME, DIFFICULTY_LEVELS, INTERVIEW_TYPES, QUESTION_COUNTS


st.set_page_config(page_title=f"Interview Questions - {APP_NAME}", page_icon="❓", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>❓ Interview Questions</h1>", unsafe_allow_html=True)

resume_analysis_id = st.session_state.get("resume_analysis_id")

if not resume_analysis_id:
    st.warning("Please upload and analyze your resume first on the Resume page.")
    st.stop()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Generate Questions", "⚙️")
    with st.form("generate_questions_form"):
        company = st.text_input("Company", placeholder="e.g., Google, Microsoft", value="Google")
        role = st.text_input("Target Role", placeholder="e.g., Software Engineer", value="Software Engineer")
        interview_type = st.selectbox("Interview Type", INTERVIEW_TYPES, index=4)
        difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1)
        num_questions = st.selectbox("Number of Questions", QUESTION_COUNTS, index=2)
        submitted = st.form_submit_button("Generate Questions", type="primary", use_container_width=True)
        if submitted:
            result = api.generate_questions(
                resume_analysis_id=resume_analysis_id,
                company=company,
                role=role,
                interview_type=interview_type,
                difficulty=difficulty.lower(),
                number_of_questions=num_questions,
            )
            if result:
                st.success(f"Generated {len(result.get('questions', []))} questions!")
                st.session_state.generated_questions = result.get("questions", [])
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Question History", "📜")
    history = api.get_question_history()
    if history:
        for q in history[:5]:
            with st.expander(f"[{q.get('difficulty','').title()}] {q.get('question', '')[:80]}..."):
                st.markdown(f"**Type:** {q.get('question_type', 'N/A')}")
                st.markdown(f"**Company:** {q.get('company', 'N/A')}")
                st.markdown(f"**Role:** {q.get('role', 'N/A')}")
                if q.get("expected_answer"):
                    st.markdown(f"**Expected Answer:** {q['expected_answer']}")
                if q.get("hints"):
                    st.markdown("**Hints:**")
                    for h in q["hints"]:
                        st.markdown(f"- {h}")
                if q.get("tags"):
                    st.markdown("**Tags:**")
                    render_tags(q["tags"])
    else:
        st.info("No questions generated yet.")
    st.markdown("</div>", unsafe_allow_html=True)

questions = st.session_state.get("generated_questions", [])
if questions:
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_header(f"Generated Questions ({len(questions)})", "📋")

    for i, q in enumerate(questions, 1):
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**Q{i}.** {q.get('question', '')}")
        st.caption(f"Type: {q.get('question_type', 'N/A')} | Difficulty: {q.get('difficulty', 'N/A')}")

        with st.expander("Show Answer & Details"):
            if q.get("expected_answer"):
                st.markdown(f"**Expected Answer:**\n{q['expected_answer']}")
            if q.get("hints"):
                st.markdown("**Hints:**")
                for h in q["hints"]:
                    st.markdown(f"- {h}")
            if q.get("follow_up"):
                st.markdown(f"**Follow-up:** {q['follow_up']}")
            if q.get("tags"):
                st.markdown("**Tags:**")
                render_tags(q["tags"])

        col1, col2 = st.columns([1, 5])
        with col1:
            q_json = json.dumps(q, indent=2)
            st.download_button(
                f"📥 Q{i}",
                data=q_json,
                file_name=f"question_{i}.json",
                mime="application/json",
                key=f"dl_q_{i}",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    all_json = json.dumps(questions, indent=2)
    st.download_button(
        "📥 Download All Questions as JSON",
        data=all_json,
        file_name="interview_questions.json",
        mime="application/json",
        use_container_width=True,
    )
