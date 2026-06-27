# AI-Interview-Preparation-Agent
A production-ready Multi-Agent AI Interview Preparation System built with Google ADK, Gemini, FastAPI, Streamlit, SQLite, and MCP as part of the Kaggle 5-Day AI Agents: Intensive Vibe Coding Capstone with Google.
# 🚀 AI Interview Preparation Agent

A production-ready **Multi-Agent AI Interview Preparation System** built using **Google Agent Development Kit (ADK), Gemini, FastAPI, Streamlit, SQLite, and MCP**.

This project is being developed as part of the **Kaggle 5-Day AI Agents: Intensive Vibe Coding Capstone with Google**.

## 🎯 Project Objective

Build an intelligent AI Interview Assistant that helps students and job seekers prepare for interviews using multiple specialized AI agents.

## ✨ Features

- 📄 Resume Analysis Agent (Google ADK + Gemini 2.5 Flash)
- 📊 ATS Scoring Engine (Google ADK + Gemini 2.5 Flash)
- ❓ Interview Question Generator (Google ADK + Gemini 2.5 Flash)
- 🤝 HR Interview Agent
- 💻 Technical Interview Agent
- 🧠 DSA Interview Agent
- 🎯 Mock Interview Multi-Agent System (Google ADK + Gemini 2.5 Flash)
- 📊 AI Feedback Agent
- 📅 Personalized Study Planner
- 🔄 Multi-Agent Workflow using Google ADK
- 🔌 MCP Tool Integration
- ⚡ FastAPI Backend
- 🎨 Streamlit Frontend
- 💾 SQLite Database

## 🛠️ Tech Stack

- Python
- Google Agent Development Kit (ADK)
- Gemini API
- FastAPI
- Streamlit
- SQLite
- MCP
- Git & GitHub

## 📈 Project Status

- ✅ Project Planning
- ✅ Development Environment Setup
- ✅ Google ADK Setup
- ✅ Database Design (SQLite + SQLAlchemy)
- ✅ Resume Upload & Parsing
- ✅ Resume Analysis Agent (ADK + Gemini)
- ✅ ATS Scoring Engine
- ✅ Interview Question Generator Agent
- ✅ Mock Interview Multi-Agent System
- ✅ Evaluation & Feedback Agent
- ✅ Personalized Study Plan Agent
- ✅ Analytics Dashboard
- ✅ Streamlit Frontend (9 pages)
- ⏳ Testing & Deployment

## 📡 API Endpoints

### Resume Analysis

| Method | Endpoint                | Description                        |
|--------|-------------------------|------------------------------------|
| POST   | /api/resumes/analyze    | Upload & analyse a resume (PDF/txt) |

### ATS Scoring

| Method | Endpoint          | Description                            |
|--------|-------------------|----------------------------------------|
| POST   | /api/ats/analyze  | Score a resume against ATS criteria    |
| GET    | /api/ats/history  | List ATS scores for the current user   |
| GET    | /api/ats/{id}     | Retrieve a specific ATS score          |

### Interview Questions

| Method | Endpoint                                           | Description                                      |
|--------|----------------------------------------------------|--------------------------------------------------|
| POST   | /api/interview/questions/generate                  | Generate personalised interview questions         |
| GET    | /api/interview/questions/history                   | List all generated questions for the current user |
| GET    | /api/interview/questions/by-analysis/{id}          | List questions for a specific resume analysis     |

### Auth

| Method | Endpoint             | Description              |
|--------|----------------------|--------------------------|
| POST   | /api/auth/register   | Register a new user      |
| POST   | /api/auth/login      | Login and get a token    |

### Mock Interview (Production Multi-Agent System)

| Method | Endpoint                             | Description                                      |
|--------|--------------------------------------|--------------------------------------------------|
| POST   | /api/interview/start                 | Start a new interview session (generates Q1)     |
| POST   | /api/interview/answer                | Submit answer, get next question + evaluation     |
| POST   | /api/interview/end                   | End an active interview session                   |
| GET    | /api/interview/{session_id}          | Get all turns for a session                       |
| GET    | /api/interview/history               | List interview turn history for the current user  |
| GET    | /api/interview/transcript/{session_id}| Get full conversation transcript                  |

### Sessions

| Method | Endpoint                        | Description                          |
|--------|---------------------------------|--------------------------------------|
| POST   | /api/sessions/create            | Create a new interview session       |
| GET    | /api/sessions/{session_id}      | Get session details                  |
| POST   | /api/sessions/{session_id}/turn | Submit a chat turn in the session    |

## 🧠 Interview Question Generator

Generates personalised interview questions using **Google ADK + Gemini 2.5 Flash**.

**Request:**
```json
POST /api/interview/questions/generate
{
  "resume_analysis_id": "uuid",
  "company": "Google",
  "role": "Software Engineer",
  "interview_type": "Mixed",
  "difficulty": "Medium",
  "number_of_questions": 10
}
```

