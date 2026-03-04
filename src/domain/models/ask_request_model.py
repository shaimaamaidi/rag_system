"""Request model for the ask-question endpoint."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Payload for a question request.

    :ivar question: Question text submitted by the user.
    """
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to answer",
    )