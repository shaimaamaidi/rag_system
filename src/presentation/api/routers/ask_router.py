from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.domain.exceptions.azure_agent_run_exception import AzureAgentRunException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException

router = APIRouter(prefix="/ask", tags=["Question Answering"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to answer",
    )


# ── Dependency ────────────────────────────────────────────────────────────────

def get_agent(request: Request):
    return request.app.state.container.agent_adapter


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Ask a question",
    description="Submit a question to the Azure AI Agent. Returns a streaming response (SSE).",
)
async def ask_question(
    body: AskRequest,
    agent=Depends(get_agent),
) -> StreamingResponse:

    if not body.question.strip():
        raise QuestionEmptyException(
            message="Question cannot be empty or whitespace"
        )

    def stream_generator():
        try:
            for chunk in agent.ask_question_stream(question=body.question):
                yield chunk
        except Exception as e:
            raise AzureAgentRunException(
                message=f"Agent streaming failed: {str(e)}"
            ) from e

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )