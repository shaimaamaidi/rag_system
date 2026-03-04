import logging
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Request
from src.domain.models.ingest_response_model import IngestResponse
from src.infrastructure.logging.logger import setup_logger

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

setup_logger()
logger = logging.getLogger(__name__)

def get_ingest_use_case(request: Request):
    return request.app.state.container.ingest_use_case

@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=IngestResponse,
    summary="Ingest a PDF document",
    description=(
        "Upload a PDF file to be processed through the full RAG ingestion pipeline: "
        "load → classify → chunk → embed → index."
    ),
)
async def ingest_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
    use_case=Depends(get_ingest_use_case),
) -> IngestResponse:

    logger.info("Received file upload: %s", file.filename)

    if not file.filename.endswith(".pdf"):
        logger.warning("Unsupported file type: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Only PDF files are accepted, got: {file.filename}",
        )

    try:
        file_bytes = await file.read()
        logger.info("Successfully read uploaded file: %s (%d bytes)", file.filename, len(file_bytes))
    except Exception as e:
        logger.error("Failed to read uploaded file: %s | Error: %s", file.filename, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    try:
        await use_case.ingest(file_bytes=file_bytes, filename=file.filename)
        logger.info("File ingested successfully: %s", file.filename)
    except Exception as e:
        logger.error("Ingestion pipeline failed for %s | Error: %s", file.filename, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline failed: {str(e)}",
        )

    return IngestResponse(
        message="Document ingested successfully",
        filename=file.filename,
        status="success"
    )