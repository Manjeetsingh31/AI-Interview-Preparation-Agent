import os

API_BASE_URL = os.getenv("API_BASE_URL", "https://ai-interview-preparation-agent.onrender.com")

APP_NAME = "AI Interview Preparation Agent"
APP_ICON = "🤖"

THEME = {
    "primary": "#6366F1",
    "secondary": "#8B5CF6",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#3B82F6",
    "dark": "#1E293B",
    "light": "#F8FAFC",
    "gray": "#94A3B8",
    "bg_light": "#F1F5F9",
    "bg_dark": "#0F172A",
    "card_bg": "#FFFFFF",
    "sidebar_bg": "#1E293B",
    "sidebar_text": "#CBD5E1",
    "sidebar_active": "#6366F1",
}

PAGE_ICONS = {
    "Dashboard": "📊",
    "Resume": "📄",
    "ATS": "🎯",
    "Interview Questions": "❓",
    "Mock Interview": "🎤",
    "Evaluation": "📝",
    "Study Plan": "📚",
    "Analytics": "📈",
}

STUDY_DURATIONS = {
    "7 Days": 7,
    "15 Days": 15,
    "30 Days": 30,
    "60 Days": 60,
}

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]
INTERVIEW_TYPES = ["HR", "Technical", "Coding", "Behavioral", "Mixed"]
QUESTION_COUNTS = [5, 10, 15, 20, 25, 30]
