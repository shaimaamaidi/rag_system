"""Question answering API routes."""

import logging
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from src.domain.exceptions.azure_agent_run_exception import AzureAgentRunException
from src.domain.exceptions.question_empty_exception import QuestionEmptyException
from src.domain.models.ask_request_model import AskRequest
from src.infrastructure.logging.logger import setup_logger

router = APIRouter(prefix="/ask", tags=["Question Answering"])

setup_logger()
logger = logging.getLogger(__name__)

def get_agent(request: Request):
    """Resolve the agent adapter from application state.

    :param request: Incoming FastAPI request.
    :return: Agent adapter instance.
    """
    return request.app.state.container.agent_adapter

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
    """Stream answers for a user question.

    :param body: Request payload containing the question.
    :param agent: Injected agent adapter.
    :return: Streaming response for the agent output.
    """

    question_text = body.question.strip()
    if not question_text:
        logger.warning("Received empty question")
        raise QuestionEmptyException(
            message="Question cannot be empty or whitespace"
        )

    logger.info("Received question: %s", question_text)

    def stream_generator():
        """Yield streaming chunks from the agent.

        :return: Generator of streaming response chunks.
        """
        try:
            for chunk in agent.ask_question_stream(question=question_text):
                yield chunk
        except Exception as e:
            logger.error("Agent streaming failed: %s", str(e))
            raise AzureAgentRunException(
                message=f"Agent streaming failed: {str(e)}"
            ) from e

    logger.info("Starting streaming response for question")
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )