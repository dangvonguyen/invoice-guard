"""Define reusable dependencies for API routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_session, get_session_manual

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionManualDep = Annotated[AsyncSession, Depends(get_session_manual)]
