from abc import ABC, abstractmethod


class PromptProviderPort(ABC):
    """Port pour le chargement des prompts."""

    @abstractmethod
    def get_system_prompt(self, prompt_type: str) -> str:
        """
        Récupère un prompt système.

        Args:
            prompt_type: Type de prompt système (answer, classifier, etc.)

        Returns:
            str: Le prompt système
        """
        pass

    @abstractmethod
    def get_user_generator_prompt(self, context: str, question: str) -> str:
        """
        Récupère et formate le prompt utilisateur.

        Args:
            context: Contexte pour répondre à la question
            question: Question de l'utilisateur

        Returns:
            str: Le prompt utilisateur formaté
        """
        pass

    @abstractmethod
    def get_user_convertor_prompt(self, mermaid_text: str) -> str:
        """
        Récupère et formate le prompt utilisateur.

        Returns:
            str: Le prompt utilisateur formaté
        """
        pass
