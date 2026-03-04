"""Output port interface for prompt loading and formatting."""

from abc import ABC, abstractmethod


class PromptProviderPort(ABC):
    """Interface for loading and formatting prompts."""

    @abstractmethod
    def get_system_prompt(self, prompt_type: str) -> str:
        """Return a system prompt by type.

        :param prompt_type: Prompt type key (answer, classifier, etc.).
        :return: System prompt text.
        """
        pass

    @abstractmethod
    def get_user_generator_prompt(self, context: str, question: str) -> str:
        """Return a user prompt for answer generation.

        :param context: Context used to answer the question.
        :param question: User question.
        :return: Formatted user prompt.
        """
        pass

    @abstractmethod
    def get_user_convertor_prompt(self, mermaid_text: str) -> str:
        """Return a user prompt for workflow conversion.

        :param mermaid_text: Mermaid flowchart text.
        :return: Formatted user prompt.
        """
        pass

    @abstractmethod
    def get_agent_instructions(self) -> str:
        """Return system instructions for the agent.

        :return: Instruction text for agent behavior.
        """
        pass