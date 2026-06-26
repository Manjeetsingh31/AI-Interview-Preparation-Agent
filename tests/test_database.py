"""Comprehensive test script for the database layer.

Validates all models, CRUD operations, and edge cases.
Run from the project root with:

    python -m tests.test_database

or:

    python tests/test_database.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///./test_interview_agent.db"

from backend.app.core.database import Base, engine, SessionLocal, init_db
from backend.app.core.config import settings

from backend.app.models.user import User
from backend.app.models.resume_analysis import ResumeAnalysis
from backend.app.models.interview_history import InterviewHistory
from backend.app.models.question import Question
from backend.app.models.feedback import Feedback
from backend.app.models.study_plan import StudyPlan
from backend.app.models.progress import Progress

from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.schemas.resume_analysis import ResumeAnalysisCreate, ResumeAnalysisUpdate
from backend.app.schemas.interview_history import InterviewHistoryCreate, InterviewHistoryUpdate
from backend.app.schemas.question import QuestionCreate, QuestionUpdate
from backend.app.schemas.feedback import FeedbackCreate, FeedbackUpdate
from backend.app.schemas.study_plan import StudyPlanCreate, StudyPlanUpdate
from backend.app.schemas.progress import ProgressCreate, ProgressUpdate

from backend.app.crud.crud_user import user as crud_user
from backend.app.crud.crud_resume import resume_analysis as crud_resume
from backend.app.crud.crud_interview import interview_history as crud_interview
from backend.app.crud.crud_question import question as crud_question
from backend.app.crud.crud_feedback import feedback as crud_feedback
from backend.app.crud.crud_progress import progress as crud_progress
from backend.app.crud.crud_study_plan import study_plan as crud_study_plan

db: SessionLocal = None


def setup_module():
    global db
    print("\n" + "=" * 60)
    print("DATABASE LAYER — TEST SUITE")
    print("=" * 60)

    init_db()
    db = SessionLocal()
    print(f"[SETUP] Database URL: {settings.DATABASE_URL}")
    print(f"[SETUP] Tables created.")
    print()


def teardown_module():
    db.close()
    engine.dispose()
    
    db_path = os.path.join(os.path.dirname(__file__), "..", "test_interview_agent.db")
    if os.path.exists(db_path):
        retries = 3
        while retries > 0:
            try:
                os.remove(db_path)
                print(f"[TEARDOWN] Test database '{db_path}' removed.")
                break
            except PermissionError:
                retries -= 1
                import time
                time.sleep(0.5)
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


def print_separator(title: str):
    print(f"\n--- {title} ---")


def test_create_user():
    print_separator("CREATE USER")
    
    user_in = UserCreate(
        full_name="Alice Johnson",
        email="alice@example.com",
        password="securepass123",
    )
    user = crud_user.create_with_hash(
        db, obj_in=user_in, password_hash="hashed_" + user_in.password
    )
    
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Johnson"
    assert user.is_active is True
    assert user.created_at is not None
    print(f"  Created: id={user.id}, email={user.email}, name={user.full_name}")
    print(f"  Created at: {user.created_at}")
    return user


def test_create_duplicate_email(user: User):
    print_separator("DUPLICATE EMAIL CHECK")
    
    is_taken = crud_user.is_email_taken(db, email=user.email)
    print(f"  Is 'alice@example.com' taken? {is_taken}")
    assert is_taken is True
    
    is_taken = crud_user.is_email_taken(db, email="nonexistent@example.com")
    print(f"  Is 'nonexistent@example.com' taken? {is_taken}")
    assert is_taken is False


def test_get_user_by_email(user: User):
    print_separator("GET USER BY EMAIL")
    
    found = crud_user.get_by_email(db, email=user.email)
    assert found is not None
    assert found.id == user.id
    print(f"  Found: id={found.id}, email={found.email}")
    
    not_found = crud_user.get_by_email(db, email="ghost@example.com")
    assert not_found is None
    print(f"  Non-existent email returns: {not_found}")


def test_update_user(user: User):
    print_separator("UPDATE USER")
    
    update_data = UserUpdate(full_name="Alice J. Johnson")
    updated = crud_user.update(db, db_obj=user, obj_in=update_data)
    
    assert updated.full_name == "Alice J. Johnson"
    print(f"  Updated name: '{updated.full_name}'")
    
    update_data = UserUpdate(is_active=False)
    updated = crud_user.update(db, db_obj=user, obj_in=update_data)
    assert updated.is_active is False
    print(f"  Updated is_active: {updated.is_active}")
    
    update_data = UserUpdate(is_active=True)
    updated = crud_user.update(db, db_obj=user, obj_in=update_data)


def test_get_user_by_id(user: User):
    print_separator("GET USER BY ID")
    
    found = crud_user.get(db, id=user.id)
    assert found is not None
    assert found.id == user.id
    print(f"  Found user by id: {found.id}")
    
    not_found = crud_user.get(db, id=str(uuid.uuid4()))
    assert not_found is None
    print(f"  Non-existent id returns: {not_found}")


def test_list_users(user: User):
    print_separator("LIST USERS (PAGINATION)")
    
    users = crud_user.get_multi(db, skip=0, limit=10)
    assert len(users) >= 1
    print(f"  Total users: {len(users)}")
    for u in users:
        print(f"    - {u.id}: {u.email}")


def test_count_users(user: User):
    print_separator("COUNT USERS")
    
    count = crud_user.count(db)
    print(f"  Total user count: {count}")
    assert count >= 1


def test_create_resume_analysis(user: User):
    print_separator("CREATE RESUME ANALYSIS")
    
    resume_in = ResumeAnalysisCreate(
        user_id=user.id,
        resume_filename="alice_resume.pdf",
        ats_score=85,
        skills=["Python", "FastAPI", "SQLAlchemy"],
        missing_skills=["Kubernetes", "Docker"],
        strengths=["Strong backend architecture skills"],
        weaknesses=["Limited DevOps experience"],
        recommendations=["Learn Docker and Kubernetes basics"],
    )
    analysis = crud_resume.create(db, obj_in=resume_in)
    
    assert analysis.id is not None
    assert analysis.user_id == user.id
    assert analysis.ats_score == 85
    print(f"  Created resume analysis: id={analysis.id}, ATS score={analysis.ats_score}")
    return analysis


def test_get_resume_by_user(user: User, analysis):
    print_separator("GET RESUME BY USER")
    
    analyses = crud_resume.get_by_user(db, user_id=user.id)
    assert len(analyses) >= 1
    print(f"  Found {len(analyses)} resume(s) for user")
    
    latest = crud_resume.get_latest_by_user(db, user_id=user.id)
    assert latest is not None
    assert latest.id == analysis.id
    print(f"  Latest resume: {latest.resume_filename}")


def test_update_resume_analysis(analysis):
    print_separator("UPDATE RESUME ANALYSIS")
    
    update_data = ResumeAnalysisUpdate(ats_score=90)
    updated = crud_resume.update(db, db_obj=analysis, obj_in=update_data)
    assert updated.ats_score == 90
    print(f"  Updated ATS score: {updated.ats_score}")


def test_create_interview_history(user: User):
    print_separator("CREATE INTERVIEW HISTORY")
    
    interview_in = InterviewHistoryCreate(
        user_id=user.id,
        interview_type="behavioral",
        question="Tell me about a time you led a team.",
        answer="I led a team of 5 engineers...",
        score=88,
        feedback="Good structure, could add more metrics.",
    )
    history = crud_interview.create(db, obj_in=interview_in)
    
    assert history.id is not None
    assert history.interview_type == "behavioral"
    assert history.score == 88
    print(f"  Created interview turn: id={history.id}, type={history.interview_type}")
    return history


def test_get_interview_by_user(user: User):
    print_separator("GET INTERVIEW HISTORY BY USER")
    
    records = crud_interview.get_by_user(db, user_id=user.id)
    print(f"  Found {len(records)} interview record(s)")
    for r in records:
        print(f"    - {r.id}: [{r.interview_type}] {r.question[:50]}...")


def test_get_interview_by_type(user: User):
    print_separator("FILTER INTERVIEW BY TYPE")
    
    behavioral = crud_interview.get_by_type(db, user_id=user.id, interview_type="behavioral")
    print(f"  Behavioral: {len(behavioral)} record(s)")
    
    coding = crud_interview.get_by_type(db, user_id=user.id, interview_type="coding")
    print(f"  Coding: {len(coding)} record(s)")


def test_create_question():
    print_separator("CREATE QUESTION")
    
    q_in = QuestionCreate(
        category="python",
        difficulty="medium",
        question="Explain Python decorators with an example.",
        expected_answer="A decorator is a function that wraps another function...",
        tags=["python", "decorators", "functions"],
    )
    question = crud_question.create(db, obj_in=q_in)
    
    assert question.id is not None
    assert question.category == "python"
    assert question.difficulty == "medium"
    print(f"  Created question: id={question.id}, category={question.category}")
    return question


def test_get_question_by_category():
    print_separator("GET QUESTION BY CATEGORY")
    
    questions = crud_question.get_by_category(db, category="python")
    print(f"  Python questions: {len(questions)}")
    
    questions = crud_question.get_by_category(db, category="system_design")
    print(f"  System Design questions: {len(questions)}")


def test_get_random_question():
    print_separator("GET RANDOM QUESTION")
    
    random_q = crud_question.get_random(db, limit=1)
    print(f"  Random question: {random_q[0].question[:60]}...")
    assert len(random_q) == 1


def test_create_feedback(user: User):
    print_separator("CREATE FEEDBACK")
    
    fb_in = FeedbackCreate(
        user_id=user.id,
        communication_score=85,
        technical_score=78,
        confidence_score=90,
        overall_score=84,
        strengths=["Clear communication", "Good technical depth"],
        weaknesses=["Could use more examples", "Rushed some answers"],
        suggestions=["Practice STAR method", "Slow down when explaining"],
    )
    feedback = crud_feedback.create(db, obj_in=fb_in)
    
    assert feedback.id is not None
    assert feedback.overall_score == 84
    print(f"  Created feedback: id={feedback.id}, overall={feedback.overall_score}")
    return feedback


def test_get_feedback_average(user: User):
    print_separator("FEEDBACK AVERAGE")
    
    avg = crud_feedback.get_average_overall(db, user_id=user.id)
    print(f"  Average overall score: {avg}")
    assert avg is not None


def test_create_study_plan(user: User):
    print_separator("CREATE STUDY PLAN")
    
    plan_in = StudyPlanCreate(
        user_id=user.id,
        day=1,
        topic="Python Fundamentals",
        task="Review decorators, generators, and context managers",
        status="pending",
    )
    plan = crud_study_plan.create(db, obj_in=plan_in)
    
    assert plan.id is not None
    assert plan.day == 1
    print(f"  Created study plan: id={plan.id}, day={plan.day}, topic={plan.topic}")
    return plan


def test_mark_study_completed(plan):
    print_separator("MARK STUDY PLAN COMPLETED")
    
    completed = crud_study_plan.mark_completed(db, id=plan.id)
    assert completed is not None
    assert completed.status == "completed"
    print(f"  Marked plan '{plan.topic}' as '{completed.status}'")


def test_study_completion_rate(user: User):
    print_separator("STUDY COMPLETION RATE")
    
    rate = crud_study_plan.get_completion_rate(db, user_id=user.id)
    print(f"  Completion rate: {rate}%")


def test_create_progress(user: User):
    print_separator("CREATE PROGRESS")
    
    prog_in = ProgressCreate(
        user_id=user.id,
        completed_interviews=3,
        average_score=82,
        current_level="intermediate",
        weak_topics=["System Design", "Algorithms"],
        strong_topics=["Python", "Behavioral"],
    )
    progress = crud_progress.create(db, obj_in=prog_in)
    
    assert progress.id is not None
    assert progress.average_score == 82
    print(f"  Created progress: id={progress.id}, level={progress.current_level}")
    return progress


def test_upsert_progress(user: User):
    print_separator("PROGRESS UPSERT")
    
    update_data = ProgressUpdate(completed_interviews=4, average_score=83)
    upserted = crud_progress.upsert(db, user_id=user.id, obj_in=update_data)
    
    assert upserted.completed_interviews == 4
    assert upserted.average_score == 83
    print(f"  Upserted progress: interviews={upserted.completed_interviews}, avg={upserted.average_score}")
    
    new_user_in = UserCreate(
        full_name="Bob Smith",
        email="bob@example.com",
        password="bobpass123",
    )
    new_user = crud_user.create_with_hash(db, obj_in=new_user_in, password_hash="hashed_bobpass")
    
    new_update = ProgressUpdate(completed_interviews=1, average_score=75)
    new_progress = crud_progress.upsert(db, user_id=new_user.id, obj_in=new_update)
    assert new_progress.completed_interviews == 1
    print(f"  Created new progress for Bob: interviews={new_progress.completed_interviews}")


def test_delete_resume_analysis(analysis):
    print_separator("DELETE RESUME ANALYSIS")
    
    deleted = crud_resume.remove(db, id=analysis.id)
    assert deleted is not None
    assert deleted.id == analysis.id
    print(f"  Deleted resume analysis: id={deleted.id}")
    
    check = crud_resume.get(db, id=analysis.id)
    assert check is None
    print(f"  Verified deletion: get() returns {check}")


def test_cascade_delete_user(user: User):
    print_separator("CASCADE DELETE USER")
    
    user_id = user.id
    crud_user.remove(db, id=user_id)
    
    remaining_resumes = crud_resume.get_by_user(db, user_id=user_id)
    print(f"  Remaining resumes after user delete: {len(remaining_resumes)}")
    assert len(remaining_resumes) == 0
    
    remaining_interviews = crud_interview.get_by_user(db, user_id=user_id)
    print(f"  Remaining interviews after user delete: {len(remaining_interviews)}")
    assert len(remaining_interviews) == 0
    
    remaining_feedback = crud_feedback.get_by_user(db, user_id=user_id)
    print(f"  Remaining feedbacks after user delete: {len(remaining_feedback)}")
    assert len(remaining_feedback) == 0
    
    remaining_plans = crud_study_plan.get_by_user(db, user_id=user_id)
    print(f"  Remaining study plans after user delete: {len(remaining_plans)}")
    assert len(remaining_plans) == 0
    
    deleted_progress = crud_progress.get_by_user(db, user_id=user_id)
    print(f"  Remaining progress after user delete: {deleted_progress}")
    assert deleted_progress is None


def test_invalid_id_handling():
    print_separator("INVALID ID HANDLING")
    
    fake_id = str(uuid.uuid4())
    
    result = crud_user.get(db, id=fake_id)
    assert result is None
    print(f"  get(non-existent) returns: {result}")
    
    result = crud_user.remove(db, id=fake_id)
    assert result is None
    print(f"  remove(non-existent) returns: {result}")


def test_search_by_field(user):
    print_separator("SEARCH BY FIELD")
    
    users = crud_user.get_by_field(db, field="email", value="bob@example.com")
    print(f"  search(email='bob@example.com') found: {len(users)} user(s)")


def run_all():
    setup_module()
    
    try:
        user = test_create_user()
        test_create_duplicate_email(user)
        test_get_user_by_email(user)
        test_update_user(user)
        test_get_user_by_id(user)
        test_list_users(user)
        test_count_users(user)
        
        analysis = test_create_resume_analysis(user)
        test_get_resume_by_user(user, analysis)
        test_update_resume_analysis(analysis)
        
        test_create_interview_history(user)
        test_get_interview_by_user(user)
        test_get_interview_by_type(user)
        
        test_create_question()
        test_get_question_by_category()
        test_get_random_question()
        
        test_create_feedback(user)
        test_get_feedback_average(user)
        
        plan = test_create_study_plan(user)
        test_mark_study_completed(plan)
        test_study_completion_rate(user)
        
        test_create_progress(user)
        test_upsert_progress(user)
        
        test_delete_resume_analysis(analysis)
        
        test_search_by_field(user)
        
        test_invalid_id_handling()
        
        test_cascade_delete_user(user)
        
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        teardown_module()


if __name__ == "__main__":
    run_all()
