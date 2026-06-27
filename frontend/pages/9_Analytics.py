import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css, stat_card
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_progress_bar
from components.charts import (
    radar_chart, bar_chart, pie_chart, line_chart, gauge_chart,
)
from utils.constants import APP_NAME


st.set_page_config(page_title=f"Analytics - {APP_NAME}", page_icon="📈", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>📈 Analytics Dashboard</h1>", unsafe_allow_html=True)

with st.spinner("Loading analytics..."):
    dashboard = api.get_dashboard()

if not dashboard:
    st.info("No analytics data available yet.")
    st.stop()

stats = dashboard.get("statistics", {})
summary = dashboard.get("summary", {})

col1, col2, col3, col4 = st.columns(4)
with col1:
    readiness = summary.get("overall_readiness_score", 0) or 0
    st.markdown(stat_card("Readiness", readiness, "%", "success" if readiness >= 70 else "warning"), unsafe_allow_html=True)
with col2:
    ats_score = summary.get("ats_score", 0) or 0
    st.markdown(stat_card("ATS Score", f"{ats_score:.0f}", "/100", "success" if ats_score >= 70 else "warning"), unsafe_allow_html=True)
with col3:
    avg_score = summary.get("average_score", 0) or 0
    st.markdown(stat_card("Avg Interview", f"{avg_score:.0f}", "/100", "info"), unsafe_allow_html=True)
with col4:
    sesh_count = summary.get("completed_sessions", 0)
    st.markdown(stat_card("Sessions", sesh_count, "", "primary"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

resume = stats.get("resume", {})
ats = stats.get("ats", {})
interview = stats.get("interview", {})
evaluation = stats.get("evaluation", {})
study = stats.get("study", {})
skills = stats.get("skills", {})
timeline = stats.get("timeline", {})
progress = stats.get("progress", {})

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Resume", "ATS", "Interview", "Study", "Skills", "Timeline"
])

with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Resume Analytics", "📄")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Resume Uploaded", "Yes" if resume.get("resume_uploaded") else "No")
    with col2: st.metric("Analysed", "Yes" if resume.get("resume_analysed") else "No")
    with col3: st.metric("Skills Found", resume.get("skills_count", 0))
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Missing Skills", resume.get("missing_skills_count", 0))
    with col2: st.metric("Strengths", resume.get("strengths_count", 0))
    with col3: st.metric("Weaknesses", resume.get("weaknesses_count", 0))
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("ATS Analytics", "🎯")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Current Score", f"{ats.get('current_score', 0):.0f}/100" if ats.get("current_score") else "N/A")
    with col2:
        impr = ats.get("improvement")
        st.metric("Improvement", f"{impr:+.0f}" if impr else "N/A")
    with col3: st.metric("Total Analyses", ats.get("total_analyses", 0))

    current = ats.get("current_score", 0) or 0
    gauge_chart(current, "ATS Score")

    missing_kw = ats.get("missing_keywords", [])
    if missing_kw:
        st.markdown("**Missing Keywords:**")
        st.markdown("".join(f"<span class='tag'>{k}</span>" for k in missing_kw), unsafe_allow_html=True)

    suggestions = ats.get("suggestions", [])
    if suggestions:
        st.markdown("**Suggestions:**")
        for s in suggestions:
            st.markdown(f"- {s}")
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Interview Analytics", "🎤")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Sessions", interview.get("total_sessions", 0))
    with col2: st.metric("Completed", interview.get("completed_sessions", 0))
    with col3: st.metric("Avg Score", f"{interview.get('average_score', 0):.0f}" if interview.get("average_score") else "N/A")
    with col4: st.metric("Questions", interview.get("questions_answered", 0))

    cat_dist = interview.get("category_distribution", {})
    if cat_dist:
        pie_chart(list(cat_dist.keys()), list(cat_dist.values()), "Category Distribution")

    diff_dist = interview.get("difficulty_distribution", {})
    if diff_dist:
        bar_chart(list(diff_dist.keys()), list(diff_dist.values()), "Difficulty Distribution")

    best = interview.get("best_score")
    worst = interview.get("worst_score")
    if best or worst:
        col1, col2 = st.columns(2)
        with col1: st.metric("Best Score", best or "N/A")
        with col2: st.metric("Worst Score", worst or "N/A")
    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Study Analytics", "📚")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Plans", study.get("total_plans", 0))
    with col2: st.metric("Active", study.get("active_plans", 0))
    with col3: st.metric("Completed", study.get("completed_plans", 0))
    with col4: st.metric("Completion", f"{study.get('completion_percentage', 0):.0f}%" if study.get("completion_percentage") else "N/A")

    col1, col2 = st.columns(2)
    with col1: st.metric("Tasks Completed", study.get("tasks_completed", 0))
    with col2: st.metric("Tasks Pending", study.get("tasks_pending", 0))

    completion = study.get("completion_percentage", 0) or 0
    gauge_chart(completion, "Study Completion")
    st.markdown("</div>", unsafe_allow_html=True)

