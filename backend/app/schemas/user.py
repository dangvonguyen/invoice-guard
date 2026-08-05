from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    """Response for users getting their own user data."""

    id: str
    email: str
