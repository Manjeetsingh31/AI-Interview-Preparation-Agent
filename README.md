# AI Interview Preparation Agent

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?logo=googlegemini&logoColor=white)
![Google ADK](https://img.shields.io/badge/Google_ADK-2.3+-4285F4?logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Pydantic v2](https://img.shields.io/badge/Pydantic_v2-E92063?logo=pydantic&logoColor=white)

A multi-agent AI system that helps job seekers prepare for interviews through resume analysis, ATS scoring, personalized question generation, live mock interviews, performance evaluation, and adaptive study planning.

---

## Table of Contents

- [Overview](#overview)
- [Project Highlights](#project-highlights)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [AI Agent Workflow](#ai-agent-workflow)
- [Tech Stack](#tech-stack)
- [Project Workflow](#project-workflow)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Screenshots](#screenshots)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)

---

## Overview

AI Interview Preparation Agent is an end-to-end multi-agent AI platform designed to help job seekers prepare for technical and behavioral interviews through resume analysis, ATS scoring, AI-powered mock interviews, interview evaluation, and personalized study plans.

---

## Project Highlights

- **Six specialized AI agents** orchestrated via Google ADK with structured output schemas
- **Adaptive mock interview** system with real-time difficulty adjustment and category switching
- **Readiness score** that aggregates resume quality, ATS compatibility, interview performance, and study progress
- **Interactive dashboard** with Plotly visualizations including radar charts, gauge charts, and timeline analytics
- **PDF-native resume parsing** using PyMuPDF with Gemini-powered structured data extraction
- **Comprehensive evaluation** across six performance dimensions with hire decision recommendations

---

## 🚀 Project Status

Current Status: Active Development

Core modules completed:

- Resume Analysis
- ATS Analysis
- Mock Interview
- Interview Evaluation
- Study Plan
- Dashboard

---

## Problem Statement

Job seekers face several challenges during interview preparation:

- **No objective feedback** on resume quality and ATS compatibility
- **Generic interview questions** that do not target specific roles, companies, or skill gaps
- **No real-time practice** environment that simulates actual interview conditions
- **No structured evaluation** identifying strengths and weaknesses after practice
- **No personalized study roadmap** focused on areas needing improvement

---

## Solution

This system addresses each challenge with a dedicated AI agent:

1. **Resume Analysis Agent** — extracts structured data from uploaded resumes
2. **ATS Scoring Agent** — evaluates the resume against ATS criteria and job role matching
3. **Interview Question Agent** — generates personalized questions based on resume, target role, and company
4. **Mock Interview Agent** — conducts a full adaptive interview with intelligent follow-ups
5. **Interview Evaluation Agent** — scores performance across six dimensions post-interview
6. **Study Plan Agent** — creates a day-by-day learning roadmap targeting weak areas

---

## Key Features

- **Resume Upload & Parsing** — PDF and TXT support with Gemini-native document analysis
- **Structured Resume Extraction** — name, contact, skills, education, experience, projects, certifications
- **ATS Scoring** — section-level evaluation across 11 categories with job role matching and skill gap analysis
- **Personalized Question Generation** — contextual questions based on resume projects, skills, target company, and role
- **Adaptive Mock Interviews** — real-time difficulty progression, category switching, and intelligent follow-up logic
- **Multi-Dimension Evaluation** — technical, communication, problem-solving, confidence, behavioral, and coding scores
- **Personalized Study Plans** — 7, 15, 30, or 60-day roadmaps with daily tasks, projects, and resources
- **Analytics Dashboard** — readiness score, skill analysis, timeline, interview statistics, and ATS trends
- **Interactive Charts** — radar, bar, pie, line, and gauge visualizations using Plotly
- **Session History** — full interview transcripts and evaluation history

---

## System Architecture

```
                           ┌──────────────────────────┐
                           │     Streamlit Frontend    │
                           │   (9-page application)   │
                           └───────────┬──────────────┘
                                       │ HTTP (requests)
                                       ▼
                           ┌──────────────────────────┐
                           │   FastAPI Backend Server  │
                           │   (CORS-enabled, ASGI)   │
                           └───┬──────┬──────┬──────┬──┘
                               │      │      │      │
                    ┌──────────┘      │      │      └──────────┐
                    ▼                  ▼      ▼                  ▼
            ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
            │  API Routes │   │  CRUD Layer │   │  Services   │
            │  (8 files)  │──▶│  (17 files) │   │  (3 files)  │
            └─────────────┘   └──────┬──────┘   └──────┬──────┘
                                     │                  │
                                     ▼                  ▼
                            ┌──────────────────────────────┐
                            │   SQLite + SQLAlchemy ORM    │
                            │  (18 tables, Pydantic v2)    │
                            └──────────────────────────────┘
                                                │
                ┌───────────────────────────────┼───────────────────────────────┐
                ▼                               ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
    │  Google ADK Agents  │         │    Gemini 2.5 Flash │         │   Legacy Fallback   │
    │  (6 production)     │────────▶│    (LLM Inference)  │         │   Agents (4 files)   │
    │  + 4 legacy         │         │                     │         │                     │
    └─────────────────────┘         └─────────────────────┘         └─────────────────────┘
```

---

## AI Agent Workflow

All agents use Google ADK with Gemini 2.5 Flash, structured output schemas (Pydantic v2), and `InMemorySessionService` for stateless execution.

### Resume Analysis Agent

```
User Uploads Resume (PDF/TXT)
        │
        ▼
  PyMuPDF extracts text
        │
        ▼
  ADK Agent (resume_agent)
  ├── output_schema: ResumeData
  ├── temperature: 0.1
  └── Extracts: full_name, email, phone, skills,
                technical_skills, soft_skills, education,
                experience, projects, certifications, languages
        │
        ▼
  Structured JSON → Database (resume_analyses_adk)
```

- Singleton agent with 5-attempt retry logic via tenacity
- Returns strictly typed Pydantic v2 schema
- Validates every field; uses empty defaults for missing data

### ATS Scoring Agent

```
ResumeData JSON (from Resume Analysis Agent)
        │
        ▼
  ADK Agent (ats_agent)
  ├── output_schema: AtsOutput
  ├── temperature: 0.2
  └── Scoring weightage (100 points):
        Technical Skills (30), Projects (20), Experience (15),
        Education (10), Structure (10), Certifications (5),
        Achievements (5), Grammar & Readability (5)
        │
        ▼
  Structured JSON → Database (ats_scores)
  ├── Section scores with reasons & recommendations
  ├── Job role matching (7 roles, 0-100%)
  ├── Skill gap analysis (missing technologies, languages,
  │   frameworks, cloud, DevOps, databases, soft skills)
  └── Improvement suggestions
```

- Evaluates 11 sections individually with per-section reasoning
- Matches resume against 7 job roles: Python Developer, Backend Developer, AI Engineer, ML Engineer, Data Analyst, Software Engineer, Full Stack Developer
- Categorizes skill gaps into 7 categories for targeted improvement

### Interview Question Agent

```
ResumeData + Parameters (company, role, type, difficulty, count)
        │
        ▼
  ADK Agent (interview_question_agent)
  ├── output_schema: InterviewQuestionList
  ├── temperature: 0.4
  └── Rules:
        - Uses resume projects and skills for personalization
        - Balances question types (HR, Technical, Coding, Behavioral,
          Resume, System Design, Project Discussion)
        - Progressive difficulty (easier → harder)
        - No duplicate questions within a batch
        │
        ▼
  Structured JSON → Database (interview_questions)
  ├── question, expected_answer, hints, follow_up, tags
  └── Supports: Generic, Google, Microsoft, Amazon, Meta, Apple,
                Netflix, Oracle, IBM, Adobe, TCS, Infosys, Wipro,
                Accenture, Capgemini, Deloitte, Cognizant
```

- Each question includes hints, expected answer, follow-up question, and tags
- Generates company-specific questions relevant to the target organization
- Question types adapt based on the selected interview type

### Mock Interview Agent

```
/start ──→ Load ResumeData + ATS + Generated Questions
            │
            ▼
      ADK Agent (interview_agent)
      ├── output_schema: InterviewAgentTurn
      ├── temperature: 0.3
      ├── Adaptive difficulty (↑ every 3-4 correct, ↓ if score < 40)
      ├── Category switching (no consecutive same-category)
      └── Follow-up logic:
            score < 40  → clarification question
            score ≥ 80  → deeper follow-up
            otherwise   → one follow-up, then next question
            │
            ▼   Loop until all questions asked or user ends
      /answer ──→ Submit answer → evaluate → next question
            │
            ▼
      /end ──→ Return transcript summary
```

- Supports 5 interview types: HR, Technical, Coding, Behavioural, Mixed
- Conversation memory via previous turns passed in each prompt
- Score tracking with automatic difficulty adjustment every 3-4 turns
- Company-specific expectations based on supported company list
- Never repeats questions across the session

### Interview Evaluation Agent

```
/end (triggers evaluation)
        │
        ▼
  Load full transcript + ResumeData + ATS scores
        │
        ▼
  ADK Agent (evaluation_agent)
  ├── output_schema: InterviewEvaluationOutput
  ├── Lazy-initialized singleton
  └── Evaluates 6 dimensions (0-100 each):
        Technical, Communication, Problem Solving,
        Confidence, Behavioral, Coding
        │
        ▼
  Structured JSON → Database (interview_evaluations)
  ├── Overall composite score (0-100)
  ├── Strengths & weaknesses lists
  ├── Missed topics & strong topics
  ├── Improvement suggestions
  ├── Hire decision: Strong Hire / Hire / Borderline / Reject
  ├── Difficulty level: Easy / Medium / Hard
  └── Human-readable evaluation summary
```

- Post-interview analysis runs automatically after session end
- Uses the complete conversation transcript for holistic assessment
- Provides both quantitative scores and qualitative feedback
- Fallback implementation ensures robustness when ADK is unavailable

### Study Plan Agent

```
Evaluation + ResumeData + ATS scores
        │
        ▼
  ADK Agent (study_plan_agent)
  ├── output_schema: StudyPlanOutput
  ├── Lazy-initialized singleton
  └── Plan durations:
        7 days  → Rapid Preparation
        15 days → Focused Preparation
        30 days → Comprehensive Preparation
        60 days → Placement Preparation
        │
        ▼
  Structured JSON → Database (study_plans_ai)
  ├── Roadmap overview with weekly focus areas
  ├── Day-by-day tasks (topic, difficulty, time, coding task,
  │   reading task, revision task, goal)
  ├── Weekly goals and milestones with mini-projects
  ├── Coding practice recommendations (platform, difficulty)
  ├── Interview practice recommendations (questions, tips)
  ├── Recommended projects for missing skills
  ├── Recommended certifications for target role
  └── Learning resources (docs, books, videos, courses)
```

- Prioritizes weakest topics first, builds on strengths with advanced material
- Generates a comprehensive learning roadmap with specific daily tasks
- Includes mock interview scheduling recommendations
- Fallback plan generator ensures the feature works without ADK

### Readiness Score

The **Readiness Score** aggregates all agent outputs into a single metric:

```
Readiness = (resume × 0.15) + (ats × 0.20) + (interview × 0.25)
          + (evaluation × 0.25) + (study × 0.15)
```

---

## Tech Stack

### Frontend

| Technology | Purpose |
|-----------|---------|
| Streamlit | Web application framework |
| Plotly | Interactive data visualizations |
| Pandas | Data manipulation |
| Requests | HTTP client for API communication |
| Pillow | Image processing |

### Backend

| Technology | Purpose |
|-----------|---------|
| Python | Runtime |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| SQLAlchemy | ORM and database abstraction |
| Pydantic | Data validation and serialization |
| PyMuPDF | PDF text extraction |
| python-multipart | File upload handling |

### AI & Agents

| Technology | Purpose |
|-----------|---------|
| Google ADK | Agent Development Kit for multi-agent orchestration |
| Gemini | LLM for all agent inference |
| google-genai | Gemini SDK client |
| tenacity | Retry logic with exponential backoff |

### Database

| Technology | Purpose |
|-----------|---------|
| SQLite | Embedded database (zero configuration) |
| SQLAlchemy | ORM with 18 model tables |

---

## Project Workflow

```mermaid
flowchart TD
    A[User] -->|Upload Resume PDF/TXT| B[FastAPI: /api/resumes/upload]
    B --> C[Extract Text via PyMuPDF]
    C --> D[Resume Analysis ADK Agent]
    D -->|Structured ResumeData| E[SQLite Database]
    D --> F[ATS Scoring ADK Agent]
    F -->|AtsOutput| E
    D --> G[Interview Question ADK Agent]
    G -->|Personalized Questions| E

    H[User] -->|Start Interview| I[FastAPI: /api/interview/start]
    I --> J[Mock Interview ADK Agent]
    J -->|First Question| K[User Answers]
    K -->|/api/interview/answer| L[Agent Evaluates + Scores]
    L -->|Score < 40?| M[Clarification Follow-up]
    L -->|Score >= 80?| N[Deeper Follow-up]
    L -->|Otherwise| O[Next Question]
    M --> K
    N --> K
    O -->|Loop| K
    O -->|All questions done| P[/api/interview/end]
    P --> Q[Interview Evaluation ADK Agent]
    Q -->|6-Dimension Scores| E
    Q --> R[Study Plan ADK Agent]
    R -->|Personalized Roadmap| E

    S[User] -->|View Dashboard| T[FastAPI: /api/dashboard/*]
    T --> U[Aggregate All Data]
    U --> V[Readiness Score]
    V --> W[Streamlit UI: Charts + Stats]

    style A fill:#4CAF50,color:white
    style H fill:#4CAF50,color:white
    style S fill:#4CAF50,color:white
    style D fill:#4285F4,color:white
    style F fill:#4285F4,color:white
    style G fill:#4285F4,color:white
    style J fill:#4285F4,color:white
    style Q fill:#4285F4,color:white
    style R fill:#4285F4,color:white
    style E fill:#FF6F00,color:white
    style W fill:#FF4B4B,color:white
```

---

## Folder Structure

```
AI-Interview-Preparation-Agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── crud/
│   │   ├── services/
│   │   │   └── agents/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   ├── components/
│   ├── utils/
│   ├── assets/
│   └── app.py
├── tests/
├── .agents/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.13+
- Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate    # Windows
source venv/bin/activate   # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=sqlite:///./interview_agent.db
SECRET_KEY=supersecretkeyforinterviewagent
GEMINI_API_KEY=your_gemini_api_key_here
```

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite database path (default: `sqlite:///./interview_agent.db`) |
| `SECRET_KEY` | Secret key for authentication |
| `GEMINI_API_KEY` | Your Google Gemini API key from Google AI Studio |

### Run Commands

Start the backend server:

```bash
cd backend
.\venv\Scripts\activate    # Windows
source venv/bin/activate   # Linux / macOS
uvicorn app.main:app --reload --port 8000
```

Start the frontend application (in a new terminal):

```bash
cd frontend
streamlit run app.py
```

Access the application at `http://localhost:8501`.

---

## API Endpoints

| Module | Description |
|--------|-------------|
| Authentication | User registration and login |
| Resume Analysis | Resume upload and AI analysis |
| ATS Analysis | ATS scoring and recommendations |
| Interview | Mock interview session management |
| Evaluation | Interview evaluation and feedback |
| Study Plan | Personalized study plan generation |
| Dashboard | Analytics and progress tracking |

---

## Screenshots

> Screenshots will be added here after deployment.

| Page | Description |
|------|-------------|
| Dashboard | Overview with readiness score, stats, and quick actions |
| Resume | Resume upload, analysis results, and extracted data |
| ATS | ATS score breakdown, job matching, and skill gaps |
| Interview Questions | Generated questions with filters and export |
| Mock Interview | Real-time chat interface with timer and scoring |
| Evaluation | Post-interview evaluation with dimension scores |
| Study Plan | Generated roadmap with daily tasks and progress |
| Analytics | Charts for skills, timeline, and performance trends |

---

## 🎥 Demo

This project includes the following end-to-end workflow:

- User Authentication
- Resume Upload & Analysis
- ATS Resume Scoring
- AI Mock Interview
- AI Interview Evaluation
- Personalized Study Plan
- Dashboard Analytics

> Screenshots and demo video will be added before the final submission.

---

## Future Improvements

- **JWT-based authentication** — replace the current mock auth with proper JWT tokens and OAuth integration
- **PostgreSQL support** — add production-grade database support alongside SQLite
- **Multi-language support** — extend the agents to support interviews in additional languages
- **Voice-based interviews** — integrate speech-to-text and text-to-speech for verbal mock interviews
- **Code execution environment** — embed a code runner for live coding interview questions
- **Interview scheduling** — calendar integration for scheduled mock interview sessions
- **Export functionality** — PDF export for study plans and evaluation reports
- **Docker deployment** — containerized setup with docker-compose for one-command deployment
- **CI/CD pipeline** — automated testing and deployment with GitHub Actions
- **Rate limiting & caching** — API rate limiting and response caching for production scaling

---

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure tests pass and follow the existing code style.

---

## 👨‍💻 Author

**Manjeet Kumar**

Computer Science & Design Engineering Student

### Connect with me

- GitHub: https://github.com/Manjeetsingh31
- LinkedIn: https://www.linkedin.com/in/manjeet-kumar-singh-a4b353296/
