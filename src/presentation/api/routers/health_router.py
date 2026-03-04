import logging
from fastapi import APIRouter

from src.infrastructure.adapters.config.logger import setup_logger

# ── Logger ─────────────────────────
setup_logger()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health():
    logger.info("Health check requested")
    return {"status": "ok"}