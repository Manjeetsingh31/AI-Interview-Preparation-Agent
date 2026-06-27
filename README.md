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
- ⏳ HR Agent
- ⏳ Technical Agent
- ⏳ DSA Agent
- ⏳ Feedback Agent
- ⏳ Study Planner
- ⏳ FastAPI Backend (in progress)
- ⏳ Streamlit Frontend
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