**Response:**
```json
{
  "questions": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "resume_analysis_id": "uuid",
      "company": "Google",
      "role": "Software Engineer",
      "interview_type": "Mixed",
      "difficulty": "Medium",
      "question_type": "Technical",
      "question": "Explain Python decorators.",
      "expected_answer": "Decorators are functions...",
      "hints": ["Functions", "Closures"],
      "follow_up": "How are decorators implemented internally?",
      "tags": ["python", "decorators"],
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**Question Types:** HR, Technical, Coding, Behavioral, Resume, System Design, Project Discussion

**Generation Rules:**
- Uses resume skills, projects, experience, and education for context
- Balances question types across the interview
- Questions progress from easier to harder
- Each question includes hints, expected answer, follow-up, and tags
- No duplicate questions

## 🎯 Mock Interview Multi-Agent System

The Production Mock Interview Multi-Agent System conducts a complete interview exactly like a real interviewer using **Google ADK + Gemini 2.5 Flash**.

### Supported Interview Types

- **HR** — Cultural fit, motivation, career goals, teamwork
- **Technical** — System design, architecture, technology choices
- **Coding** — Algorithms, data structures, code quality, problem-solving
- **Behavioural** — Past experiences, leadership, conflict resolution
- **Mixed** — Blend of all types as appropriate

### Architecture

```
Client ──POST/GET──► FastAPI Route ──► ADK Agent ──► Gemini 2.5 Flash
                          │                         │
                          ▼                         ▼
                    Database                    Structured Turn
                 (ResumeADK, ATS,          (InterviewAgentTurn)
                  InterviewTurn)
                          │
                          ▼
                    JSON Response
```

### Interview Flow

1. **POST /api/interview/start** — Loads resume analysis, ATS analysis, and generated questions; creates a session; generates the first question
2. **POST /api/interview/answer** — Submits the candidate's answer; agent evaluates and scores it; generates the next question or follow-up; maintains conversation memory
3. The cycle repeats until the configured number of questions is asked
4. **POST /api/interview/end** — Ends the session and returns the transcript summary

### Key Features

- **Adaptive questioning** based on resume, ATS weaknesses, skills, projects, education, previous answers, previous questions, difficulty level, company, and job role
- **Intelligent follow-up logic**: weak answer → clarification; strong answer → deeper question; partial answer → one follow-up
- **Difficulty progression**: increases every 3-4 correct answers, decreases if score < 40
- **Category switching**: never asks two same-category questions consecutively
- **Conversation memory**: maintains full context across all turns
- **Never repeats questions**

### Supported Companies

Generic, Google, Microsoft, Amazon, Meta, Apple, Netflix, Oracle, IBM, Adobe, TCS, Infosys, Wipro, Accenture, Capgemini, Deloitte, Cognizant

### Database Schema

**interview_turns** table:
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Primary key |
| session_id | FK → interview_sessions | Parent session |
| user_id | FK → users | Candidate |
| resume_analysis_id | FK → resume_analyses_adk | Resume context |
| question_number | Integer | Sequential Q number |
| question | Text | Interview question |
| candidate_answer | Text | Candidate's answer |
| follow_up | Text | Follow-up question |
| difficulty | String | Easy / Medium / Hard |
| category | String | HR / Technical / Coding / Behavioural |
| tags | JSON | Keyword tags |
| expected_answer | Text | Ideal answer |
| evaluation | Text | AI evaluation |
| score | Integer | Score 0-100 |
| response_time | Integer | Seconds taken |
| created_at | DateTime | UTC timestamp |

## 🎨 Streamlit Frontend

The frontend is a multi-page Streamlit application in the `frontend/` directory.

### Setup

```bash
cd frontend
pip install -r requirements.txt
```

### Running

Start the backend first, then:

```bash
cd frontend
streamlit run app.py
```

### Pages

| # | Page | Description |
|---|------|-------------|
| 1 | Login | Email/password login and registration |
| 2 | Dashboard | Overview with stats, quick actions, study progress |
| 3 | Resume | Upload PDF/TXT, analyze, view extracted data |
| 4 | ATS | Run ATS analysis, view scores, sections, suggestions |
| 5 | Interview Questions | Generate tailored questions with filters |
| 6 | Mock Interview | Real-time chat interface with timer and scoring |
| 7 | Evaluation | Generate and view interview evaluations |
| 8 | Study Plan | Generate 7/15/30/60-day plans, track progress |
| 9 | Analytics | Charts, readiness score, timeline, skill analysis |

### Structure

```
frontend/
├── app.py                      # Main entry point with routing
├── pages/
│   ├── 1_Login.py              # Authentication (login/register)
│   ├── 2_Dashboard.py          # Dashboard overview
│   ├── 3_Resume.py             # Resume upload & analysis
│   ├── 4_ATS.py                # ATS scoring & display
│   ├── 5_Interview_Questions.py# Question generation
│   ├── 6_Mock_Interview.py     # Interactive mock interview
│   ├── 7_Evaluation.py         # Interview evaluation
│   ├── 8_Study_Plan.py         # Study plan generation
│   └── 9_Analytics.py          # Full analytics dashboard
├── components/
│   ├── sidebar.py              # Reusable sidebar navigation
│   ├── cards.py                # Stat cards, tags, progress bars
│   └── charts.py               # Plotly charts (radar, bar, pie, line, gauge)
├── utils/
│   ├── api.py                  # API client (all 40+ endpoints)
│   ├── constants.py            # Theme, config, constants
│   ├── session.py              # Session state management
│   └── styles.py               # CSS and HTML components
├── assets/
│   └── style.css               # Custom styles
└── requirements.txt            # Python dependencies
```

### Tech Stack

- **Streamlit** — UI framework
- **requests** — HTTP client for backend APIs
- **plotly** — Interactive charts (radar, bar, pie, line, gauge)
- **pandas** — Data manipulation

## 🏆 Kaggle Capstone

This project is developed for the **Kaggle 5-Day AI Agents: Intensive Vibe Coding Capstone with Google** and demonstrates:

- Multi-Agent AI Systems
- Google ADK
- Agent Skills
- MCP Integration
- Secure AI Workflows
- Real-world AI Application Design

## 📜 License

MIT License