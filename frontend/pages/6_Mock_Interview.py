import time
import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_progress_bar
from components.charts import bar_chart, line_chart
from utils.constants import APP_NAME, DIFFICULTY_LEVELS, INTERVIEW_TYPES


st.set_page_config(page_title=f"Mock Interview - {APP_NAME}", page_icon="🎤", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>🎤 Mock Interview</h1>", unsafe_allow_html=True)

if "interview_active" not in st.session_state:
    st.session_state.interview_active = False
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = []
if "current_question_idx" not in st.session_state:
    st.session_state.current_question_idx = 0
if "interview_history" not in st.session_state:
    st.session_state.interview_history = []
if "interview_start_time" not in st.session_state:
    st.session_state.interview_start_time = None
if "interview_session_id" not in st.session_state:
    st.session_state.interview_session_id = None
if "interview_scores" not in st.session_state:
    st.session_state.interview_scores = []

resume_analysis_id = st.session_state.get("resume_analysis_id")

if not st.session_state.interview_active:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Start New Interview", "🎬")
        if not resume_analysis_id:
            st.warning("Please upload and analyze your resume first.")
        else:
            with st.form("start_interview_form"):
                company = st.text_input("Company", value="Google")
                role = st.text_input("Target Role", value="Software Engineer")
                interview_type = st.selectbox("Interview Type", INTERVIEW_TYPES, index=4)
                difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1)
                num_q = st.slider("Number of Questions", 5, 30, 10)
                submitted = st.form_submit_button("Start Interview", type="primary", use_container_width=True)
                if submitted:
                    result = api.start_interview(
                        resume_analysis_id=resume_analysis_id,
                        company=company,
                        role=role,
                        interview_type=interview_type,
                        difficulty=difficulty.lower(),
                        number_of_questions=num_q,
                    )
                    if result:
                        st.session_state.interview_active = True
                        st.session_state.interview_session_id = result.get("session_id")
                        st.session_state.current_question_idx = 1
                        st.session_state.interview_questions = [result]
                        st.session_state.interview_history = []
                        st.session_state.interview_scores = []
                        st.session_state.interview_total_questions = num_q
                        st.session_state.interview_start_time = time.time()
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Past Interviews", "📜")
        history = api.get_interview_history()
        if history:
            sessions = set()
            for turn in history:
                sid = turn.get("session_id")
                if sid and sid not in sessions:
                    sessions.add(sid)
                    score = turn.get("score", "N/A")
                    st.markdown(f"- Session `{sid[:8]}...` | Score: {score}")
        else:
            st.info("No past interviews.")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    session_id = st.session_state.interview_session_id
    questions = st.session_state.interview_questions
    current_q = questions[-1] if questions else {}
    q_no = st.session_state.current_question_idx
    is_final = current_q.get("is_final", False)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Question", f"{q_no}")
    with col2: st.metric("Category", current_q.get("category", "-"))
    with col3: st.metric("Difficulty", current_q.get("difficulty", "-").title())
    with col4:
        if st.session_state.interview_start_time:
            elapsed = int(time.time() - st.session_state.interview_start_time)
            st.metric("Time", f"{elapsed // 60}m {elapsed % 60}s")
    st.markdown("</div>", unsafe_allow_html=True)

    if is_final:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Interview Complete! 🎉", "✅")
        st.markdown(f"**Summary:** {current_q.get('transcript_summary', current_q.get('finished_reason', 'Interview finished.'))}")
        if st.session_state.interview_scores:
            st.markdown("### Performance")
            scores = [s.get("score", 0) for s in st.session_state.interview_scores if s.get("score")]
            if scores:
                avg_score = sum(scores) / len(scores)
                st.metric("Average Score", f"{avg_score:.0f}/100")
                line_chart(
                    [{"q": i + 1, "score": s} for i, s in enumerate(scores)],
                    x_col="q", y_col="score",
                    title="Score Progression",
                )
        if st.button("End Session", type="primary", use_container_width=True):
            api.end_interview(session_id)
            for k in ["interview_active", "interview_questions", "current_question_idx", "interview_history", "interview_start_time", "interview_session_id", "interview_scores"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header(f"Question {q_no}", "❓")
        st.markdown(f"<div style='font-size: 1.2rem; line-height: 1.6;'>{current_q.get('question', '')}</div>", unsafe_allow_html=True)
        if current_q.get("follow_up"):
            st.markdown(f"**Follow-up:** {current_q.get('follow_up')}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Your Answer", "✍️")
        with st.form("answer_form"):
            answer = st.text_area("Type your answer:", height=150, placeholder="Write your answer here...")
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Submit Answer", type="primary", use_container_width=True)
            with col2:
                end_early = st.form_submit_button("End Interview Early", use_container_width=True)
            if submitted:
                if answer.strip():
                    result = api.submit_answer(
                        session_id, answer,
                        total_questions=st.session_state.get("interview_total_questions"),
                    )
                    if result:
                        st.session_state.current_question_idx = result.get("question_number", q_no + 1)
                        st.session_state.interview_questions.append(result)
                        if result.get("score") is not None:
                            st.session_state.interview_scores.append(result)
                        st.rerun()
                else:
                    st.error("Please write an answer.")
            if end_early:
                api.end_interview(session_id)
                for k in ["interview_active", "interview_questions", "current_question_idx", "interview_history", "interview_start_time", "interview_session_id", "interview_scores"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.interview_history:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Conversation History", "💬")
            for msg in st.session_state.interview_history[-10:]:
                role_class = "user-message" if msg.get("role") == "user" else "assistant-message"
                st.markdown(f"<div class='chat-message {role_class}'>{msg.get('content', '')}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
