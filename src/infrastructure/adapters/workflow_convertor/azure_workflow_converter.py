"""Azure OpenAI adapter for converting Mermaid workflows to JSON."""

import logging
import os

from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from src.domain.exceptions.workflow_conversion_exception import WorkflowConversionException
from src.domain.exceptions.workflow_converter_config_exception import WorkflowConverterConfigException
from src.domain.models.workflow_model import WorkflowResult
from src.domain.ports.input.workflow_converter_port import WorkflowConverterPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class AzureWorkflowConverter(WorkflowConverterPort):
    """Convert Mermaid workflows using Azure OpenAI.

    :param prompt_provider: Provider for system and user prompts.
    """

    def __init__(self, prompt_provider: PromptProviderPort):
        """Initialize the converter.

        :param prompt_provider: Provider for system and user prompts.
        :raises WorkflowConverterConfigException: If required env vars are missing.
        """
        load_dotenv()
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self._deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([api_key, endpoint, api_version, self._deployment]):
            raise WorkflowConverterConfigException(
                message="Missing Azure OpenAI environment variables for WorkflowConverter: "
                        "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
                        "AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME",
            )

        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self.prompt_provider = prompt_provider
        logger.info("AzureWorkflowConverter initialized with deployment: %s", self._deployment)

    def convert(self, mermaid_text: str) -> WorkflowResult:
        """Convert Mermaid text into a workflow JSON payload.

        :param mermaid_text: Mermaid flowchart content.
        :return: Workflow conversion result.
        :raises WorkflowConversionException: If conversion fails or input is empty.
        """
        if not mermaid_text or not mermaid_text.strip():
            raise WorkflowConversionException(
                message="Mermaid text cannot be empty",
            )

        logger.info("Starting workflow conversion for Mermaid text (length=%d)", len(mermaid_text))

        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    ChatCompletionSystemMessageParam(
                        role="system",
                        content=self.prompt_provider.get_system_prompt(prompt_type="convertor")
                    ),
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=self.prompt_provider.get_user_convertor_prompt(mermaid_text)
                    )
                ],
            )
            raw_json = response.choices[0].message.content
            logger.info("Workflow conversion succeeded (output length=%d)", len(str(raw_json)))
            return WorkflowResult(raw_json=raw_json)
        except Exception as e:
            logger.error("Azure OpenAI workflow conversion failed: %s", e)
            raise WorkflowConversionException(
                message=f"Azure OpenAI workflow conversion failed: {str(e)}",
            ) from e