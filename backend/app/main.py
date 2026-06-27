import os
import hashlib
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

# Core imports
from backend.app.core.config import settings
from backend.app.core.db import engine, Base, get_db
from backend.app.models import models
from backend.app.schemas import schemas

# Service agents
from backend.app.services.agents.analyzer import ResumeAnalyzer
from backend.app.services.agents.orchestrator import InterviewOrchestrator

# ADK Resume Analysis router
from backend.app.api.resume_analysis import router as adk_resume_router

# ATS Scoring Engine router
from backend.app.api.ats import router as ats_router
from backend.app.core.database import init_db as init_refactored_db

# Initialize FastAPI App
app = FastAPI(title=settings.PROJECT_NAME)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database tables
Base.metadata.create_all(bind=engine)
init_refactored_db()

# Include routers
app.include_router(adk_resume_router)
app.include_router(ats_router)

# Helper functions for Auth (using Python standard hashlib to avoid external C dependencies)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user_id(token: str = "mock-token", db: Session = Depends(get_db)) -> str:
    # A simplified JWT/Session provider for capstone;
    # In production, decode JWT token to extract email/id.
    # If header doesn't exist, we fall back to a default mock user for local testing convenience.
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    user = db.query(models.User).filter(models.User.email == "candidate@example.com").first()
    if not user:
        # Create default mock user
        user = models.User(
            email="candidate@example.com",
            password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id

# --- AUTH ENDPOINTS ---

@app.post("/api/auth/register", response_model=schemas.UserOut)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or user.password_hash != hash_password(user_data.password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    return schemas.Token(
        access_token=f"Bearer-{user.id}",
        token_type="bearer",
        user_id=user.id
    )

# --- RESUME ENDPOINTS ---

@app.post("/api/resumes/upload", response_model=schemas.ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # Read the file content
    contents = await file.read()
    filename = file.filename
    
    # Try parsing text directly. If it is PDF, we can use Gemini native document reading.
    # Convert file bytes to text or directly use Gemini native capabilities
    from google.genai import types
    from google import genai
    
    # For now, let's pass the bytes to the Gemini client if it's a PDF
    try:
        analyzer = ResumeAnalyzer()
        
        # Decide content type
        mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "text/plain"
        
        if mime_type == "application/pdf":
            # Send file to Gemini directly for analysis
            prompt = "Please extract skills, summary, weaknesses, and focus areas from this resume."
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            from backend.app.services.agents.analyzer import ResumeAnalysisSchema
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=contents,
                        mime_type="application/pdf",
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction="You are a professional HR recruiter and resume parser. Output structured JSON matching the requested schema.",
                    response_mime_type="application/json",
                    response_schema=ResumeAnalysisSchema,
                    temperature=0.2,
                )
            )
            import json
            parsed_json = json.loads(response.text)
            parsed_data = ResumeAnalysisSchema(**parsed_json).model_dump()
        else:
            # Parse text files directly
            text_content = contents.decode("utf-8", errors="ignore")
            parsed_data = analyzer.analyze_resume(text_content).model_dump()
            
    except Exception as e:
        # Fallback empty structure
        parsed_data = {
            "skills": ["General ML", "Software Design", "Data Structures"],
            "experience_summary": "Parsed resume with default details.",
            "suggested_weaknesses": ["System architecture scale", "Behavioral examples"],
            "recommended_topics": ["ML Algorithms", "Python Programming"]
        }

    # Save to database
    resume = models.Resume(
        user_id=user_id,
        filename=filename,
        parsed_data=parsed_data
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume

# --- SESSION ENDPOINTS ---

@app.post("/api/sessions/create", response_model=schemas.SessionOut)
def create_session(
    session_data: schemas.SessionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    new_session = models.InterviewSession(
        user_id=user_id,
        resume_id=session_data.resume_id,
        role=session_data.role,
        company=session_data.company or "Standard",
        interview_type=session_data.interview_type,
        status="active"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    # Initialize the first question in the background using the Orchestrator
    orchestrator = InterviewOrchestrator()
    orchestrator.process_turn(db, new_session.id, candidate_message=None)
    
    return new_session

@app.get("/api/sessions/{session_id}", response_model=schemas.SessionDetailOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.post("/api/sessions/{session_id}/turn", response_model=schemas.ChatTurnResponse)
def submit_turn(
    session_id: str,
    turn_data: schemas.ChatTurnRequest,
    db: Session = Depends(get_db)
):
    orchestrator = InterviewOrchestrator()
    try:
        response = orchestrator.process_turn(db, session_id, candidate_message=turn_data.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ANALYTICS ENDPOINTS ---

@app.get("/api/analytics/progress")
def get_progress(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    sessions = (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.user_id == user_id, models.InterviewSession.status == "completed")
        .order_by(models.InterviewSession.created_at.asc())
        .all()
    )
    
    progress = []
    for s in sessions:
        if s.evaluation:
            progress.append({
                "session_id": s.id,
                "role": s.role,
                "company": s.company,
                "interview_type": s.interview_type,
                "overall_score": s.evaluation.overall_score,
                "criteria_scores": s.evaluation.criteria_scores,
                "date": s.completed_at.strftime("%Y-%m-%d")
            })
            
    return progress
