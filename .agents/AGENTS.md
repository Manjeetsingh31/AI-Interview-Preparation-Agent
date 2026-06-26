# Workspace Agent Rules

- **Code Quality**: Ensure all code maintains strict separation of concerns between backend (FastAPI) and frontend (Streamlit).
- **Type Safety**: Always leverage Pydantic v2 schemas for all API payloads and Gemini structured output parameters.
- **SQLite Engine**: Manage database sessions utilizing SQLAlchemy context managers to guarantee connections are closed cleanly.
- **Gemini SDK Pattern**: Always instantiate the `google-genai` client using `genai.Client(api_key=settings.GEMINI_API_KEY)` and select appropriate model configurations.
