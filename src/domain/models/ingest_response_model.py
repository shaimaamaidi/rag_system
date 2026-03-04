from pydantic import BaseModel


class IngestResponse(BaseModel):
    message: str
    filename: str
    status: str