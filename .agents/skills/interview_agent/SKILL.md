---
name: Interview Prep Agent Skill
description: Instructions for implementing, refining, or debugging the AI Interview Preparation Agent using Google Gen AI SDK, FastAPI, and Streamlit.
---

# Interview Prep Agent Skill Instructions

This skill helps orchestrate agent logic across FastAPI and Streamlit.

## Setup Requirements
- Check that the Gemini API is initialized using `google-genai`.
- Verify SQLite database connection using SQLAlchemy sessions.
- Maintain simple schemas using Pydantic.

## Design Patterns
1. **Dynamic Interview Turn**: The interviewer takes the target role, company context, candidate's resume keywords, and past dialogue transcript turns to formulate a structured next action (`probe` or `next_question`).
2. **Session Memory**: Compile existing conversation logs from the SQLite database and pass them as `types.Content` inputs to the API.
3. **Actionable Assessment**: Compile full transcripts at the session end and request `gemini-2.5-pro` to output a structured JSON scoring rubric and concrete recommendations.
