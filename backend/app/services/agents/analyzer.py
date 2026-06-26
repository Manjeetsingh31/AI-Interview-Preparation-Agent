from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List
from backend.app.core.config import settings

# Define the structure we want returned by Gemini for resume analysis
class ResumeAnalysisSchema(BaseModel):
    skills: List[str]
    experience_summary: str
    suggested_weaknesses: List[str]  # Potential focus areas or skill gaps to probe
    recommended_topics: List[str]   # Topics/projects relevant to their resume

class ResumeAnalyzer:
    def __init__(self):
        # Initialize client using setting API key
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def analyze_resume(self, resume_text: str) -> ResumeAnalysisSchema:
        """
        Parses resume text using Gemini and returns structured metadata.
        """
        prompt = f"""
        Analyze the following resume text. Extract a list of skills, a brief 1-2 sentence experience summary,
        potential areas of weakness or skill gaps that an interviewer should explore, and relevant topics to focus on.
        
        Resume text:
        \"\"\"{resume_text}\"\"\"
        """
        
        system_instruction = (
            "You are a professional HR recruiter and technical parser. Your task is to analyze candidate resume text "
            "and output a structured evaluation matching the requested schema."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ResumeAnalysisSchema,
                    temperature=0.2,
                )
            )
            
            # The SDK will automatically parse the output if response_schema is defined, 
            # or it returns a JSON string in response.text
            import json
            data = json.loads(response.text)
            return ResumeAnalysisSchema(**data)
            
        except Exception as e:
            # Fallback in case of error
            return ResumeAnalysisSchema(
                skills=[],
                experience_summary="Failed to parse resume.",
                suggested_weaknesses=["Technical proficiency", "Behavioral depth"],
                recommended_topics=["General engineering questions"]
            )
