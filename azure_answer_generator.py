"""
Module containing the AzureOpenAIAnswerGenerator class.
Provides an adapter to generate answers and validate domains using Azure OpenAI's chat completions.
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from azure_search_adapter import AzureAISearchAdapter


class AzureOpenAIAnswerGenerator:
    """
    Adapter for generating answers and validating domains using Azure OpenAI.

    This adapter implements the AnswerGeneratorPort and provides:
    - generate_answer: Generates answers for user questions based on context.
    - ask_is_allowed: Determines if a question is within allowed domains.
    """

    def __init__(self, azure_adapter: AzureAISearchAdapter):
        load_dotenv()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not all([self.endpoint, self.api_key, self.api_version, self.embedding_model, self.model]):
            raise ValueError(
                "One or more Azure OpenAI environment variables are missing: "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_EMBEDDING_MODEL, AZURE_OPENAI_DEPLOYMENT_NAME"
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
        self.azure_adapter = azure_adapter

    def generate_answer(self, context, question) -> str:
        system_prompt = (
            "You are a helpful assistant that answers questions strictly based on "
            "the provided context. You always cite your sources accurately."
        )

        user_prompt = f"""
        You are a specialist assistant. Answer questions strictly using the documents provided below.

        **INSTRUCTIONS**

        1. **Answer rules:**
           - Answer the question **based ONLY on the provided context**.
           - If the answer is **not found in the context**, reply exactly:
             "I don't know, please try a different question."
           - Do not guess, infer, or introduce any information.

        2. **Citation rules:**
           - For every piece of information you use, provide a citation immediately after the answer.
           - **Citation formatting:**
             ```
             - Document name: [doc_name]
             - Title: [according to rules below]
             - Original text: [full original_text]
             ```
           - **Title rules:**
             a) If the excerpt contains "مادة": use it alone. Example: `Title: المادة الثالثة`
             b) If both title and sub_title exist: `title — sub_title`
             c) If only title exists: use title
             d) If only sub_title exists: use sub_title
             e) If neither title nor sub_title exists: choose a short descriptive title from the original_text itself

        3. **Important:**
           - First give the answer, then the citation(s). 
           - If multiple citations are used, list them **separately** under the answer.

        **CONTEXT**
        {context}

        **QUESTION**
        {question}

        **OUTPUT FORMAT**
        Answer: [direct answer to the question]

        Citations:
        - Document name: ...
        - Title: ...
        - Original text: ...
        """

        try:
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=user_prompt)
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError("Failed to generate answer with Azure OpenAI") from e