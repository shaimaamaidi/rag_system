"""Output port interface for prompt loading and formatting."""

from abc import ABC, abstractmethod


class PromptProviderPort(ABC):
    """Interface for loading and formatting prompts."""

    @abstractmethod
    def get_system_convertor_prompt(self) -> str:
        """Return a system prompt by type.

        :return: System prompt text.
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