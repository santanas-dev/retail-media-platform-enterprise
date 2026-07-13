"""
Identity API routes — decomposed by bounded context.

Each sub-module contains a FastAPI APIRouter without prefix.
The parent identity.py aggregates them into a single router
with prefix="/api/v1/identity".
"""
