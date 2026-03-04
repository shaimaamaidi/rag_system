import logging
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from src.domain.exceptions.azure_answer_exception import AzureOpenAIAnswerException
from src.domain.exceptions.azure_config_exception import AzureOpenAIConfigException
from src.domain.ports.output.answer_generator_port import AnswerGeneratorPort
from src.domain.ports.output.prompt_provider_port import PromptProviderPort
from src.infrastructure.logging.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


class AzureOpenAIAnswerGenerator(AnswerGeneratorPort):

    def __init__(self, prompt_provider: PromptProviderPort):
        load_dotenv()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([self.endpoint, self.api_key, self.api_version, self.embedding_model, self.model]):
            logger.error("Missing Azure OpenAI environment variables")
            raise AzureOpenAIConfigException(
                "One or more Azure OpenAI environment variables are missing"
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        self.prompt_provider = prompt_provider
        logger.info("AzureOpenAIAnswerGenerator initialized successfully")

    def generate_answer(self, context, question) -> str:
        logger.info("Generating answer for a new question")
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

            answer = response.choices[0].message.content
            logger.info("Answer generated successfully")
            return answer

        except Exception as e:
            logger.exception("Failed to generate answer with Azure OpenAI")
            raise AzureOpenAIAnswerException(
                f"Failed to generate answer with Azure OpenAI: {str(e)}"
            )