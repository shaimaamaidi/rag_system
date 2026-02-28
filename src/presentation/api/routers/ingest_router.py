from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi import Request

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


def get_ingest_use_case(request: Request):
    return request.app.state.container.ingest_use_case


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Ingest a PDF document",
    description="Upload a PDF file to be processed through the full RAG ingestion pipeline: "
                "load → classify → chunk → embed → index.",
)
async def ingest_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
    use_case=Depends(get_ingest_use_case),
) -> str:
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Only PDF files are accepted, got: {file.filename}",
        )

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    try:
        use_case.execute(file_bytes=file_bytes, filename=file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline failed: {str(e)}",
        )

    return "Document ingested successfully"