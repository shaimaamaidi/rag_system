"""Adapter that orchestrates OCR processing with Llama Cloud."""

import logging

from src.domain.models.ocr_result_model import OcrResult
from src.domain.ports.output.LlamaOcrPort import LlamaOcrPort
from .llama_api_client import LlamaApiClient
from .llama_parser import LlamaOcrParser
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class LlamaOcrAdapter(LlamaOcrPort):
    """Orchestrate OCR upload, polling, and parsing."""

    def __init__(self):
        """Initialize the adapter with API client and parser."""
        self.client = LlamaApiClient()
        self.parser = LlamaOcrParser()
        logger.info("LlamaOcrAdapter initialized")

    async def process(self, image_path: str) -> OcrResult:
        """Process an image through Llama OCR.

        :param image_path: Path to the image file.
        :return: Parsed OCR result.
        """
        logger.info("Starting OCR process for image: %s", image_path)

        job_id = await self.client.upload_image(image_path)
        logger.info("Upload completed, job_id=%s", job_id)

        data = await self.client.wait_for_completion(job_id)
        logger.info("OCR job completed for job_id=%s", job_id)

        raw_md = self.parser.extract_text_from_response(data)

        if not raw_md:
            logger.warning("No OCR content extracted from image: %s", image_path)
            return OcrResult("", "", "", False)

        workflow, pre_graph, post_graph = self.parser.split_mermaid_blocks(raw_md)
        logger.info(
            "Parsed workflow and graph blocks, workflow length=%d",
            len(workflow)
        )

        has_table_pre = "<table" in pre_graph.lower()
        has_table_post = "<table" in post_graph.lower()
        logger.info("Tables detected: pre=%s, post=%s", has_table_pre, has_table_post)

        if has_table_pre:
            pre_graph = self.parser.convert_html_tables_to_markdown(pre_graph)
        if has_table_post:
            post_graph = self.parser.convert_html_tables_to_markdown(post_graph)

        logger.info("OCR process finished for image: %s", image_path)
        return OcrResult(
            workflow=workflow,
            pre_graph_content=pre_graph,
            post_graph_content=post_graph,
            has_table=has_table_pre or has_table_post,
        )