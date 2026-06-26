from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

class EvaluationSchema(BaseModel):
    overall_score: int                   # 0 to 100
    feedback_summary: str                # High-level critique of the candidate's performance
    criteria_scores: Dict[str, int]      # Category-level scores (e.g., "communication": 80, "technical": 70)
    recommendations: List[str]           # Detailed, actionable improvement tips

class EvaluationAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-pro"  # Use the heavier, reasoning-focused model for evaluation

    def evaluate_session(
        self,
        role: str,
        company: str,
        interview_type: str,
        resume_data: Optional[Dict[str, Any]],
        transcript_history: List[Dict[str, str]]
    ) -> EvaluationSchema:
        """
        Runs a comprehensive assessment of the interview transcript.
        """
        # Format resume
        resume_context = ""
        if resume_data:
            resume_context = (
                f"Candidate Summary: {resume_data.get('experience_summary', '')}\n"
                f"Candidate Skills: {', '.join(resume_data.get('skills', []))}\n"
            )
        else:
            resume_context = "No resume uploaded.\n"

        # Format transcript
        history_str = ""
        for turn in transcript_history:
            sender = "Candidate" if turn["sender"] == "candidate" else "Interviewer"
            history_str += f"{sender}: {turn['message']}\n"

        prompt = f"""
        Role Profile:
        - Target Role: {role}
        - Target Company: {company}
        - Interview Type: {interview_type} (coding/behavioral/system_design)
        
        {resume_context}
        
        Interview Transcript:
        {history_str}
        
        Your Task:
        As an expert interviewer, evaluate the candidate's response in this interview.
        Assess:
        1. Technical/Behavioral competence matching the target role and company standard.
        2. Clarity, structure (e.g. STAR method for behavioral), and tone.
        3. Response correctness and speed of grasping feedback.
        
        Output:
        - An overall percentage score (0-100).
        - A constructive overview summary.
        - Granular category ratings out of 100 for (at least) communication, problem_solving, technical_depth, and role_fit.
        - A set of 3-5 specific, action-oriented recommendations explaining how the candidate could improve their answers.
        """

        system_instruction = (
            "You are an elite talent assessor. You evaluate job interview transcripts with extreme detail, "
            "providing constructive but strict grades and specific, actionable rewrite tips for candidates."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=EvaluationSchema,
                    temperature=0.3,
                )
            )
            
            import json
            data = json.loads(response.text)
            return EvaluationSchema(**data)
            
        except Exception as e:
            # Fallback
            return EvaluationSchema(
                overall_score=50,
                feedback_summary=f"Evaluation failed due to system exception: {str(e)}",
                criteria_scores={"communication": 50, "problem_solving": 50, "technical_depth": 50, "role_fit": 50},
                recommendations=["Please try completing another interview session."]
            )
