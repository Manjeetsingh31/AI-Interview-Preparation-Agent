import json
import time
import streamlit as st
import requests
from utils.constants import API_BASE_URL


class APIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.timeout = 60

    @property
    def _headers(self):
        headers = {"Content-Type": "application/json"}
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        try:
            if "headers" not in kwargs:
                kwargs["headers"] = self._headers
            if method == "get":
                r = requests.get(url, **kwargs)
            elif method == "post":
                r = requests.post(url, **kwargs)
            elif method == "put":
                r = requests.put(url, **kwargs)
            elif method == "delete":
                r = requests.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            r.raise_for_status()
            if r.status_code == 204:
                return None
            return r.json()
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot connect to {self.base_url}. Is the backend running?")
            return None
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except (json.JSONDecodeError, AttributeError):
                detail = str(e)
            st.error(detail)
            return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None

    # --- Auth ---
    def login(self, email, password):
        return self._request("post", "/api/auth/login", json={"email": email, "password": password})

    def register(self, email, password):
        return self._request("post", "/api/auth/register", json={"email": email, "password": password})

    # --- Resume ---
    def analyze_resume(self, file_bytes, filename):
        url = f"{self.base_url}/api/resumes/analyze"
        headers = {}
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with st.spinner("Analyzing resume..."):
                r = requests.post(
                    url,
                    files={"file": (filename, file_bytes, "application/pdf" if filename.lower().endswith(".pdf") else "text/plain")},
                    headers=headers,
                    timeout=120,
                )
                r.raise_for_status()
                return r.json()
        except requests.exceptions.Timeout:
            st.error("Resume analysis timed out. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")
            return None
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except (json.JSONDecodeError, AttributeError):
                detail = str(e)
            st.error(detail)
            return None
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return None

    def upload_resume(self, file_bytes, filename):
        url = f"{self.base_url}/api/resumes/upload"
        headers = {}
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = requests.post(
                url,
                files={"file": (filename, file_bytes, "application/pdf")},
                headers=headers,
                timeout=120,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return None

    # --- ATS ---
    def analyze_ats(self, resume_analysis_adk_id):
        return self._request("post", "/api/ats/analyze", json={"resume_analysis_adk_id": resume_analysis_adk_id})

    def get_ats_history(self):
        return self._request("get", "/api/ats/history")
    
    def get_interview_sessions(self):
        return self._request("get", "/api/interview/sessions")

    def get_ats_score(self, ats_id):
        return self._request("get", f"/api/ats/{ats_id}")

    # --- Interview Questions ---
    def generate_questions(self, resume_analysis_id, company, role, interview_type, difficulty, number_of_questions=10):
        return self._request("post", "/api/interview/questions/generate", json={
            "resume_analysis_id": resume_analysis_id,
            "company": company,
            "role": role,
            "interview_type": interview_type,
            "difficulty": difficulty,
            "number_of_questions": number_of_questions,
        })

    def get_question_history(self):
        return self._request("get", "/api/interview/questions/history")

    def get_questions_by_analysis(self, resume_analysis_id):
        return self._request("get", f"/api/interview/questions/by-analysis/{resume_analysis_id}")

    # --- Mock Interview ---
    def start_interview(self, resume_analysis_id, company, role, interview_type, difficulty, number_of_questions=10):
        return self._request("post", "/api/interview/start", json={
            "resume_analysis_id": resume_analysis_id,
            "company": company,
            "role": role,
            "interview_type": interview_type,
            "difficulty": difficulty,
            "number_of_questions": number_of_questions,
        })

    def submit_answer(self, session_id, answer, response_time=None, total_questions=None):
        return self._request("post", "/api/interview/answer", json={
            "session_id": session_id,
            "answer": answer,
            "response_time": response_time,
            "total_questions": total_questions,
        })

    def end_interview(self, session_id):
        return self._request("post", "/api/interview/end", json={"session_id": session_id})

    def get_session_turns(self, session_id):
        return self._request("get", f"/api/interview/{session_id}")

    def get_interview_history(self):
        return self._request("get", "/api/interview/history")

    def get_transcript(self, session_id):
        return self._request("get", f"/api/interview/transcript/{session_id}")

    # --- Evaluation ---
    def generate_evaluation(self, session_id):
        return self._request("post", "/api/evaluate", json={"session_id": session_id})

    def get_evaluation_by_session(self, session_id):
        return self._request("get", f"/api/evaluations/session/{session_id}")

    def get_evaluations(self):
        return self._request("get", "/api/evaluations")

    def get_evaluation_statistics(self):
        return self._request("get", "/api/evaluations/statistics")

    def get_evaluation_dashboard(self):
        return self._request("get", "/api/evaluations/dashboard")

    def search_evaluations(self, query):
        return self._request("get", "/api/evaluations/search", params={"q": query})

    # --- Study Plan ---
    def generate_study_plan(self, evaluation_id, target_role, target_company, study_duration):
        return self._request("post", "/api/study-plan/generate", json={
            "evaluation_id": evaluation_id,
            "target_role": target_role,
            "target_company": target_company,
            "study_duration": study_duration,
        })

    def get_study_plan(self, plan_id):
        return self._request("get", f"/api/study-plan/{plan_id}")

    def get_study_plan_history(self):
        return self._request("get", "/api/study-plan/history/all")

    def get_study_plan_progress(self, plan_id):
        return self._request("get", f"/api/study-plan/progress/{plan_id}")

    def get_study_plan_dashboard(self):
        return self._request("get", "/api/study-plan/dashboard/data")

    def update_study_plan(self, plan_id, data):
        return self._request("put", f"/api/study-plan/update/{plan_id}", json=data)

    def update_study_plan_progress(self, plan_id, completion_percentage, status=None):
        body = {"completion_percentage": completion_percentage}
        if status:
            body["status"] = status
        return self._request("put", f"/api/study-plan/progress/{plan_id}", json=body)

    def delete_study_plan(self, plan_id):
        return self._request("delete", f"/api/study-plan/{plan_id}")

    # --- Dashboard / Analytics ---
    def get_dashboard(self):
        return self._request("get", "/api/dashboard")

    def get_dashboard_summary(self):
        return self._request("get", "/api/dashboard/summary")

    def get_dashboard_statistics(self):
        return self._request("get", "/api/dashboard/statistics")

    def get_interview_analytics(self):
        return self._request("get", "/api/dashboard/interview")

    def get_ats_analytics(self):
        return self._request("get", "/api/dashboard/ats")

    def get_study_analytics(self):
        return self._request("get", "/api/dashboard/study")

    def get_skill_analytics(self):
        return self._request("get", "/api/dashboard/skills")

    def get_timeline(self, period=None):
        params = {}
        if period:
            params["period"] = period
        return self._request("get", "/api/dashboard/timeline", params=params)

    def get_readiness(self):
        return self._request("get", "/api/dashboard/readiness")

    # --- Sessions (from main.py) ---
    def create_session(self, resume_id, role, company, interview_type):
        return self._request("post", "/api/sessions/create", json={
            "resume_id": resume_id,
            "role": role,
            "company": company,
            "interview_type": interview_type,
        })

    def get_session(self, session_id):
        return self._request("get", f"/api/sessions/{session_id}")

    def submit_turn(self, session_id, message):
        return self._request("post", f"/api/sessions/{session_id}/turn", json={"message": message})

    def get_progress(self):
        return self._request("get", "/api/analytics/progress")


api = APIClient()
