import streamlit as st
from utils.styles import stat_card, info_card


def render_stat_card(label, value, suffix="", color="primary", cols=1):
    st.markdown(stat_card(label, value, suffix, color), unsafe_allow_html=True)


def render_info_card(title, content, icon="ℹ️"):
    st.markdown(info_card(title, content, icon), unsafe_allow_html=True)


def render_section_header(title, icon="📌"):
    st.markdown(f"<h2 class='sub-header'>{icon} {title}</h2>", unsafe_allow_html=True)


def render_tags(tags):
    if not tags:
        return
    html = "<div>" + "".join(f"<span class='tag'>{t}</span>" for t in tags) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_progress_bar(percentage, label=None):
    p = min(max(percentage, 0), 100)
    html = f"""
    <div style="margin: 0.5rem 0;">
        {f'<div style="font-size: 0.85rem; color: #475569; margin-bottom: 0.25rem;">{label}</div>' if label else ''}
        <div class="progress-bar">
            <div class="progress-fill" style="width: {p}%;"></div>
        </div>
        <div style="font-size: 0.8rem; color: #64748B; text-align: right;">{p:.0f}%</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