with tab5:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Skill Analytics", "🛠️")
    top_skills = skills.get("top_skills", [])
    missing_skills = skills.get("missing_skills", [])
    weak_skills = skills.get("weak_skills", [])
    strong_skills = skills.get("strong_skills", [])

    if top_skills:
        st.markdown("**Top Skills:**")
        st.markdown("".join(f"<span class='tag'>{s}</span>" for s in top_skills), unsafe_allow_html=True)

    if strong_skills:
        st.markdown("**Strong Skills:**")
        st.markdown("".join(f"<span class='tag'>{s}</span>" for s in strong_skills), unsafe_allow_html=True)

    if weak_skills:
        st.markdown("**Weak Skills:**")
        st.markdown("".join(f"<span class='tag'>{s}</span>" for s in weak_skills), unsafe_allow_html=True)

    if missing_skills:
        st.markdown("**Missing Skills:**")
        st.markdown("".join(f"<span class='tag'>{s}</span>" for s in missing_skills), unsafe_allow_html=True)

    coverage = skills.get("skill_coverage")
    if coverage:
        gauge_chart(coverage, "Skill Coverage")

    freq = skills.get("skill_frequency", {})
    if freq:
        sorted_skills = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
        bar_chart([s[0] for s in sorted_skills], [s[1] for s in sorted_skills], "Skill Frequency")
    st.markdown("</div>", unsafe_allow_html=True)

with tab6:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Timeline Activity", "📅")
    period = st.selectbox("Period", ["daily", "weekly", "monthly"], key="timeline_period")
    timeline_data = api.get_timeline(period)
    if timeline_data:
        entries = timeline_data.get(period, timeline_data.get("daily", []))
        if entries:
            if period == "daily":
                dates = [e.get("date", e.get("day", f"Day {i+1}")) for i, e in enumerate(entries)]
                counts = [e.get("sessions", e.get("count", 0)) for e in entries]
                line_chart([{"date": d, "sessions": c} for d, c in zip(dates, counts)], x_col="date", y_col="sessions", title="Activity Timeline")
            elif period == "weekly":
                weeks = [f"Week {e.get('week', e.get('week_number', i+1))}" for i, e in enumerate(entries)]
                counts = [e.get("sessions", e.get("count", 0)) for e in entries]
                bar_chart(weeks, counts, "Weekly Activity")
            else:
                months = [e.get("month", f"Month {i+1}") for i, e in enumerate(entries)]
                counts = [e.get("sessions", e.get("count", 0)) for e in entries]
                bar_chart(months, counts, "Monthly Activity")
        else:
            st.info(f"No {period} activity data.")
    else:
        st.info("No timeline data available.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='card'>", unsafe_allow_html=True)
render_section_header("Readiness Score Breakdown", "🎯")
readiness_data = api.get_readiness()
if readiness_data:
    breakdown = readiness_data.get("breakdown", {})
    overall = readiness_data.get("overall_readiness_score", 0)
    gauge_chart(overall or 0, "Overall Readiness")

    if breakdown:
        categories = []
        scores = []
        for key, val in breakdown.items():
            label = key.replace("_", " ").title()
            score_val = val if isinstance(val, (int, float)) else val.get("score", 0)
            categories.append(label)
            scores.append(score_val)
        radar_chart(categories, scores, "Readiness by Pillar")

    formula = readiness_data.get("formula", "")
    if formula:
        st.caption(f"Formula: {formula}")
st.markdown("</div>", unsafe_allow_html=True)
