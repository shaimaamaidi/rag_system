"""
Module containing the AzureOpenAIAnswerGenerator class.
Provides an adapter to generate answers and validate domains using Azure OpenAI's chat completions.
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from src.domain.exceptions.azure_answer_exception import AzureOpenAIAnswerException
from src.domain.exceptions.azure_config_exception import AzureOpenAIConfigException
from src.domain.ports.output.answer_generator_port import AnswerGeneratorPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.adapters.search_adapter.azure_search_adapter import AzureAISearchAdapter


class AzureOpenAIAnswerGenerator(AnswerGeneratorPort):
    """
    Adapter for generating answers and validating domains using Azure OpenAI.

    This adapter implements the AnswerGeneratorPort and provides:
    - generate_answer: Generates answers for user questions based on context.
    - ask_is_allowed: Determines if a question is within allowed domains.
    """

    def __init__(self, azure_adapter: AzureAISearchAdapter, prompt_provider: PromptProviderPort):
        load_dotenv()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not all([self.endpoint, self.api_key, self.api_version, self.embedding_model, self.model]):
            raise AzureOpenAIConfigException(
                "One or more Azure OpenAI environment variables are missing: "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_EMBEDDING_MODEL, AZURE_OPENAI_DEPLOYMENT_NAME"
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        self.azure_adapter = azure_adapter
        self.prompt_provider = prompt_provider

    def generate_answer(self, context, question) -> str:
        try:
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=self.prompt_provider.get_system_prompt(prompt_type="answer_generator")
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=self.prompt_provider.get_user_generator_prompt(context, question)
                )
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
            )

            return response.choices[0].message.content

        except Exception:
            raise AzureOpenAIAnswerException("Failed to generate answer with Azure OpenAI")