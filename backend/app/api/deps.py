"""Define reusable dependencies for API routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_session, get_session_manual

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionManualDep = Annotated[AsyncSession, Depends(get_session_manual)]


def get_user_repository():
    """Provide the user repository used by authentication routes.

    Concrete implementations can replace this dependency at application setup
    or in tests.
    """
    return NotImplementedError
