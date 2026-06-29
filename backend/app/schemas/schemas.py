from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any

# Authentication Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Resume Schemas
class ResumeOut(BaseModel):
    id: str
    filename: str
    parsed_data: Optional[Dict[str, Any]] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Transcript Schemas
class TranscriptCreate(BaseModel):
    sender: str  # candidate, interviewer
    message: str

class TranscriptOut(BaseModel):
    id: str
    sender: str
    message: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# Evaluation Schemas
class EvaluationOut(BaseModel):
    id: str
    session_id: str
    overall_score: int
    feedback_summary: str
    criteria_scores: Dict[str, int]
    recommendations: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Session Schemas
class SessionCreate(BaseModel):
    resume_id: Optional[str] = None
    role: str
    company: Optional[str] = "Standard"
    interview_type: str  # behavioral, coding, system_design

class SessionOut(BaseModel):
    id: str
    role: str
    company: str
    interview_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SessionDetailOut(SessionOut):
    transcripts: List[TranscriptOut] = []
    evaluation: Optional[EvaluationOut] = None

# Chat Interactive Flow
class ChatTurnRequest(BaseModel):
    message: str

class ChatTurnResponse(BaseModel):
    status: str  # active, completed
    message: Optional[str] = None
    evaluation: Optional[EvaluationOut] = None
