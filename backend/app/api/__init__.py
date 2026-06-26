"""API route packages.

Each submodule exposes a ``router`` (``APIRouter`` instance) that can be
included in the main FastAPI application with::

    from backend.app.api.resume import router as resume_router
    app.include_router(resume_router)
"""
