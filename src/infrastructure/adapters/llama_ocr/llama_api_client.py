"""Async client for Llama Cloud OCR operations."""

import json
import os
import asyncio
import httpx
import logging
from dotenv import load_dotenv

from src.domain.exceptions.llama_config_exception import LlamaConfigException
from src.domain.exceptions.llama_job_failed_exception import LlamaJobFailedException
from src.domain.exceptions.llama_polling_exception import LlamaPollingException
from src.domain.exceptions.llama_upload_exception import LlamaUploadException
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class LlamaApiClient:
    """Wrapper for Llama Cloud OCR API calls."""

    def __init__(self):
        """Initialize the client using environment configuration.

        :raises LlamaConfigException: If required credentials are missing.
        """
        load_dotenv()
        self._api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self._base_url = os.getenv("LLAMA_CLOUD_ENDPOINT")

        if not all([self._api_key, self._base_url]):
            logger.error("Missing Llama Cloud credentials")
            raise LlamaConfigException(
                message="Missing Llama Cloud credentials: LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_ENDPOINT",
                code="LLAMA_CONFIG_ERROR",
                http_status=500
            )

        self._headers = {"Authorization": f"Bearer {self._api_key}"}
        logger.info("LlamaApiClient initialized with endpoint: %s", self._base_url)

    async def upload_image(self, image_path: str) -> str:
        """Upload an image and start an OCR job.

        :param image_path: Path to the image file.
        :return: Job identifier from Llama Cloud.
        :raises LlamaUploadException: If the image is missing or upload fails.
        """
        logger.info("Uploading image: %s", image_path)

        if not os.path.exists(image_path):
            logger.error("Image file not found: %s", image_path)
            raise LlamaUploadException(
                message=f"Image file not found: {image_path}",
                code="LLAMA_UPLOAD_ERROR",
                http_status=404
            )

        url = f"{self._base_url}/parse/upload"

        configuration = {
            "tier": "agentic_plus",
            "version": "latest",
            "processing_options": {
                "ocr_parameters": {"languages": ["ar"]}
            },
            "output_options": {
                "markdown": {"annotate_links": False}
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(image_path, "rb") as f:
                    files = {"file": f}

                    response = await client.post(
                        url,
                        headers=self._headers,
                        files=files,
                        data={"configuration": json.dumps(configuration)},
                    )

                response.raise_for_status()
                job_id = response.json()["id"]
                logger.info("Image uploaded successfully, job_id=%s", job_id)
                return job_id

        except Exception as e:
            logger.error("Failed to upload image %s: %s", image_path, e)
            raise LlamaUploadException(
                message=f"Failed to upload image to Llama Cloud: {str(e)}",
                code="LLAMA_UPLOAD_ERROR",
                http_status=502
            ) from e
    async def wait_for_completion(
        self, job_id: str, max_retries: int = 20, sleep_seconds: int = 3
    ) -> dict:
        """Poll a job until it completes, fails, or times out.

        :param job_id: OCR job identifier.
        :param max_retries: Maximum poll attempts.
        :param sleep_seconds: Delay between poll attempts.
        :return: OCR result payload from Llama Cloud.
        :raises LlamaPollingException: If polling fails or times out.
        :raises LlamaJobFailedException: If the job reports failure.
        """
        logger.info("Polling Llama job: %s", job_id)

        url = f"{self._base_url}/parse/{job_id}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            for _ in range(max_retries):
                try:
                    response = await client.get(
                        url,
                        headers=self._headers,
                        params={"expand": "markdown,text"},
                    )
                    response.raise_for_status()

                except Exception as e:
                    logger.error("Polling failed for job %s: %s", job_id, e)
                    raise LlamaPollingException(
                        message=f"Failed to poll Llama job {job_id}: {str(e)}",
                        code="LLAMA_POLLING_ERROR",
                        http_status=502
                    ) from e

                data = response.json()
                status = data["job"]["status"]

                if status == "COMPLETED":
                    logger.info("Llama job completed successfully: %s", job_id)
                    return data

                elif status == "FAILED":
                    error_msg = data.get("job", {}).get("error_message", "unknown")
                    logger.error("Llama job failed: %s, error: %s", job_id, error_msg)
                    raise LlamaJobFailedException(
                        message=f"Llama job {job_id} failed: {error_msg}",
                        code="LLAMA_JOB_FAILED_ERROR",
                        http_status=502
                    )

                await asyncio.sleep(sleep_seconds)

        logger.error("Llama job polling timed out: %s", job_id)
        raise LlamaPollingException(
            message=f"Llama job {job_id} polling timed out after {max_retries * sleep_seconds} seconds",
            code="LLAMA_POLLING_TIMEOUT",
            http_status=504
        )