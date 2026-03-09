"""Response model for document ingestion."""

from pydantic import BaseModel


class IngestResponse(BaseModel):
    """Payload returned after an ingestion request.

    :ivar message: Human-readable status message.
    :ivar filename: Name of the ingested file.
    :ivar status: Status string, e.g. "success".
    """
    message: str
    filename: str
    status: str