import json
import os
import asyncio
import httpx
from dotenv import load_dotenv

from src.domain.exceptions.llama_config_exception import LlamaConfigException
from src.domain.exceptions.llama_job_failed_exception import LlamaJobFailedException
from src.domain.exceptions.llama_polling_exception import LlamaPollingException
from src.domain.exceptions.llama_upload_exception import LlamaUploadException


class LlamaApiClient:
    """Gestion asynchrone de la communication HTTP avec Llama Cloud."""

    def __init__(self):
        load_dotenv()
        self._api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self._base_url = os.getenv("LLAMA_CLOUD_ENDPOINT")

        if not all([self._api_key, self._base_url]):
            raise LlamaConfigException(
                message="Missing Llama Cloud credentials: LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_ENDPOINT",
                code="LLAMA_CONFIG_ERROR",
                http_status=500
            )

        self._headers = {
            "Authorization": f"Bearer {self._api_key}"
        }

    # ================================
    # Upload Image (ASYNC)
    # ================================
    async def upload_image(self, image_path: str) -> str:

        if not os.path.exists(image_path):
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
                return response.json()["id"]

        except Exception as e:
            raise LlamaUploadException(
                message=f"Failed to upload image to Llama Cloud: {str(e)}",
                code="LLAMA_UPLOAD_ERROR",
                http_status=502
            ) from e

    # ================================
    # Wait For Completion (ASYNC)
    # ================================
    async def wait_for_completion(self, job_id: str) -> dict:

        url = f"{self._base_url}/parse/{job_id}"

        async with httpx.AsyncClient(timeout=60.0) as client:

            while True:
                try:
                    response = await client.get(
                        url,
                        headers=self._headers,
                        params={"expand": "markdown,text"},
                    )
                    response.raise_for_status()

                except Exception as e:
                    raise LlamaPollingException(
                        message=f"Failed to poll Llama job {job_id}: {str(e)}",
                        code="LLAMA_POLLING_ERROR",
                        http_status=502
                    ) from e

                data = response.json()
                status = data["job"]["status"]

                if status == "COMPLETED":
                    return data

                elif status == "FAILED":
                    raise LlamaJobFailedException(
                        message=f"Llama job {job_id} failed: {data['job'].get('error_message', 'unknown')}",
                        code="LLAMA_JOB_FAILED_ERROR",
                        http_status=502
                    )

                await asyncio.sleep(3)