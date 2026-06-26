"""pytest configuration for the backend test suite.

Ensures the project root is on ``sys.path`` so that absolute imports
like ``from backend.app...`` work regardless of where pytest is invoked.
"""

import sys
from pathlib import Path

# Add the project root (parent of backend/) to sys.path
project_root = Path(__file__).resolve().parents[3]  # conftest → tests/ → app/ → backend/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
