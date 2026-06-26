from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.app.core.config import settings

class InterviewerTurnSchema(BaseModel):
    evaluation_of_last_answer: str  # Analysis of the candidate's response
    next_action: str                 # 'probe' (ask follow-up), 'next_question' (new topic), or 'wrap_up'
    message: str                     # What the interviewer will say/ask next

class InterviewerAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def get_next_turn(
        self,
        role: str,
        company: str,
        interview_type: str,
        resume_data: Optional[Dict[str, Any]],
        transcript_history: List[Dict[str, str]]
    ) -> InterviewerTurnSchema:
        """
        Generates the next question or response based on role, company, type, resume, and history.
        """
        # Format candidate profile
        resume_context = ""
        if resume_data:
            skills = ", ".join(resume_data.get("skills", []))
            summary = resume_data.get("experience_summary", "")
            weaknesses = ", ".join(resume_data.get("suggested_weaknesses", []))
            resume_context = (
                f"Candidate Summary: {summary}\n"
                f"Candidate Skills: {skills}\n"
                f"Key Weaknesses to Probe: {weaknesses}\n"
            )
        else:
            resume_context = "No resume uploaded.\n"

        # Format conversation history
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
        
        Conversation History:
        {history_str if history_str else "No messages exchanged yet."}
        
        Your Task:
        1. If this is the start of the interview (no history), introduce yourself professionally as an interviewer from {company} and ask a suitable warm-up question.
        2. If the candidate just answered:
           - Analyze their response. If it lacks detail, doesn't match standard patterns (like STAR method for behavioral), or contains mistakes, choose 'probe' as next_action and ask them to expand or clarify.
           - If they answered satisfactorily, choose 'next_question' and ask a new question on a different topic aligned with the role.
           - If the interview has gone on for multiple rounds, and it's time to conclude, choose 'wrap_up' and say a professional goodbye.
        """

        system_instruction = (
            "You are a professional mock interviewer. You are strict but fair, trying to simulate a real, "
            "demanding job interview. You adjust your responses dynamically based on candidate performance. "
            "Output your decision and dialogue in the requested schema."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=InterviewerTurnSchema,
                    temperature=0.7,
                )
            )
            
            import json
            data = json.loads(response.text)
            return InterviewerTurnSchema(**data)
            
        except Exception as e:
            # Fallback
            return InterviewerTurnSchema(
                evaluation_of_last_answer="Error in generation.",
                next_action="next_question",
                message=f"Let's move on to the next question. Can you tell me about your experience with building scalable applications?"
            )
