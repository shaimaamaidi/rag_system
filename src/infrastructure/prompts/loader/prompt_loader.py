from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from jinja2 import Template

from src.domain.ports.output.prompt_provider_port import PromptProviderPort


class PromptyLoader(PromptProviderPort):
    """Implémentation du chargeur de fichiers .prompty."""

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialise le loader.

        Args:
            templates_dir: Chemin vers le répertoire des templates
        """
        if templates_dir is None:
            current_dir = Path(__file__).parent.parent
            self.templates_dir = current_dir / "templates"
        else:
            self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            raise ValueError(f"Templates directory not found: {self.templates_dir}")

    @staticmethod
    def _parse_prompty_file(file_path: Path) -> Dict[str, Any]:
        """
        Parse un fichier .prompty.

        Args:
            file_path: Chemin vers le fichier .prompty

        Returns:
            Dict contenant les métadonnées et le contenu
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Séparer le frontmatter YAML du contenu
        parts = content.split('---')
        if len(parts) < 3:
            raise ValueError(f"Invalid .prompty file format: {file_path}")

        # Parser le YAML (frontmatter)
        metadata = yaml.safe_load(parts[1])

        # Récupérer le contenu du prompt
        prompt_content = '---'.join(parts[2:]).strip()

        return {
            'metadata': metadata,
            'content': prompt_content
        }

    def _load_prompt(self, prompt_name: str, **kwargs: Any) -> str:
        """
        Charge et formate un prompt.

        Args:
            prompt_name: Nom du fichier (sans extension)
            **kwargs: Variables pour le template Jinja2

        Returns:
            str: Le prompt formaté
        """
        file_path = self.templates_dir / f"{prompt_name}.prompty"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        prompty_data = PromptyLoader._parse_prompty_file(file_path)
        prompt_content = prompty_data['content']

        # Valider les inputs si définis dans les métadonnées
        metadata = prompty_data['metadata']
        if 'inputs' in metadata:
            required_inputs = set(metadata['inputs'].keys())
            provided_inputs = set(kwargs.keys())
            missing_inputs = required_inputs - provided_inputs

            if missing_inputs:
                raise ValueError(
                    f"Missing required inputs for {prompt_name}: {missing_inputs}"
                )

        # Formatter avec Jinja2
        template = Template(prompt_content)
        formatted_prompt = template.render(**kwargs)

        return formatted_prompt

    def get_system_prompt(self, prompt_type: str) -> str:
        """
        Récupère un prompt système.

        Args:
            prompt_type: Type de prompt (answer, classifier)

        Returns:
            str: Le prompt système
        """
        prompt_name = f"system_prompt_{prompt_type}"
        return self._load_prompt(prompt_name)

    def get_user_generator_prompt(self, context: str, question: str) -> str:
        """
        Récupère et formate le prompt utilisateur.

        Args:
            context: Contexte pour répondre à la question
            question: Question de l'utilisateur

        Returns:
            str: Le prompt utilisateur formaté
        """
        return self._load_prompt(
            "user_prompt_answer_generator",
            context=context,
            question=question
        )

    def get_user_convertor_prompt(self, mermaid_text: str) -> str:
        """
        Récupère et formate le prompt utilisateur pour la conversion.

        Args:
            mermaid_text: Le texte du diagramme Mermaid à convertir

        Returns:
            str: Le prompt utilisateur formaté
        """
        return self._load_prompt(
            "user_prompt_convertor",
            mermaid_text=mermaid_text
        )

    def get_agent_instructions(self) -> str:
        """
        Récupère les instructions de l'agent Azure AI.

        Returns:
            str: Les instructions de l'agent
        """
        return self._load_prompt("agent_instructions")