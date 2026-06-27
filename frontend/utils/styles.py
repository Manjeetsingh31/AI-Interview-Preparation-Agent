import streamlit as st
from utils.constants import THEME


def load_css():
    css = """
    <style>
        .stApp { background-color: #F8FAFC; }
        .main-header { font-size: 2rem; font-weight: 700; color: #1E293B; margin-bottom: 1rem; }
        .sub-header { font-size: 1.3rem; font-weight: 600; color: #334155; margin-bottom: 0.75rem; }
        .card { background: #FFFFFF; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1rem; border: 1px solid #E2E8F0; }
        .stat-card { background: linear-gradient(135deg, #6366F1, #8B5CF6); border-radius: 12px; padding: 1.25rem; color: white; text-align: center; }
        .stat-value { font-size: 2rem; font-weight: 700; }
        .stat-label { font-size: 0.85rem; opacity: 0.9; }
        .success-text { color: #10B981; font-weight: 600; }
        .warning-text { color: #F59E0B; font-weight: 600; }
        .danger-text { color: #EF4444; font-weight: 600; }
        .info-text { color: #3B82F6; font-weight: 600; }
        .metric-row { display: flex; gap: 1rem; flex-wrap: wrap; }
        .chat-message { padding: 1rem; border-radius: 12px; margin-bottom: 0.5rem; }
        .user-message { background: #6366F1; color: white; margin-left: 2rem; }
        .assistant-message { background: #F1F5F9; color: #1E293B; margin-right: 2rem; border: 1px solid #E2E8F0; }
        .tag { display: inline-block; background: #E0E7FF; color: #4338CA; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; margin: 0.15rem; }
        .btn-primary { background: #6366F1; color: white; border: none; padding: 0.5rem 1.5rem; border-radius: 8px; cursor: pointer; }
        .divider { margin: 1.5rem 0; border: 0; border-top: 1px solid #E2E8F0; }
        .sidebar-title { font-size: 1.1rem; font-weight: 600; color: #F8FAFC; padding: 1rem 0; }
        .sidebar-item { padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; color: #CBD5E1; transition: all 0.2s; }
        .sidebar-item:hover { background: #334155; color: #F8FAFC; }
        .sidebar-item.active { background: #6366F1; color: white; }
        .progress-bar { height: 8px; background: #E2E8F0; border-radius: 999px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #6366F1, #8B5CF6); border-radius: 999px; transition: width 0.5s; }
        .score-ring { width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def stat_card(label, value, suffix="", color="primary"):
    colors = {
        "primary": "linear-gradient(135deg, #6366F1, #8B5CF6)",
        "success": "linear-gradient(135deg, #10B981, #34D399)",
        "warning": "linear-gradient(135deg, #F59E0B, #FBBF24)",
        "danger": "linear-gradient(135deg, #EF4444, #F87171)",
        "info": "linear-gradient(135deg, #3B82F6, #60A5FA)",
    }
    bg = colors.get(color, colors["primary"])
    html = f"""
    <div style="background: {bg}; border-radius: 12px; padding: 1.25rem; color: white; text-align: center; min-width: 150px;">
        <div style="font-size: 2rem; font-weight: 700;">{value}{suffix}</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">{label}</div>
    </div>
    """
    return html


def info_card(title, content, icon="ℹ️"):
    html = f"""
    <div class="card">
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #1E293B;">{title}</span>
        </div>
        <div style="color: #475569; line-height: 1.6;">{content}</div>
    </div>
    """
    return html
