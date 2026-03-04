"""Health check API routes."""

import logging
from fastapi import APIRouter

from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health():
    """Return API health status.

    :return: Status payload indicating service health.
    """
    logger.info("Health check requested")
    return {"status": "ok"}