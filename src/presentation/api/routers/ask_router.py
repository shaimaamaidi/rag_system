from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ask", tags=["Question Answering"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to answer",
    )


class AskResponse(BaseModel):
    answer: str


# ── Dependency ────────────────────────────────────────────────────────────────

def get_ask_use_case(request: Request):
    return request.app.state.container.ask_use_case


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question",
    description="Submit a question to the RAG pipeline.",
)
async def ask_question(
    body: AskRequest,
    use_case=Depends(get_ask_use_case),
) -> AskResponse:
    if not body.question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty or whitespace.",
        )

    try:
        answer = use_case.execute(question=body.question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline failed: {str(e)}",
        )

    return AskResponse(answer=answer)