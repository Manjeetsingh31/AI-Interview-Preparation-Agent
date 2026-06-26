import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class User(Base):
    """User model for authentication and profile management.

    Stores user credentials and personal information. Uses UUID primary keys for
    security — non-sequential IDs prevent user enumeration attacks. The
    is_active flag supports soft deactivation without data loss.

    Relationships:
        resume_analyses: Parsed resume records belonging to this user.
        interview_histories: Past interview Q&A sessions.
        feedbacks: Performance evaluations tied to the user.
        study_plans: Personalised day-by-day study tasks.
        progress: One-to-one aggregated progress snapshot.
    """
    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID v4 primary key — prevents sequential-ID guessing",
    )
    full_name = Column(
        String(255),
        nullable=True,
        comment="Optional display name for personalisation",
    )
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Used as the primary login identifier; must be unique",
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="SHA-256 (or bcrypt) hash; never stores plain text",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="Soft-delete flag — False means account is disabled",
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp of account creation",
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp of last profile update",
    )

    resume_analyses = relationship(
        "ResumeAnalysis",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_histories = relationship(
        "InterviewHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    study_plans = relationship(
        "StudyPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    progress = relationship(
        "Progress",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
