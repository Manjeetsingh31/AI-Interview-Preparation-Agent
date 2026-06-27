import streamlit as st
from utils.api import api
from utils.session import check_auth, init_session
from utils.styles import load_css
from components.sidebar import render_sidebar
from components.cards import render_section_header, render_progress_bar, render_stat_card
from components.charts import pie_chart, bar_chart
from utils.constants import APP_NAME, STUDY_DURATIONS


st.set_page_config(page_title=f"Study Plan - {APP_NAME}", page_icon="📚", layout="wide")
init_session()
check_auth()
load_css()
render_sidebar()

st.markdown("<h1 class='main-header'>📚 Study Plan</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Generate Plan", "My Plans", "Progress"])

with tab1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    render_section_header("Generate New Study Plan", "🆕")
    evaluation_id = st.text_input("Evaluation ID (optional)", placeholder="Leave empty to generate without prior evaluation", key="sp_eval_id")
    target_role = st.text_input("Target Role", value="Software Engineer", key="sp_role")
    target_company = st.text_input("Target Company (optional)", value="", key="sp_company")
    duration_label = st.selectbox("Study Duration", list(STUDY_DURATIONS.keys()), index=2)
    duration = STUDY_DURATIONS[duration_label]

    if st.button("Generate Study Plan", type="primary", use_container_width=True):
        ev_id = evaluation_id.strip() if evaluation_id.strip() else None
        company = target_company.strip() if target_company.strip() else None
        result = api.generate_study_plan(
            evaluation_id=ev_id,
            target_role=target_role,
            target_company=company,
            study_duration=duration,
        )
        if result:
            st.success("Study plan generated successfully!")
            st.session_state.study_plan_id = result.get("id")
            st.session_state.current_study_plan = result
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    current_plan = st.session_state.get("current_study_plan")
    if current_plan:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Latest Plan", "📋")
        pct = current_plan.get("completion_percentage", 0)
        render_progress_bar(pct, f"Progress: {current_plan.get('target_role', 'N/A')}")

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Duration", f"{current_plan.get('study_duration', 0)} days")
        with col2: st.metric("Status", current_plan.get("status", "N/A").title())
        with col3: st.metric("Role", current_plan.get("target_role", "N/A"))

        weak = current_plan.get("weak_topics", [])
        strong = current_plan.get("strong_topics", [])
        if weak or strong:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Areas to Focus:**")
                for t in (weak or []):
                    st.markdown(f"- {t}")
            with col2:
                st.markdown("**Strong Areas:**")
                for t in (strong or []):
                    st.markdown(f"- {t}")

        daily_tasks = current_plan.get("daily_tasks", [])
        weekly_tasks = current_plan.get("weekly_tasks", [])
        coding = current_plan.get("coding_practice", [])
        projects = current_plan.get("recommended_projects", [])
        certs = current_plan.get("recommended_certifications", [])
        resources = current_plan.get("recommended_resources", [])

        if daily_tasks:
            st.markdown("### Daily Tasks")
            for task in daily_tasks[:5]:
                st.markdown(f"**Day {task.get('day', '?')}** - {task.get('topic', '')}")
                st.caption(f"{task.get('coding_task', '')}")
        if weekly_tasks:
            st.markdown("### Weekly Tasks")
            for week in weekly_tasks:
                st.markdown(f"**Week {week.get('week', '?')}** - {week.get('focus_area', '')}")
        if coding:
            st.markdown("### Coding Practice")
            for c in coding:
                st.markdown(f"- **{c.get('topic', '')}** ({c.get('platform', '')})")
        if projects:
            st.markdown("### Recommended Projects")
            for p in projects:
                st.markdown(f"- **{p.get('title', '')}**: {p.get('description', '')}")
        if certs:
            st.markdown("### Certifications")
            for c in certs:
                st.markdown(f"- **{c.get('name', '')}** ({c.get('provider', '')})")
        if resources:
            st.markdown("### Resources")
            for r in resources:
                st.markdown(f"- **{r.get('title', '')}** ({r.get('type', '')})")

        st.markdown("</div>", unsafe_allow_html=True)

        if current_plan.get("id"):
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            render_section_header("Update Progress", "📈")
            new_pct = st.slider("Completion %", 0, 100, int(pct), key="sp_progress_slider")
            new_status = st.selectbox("Status", ["active", "completed", "paused"], index=0 if pct < 100 else 1)
            if st.button("Update Progress", type="primary", use_container_width=True):
                result = api.update_study_plan_progress(current_plan["id"], new_pct, new_status)
                if result:
                    st.success("Progress updated!")
                    current_plan["completion_percentage"] = new_pct
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Study Plan History", "📜")
        history = api.get_study_plan_history()
        if history and history.get("plans"):
            for plan in history["plans"]:
                pct = plan.get("completion_percentage", 0)
                st.markdown(f"**{plan.get('target_role', 'N/A')}** at {plan.get('target_company', 'N/A') or 'N/A'}")
                render_progress_bar(pct, f"{plan.get('study_duration', 0)}d - {plan.get('status', 'N/A').title()}")
                if st.button(f"View →", key=f"view_plan_{plan.get('id', '')}"):
                    plan_detail = api.get_study_plan(plan["id"])
                    if plan_detail:
                        st.session_state.current_study_plan = plan_detail
                        st.session_state.study_plan_id = plan["id"]
                        st.rerun()
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        else:
            st.info("No study plans yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_section_header("Dashboard Progress", "📊")
        dash = api.get_study_plan_dashboard()
        if dash:
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Plans", dash.get("total_plans", 0))
            with col2: st.metric("Avg Completion", f"{dash.get('average_completion', 0):.0f}%")
            with col3:
                by_status = dash.get("plans_by_status", {})
                st.metric("Active", by_status.get("active", 0))
            with col4: st.metric("Completed", by_status.get("completed", 0))

            by_status = dash.get("plans_by_status", {})
            if by_status:
                pie_chart(list(by_status.keys()), list(by_status.values()), "Plans by Status")
        else:
            st.info("No dashboard data yet.")
        st.markdown("</div>", unsafe_allow_html=True)
