from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from jinja2 import Template, Environment

from src.domain.ports.output.prompt_provider_port import PromptProviderPort


class PromptyLoader(PromptProviderPort):
    """Implémentation du chargeur de fichiers .prompty."""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            current_dir = Path(__file__).parent.parent
            self.templates_dir = current_dir / "templates"
        else:
            self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            raise ValueError(f"Templates directory not found: {self.templates_dir}")

    @staticmethod
    def _parse_prompty_file(file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        parts = content.split('---')
        if len(parts) < 3:
            raise ValueError(f"Invalid .prompty file format: {file_path}")

        metadata = yaml.safe_load(parts[1])
        prompt_content = '---'.join(parts[2:]).strip()

        return {
            'metadata': metadata,
            'content': prompt_content
        }

    def _load_prompt(self, prompt_name: str, **kwargs: Any) -> str:
        file_path = self.templates_dir / f"{prompt_name}.prompty"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        prompty_data = PromptyLoader._parse_prompty_file(file_path)
        prompt_content = prompty_data['content']

        metadata = prompty_data['metadata']
        if 'inputs' in metadata:
            required_inputs = set(metadata['inputs'].keys())
            provided_inputs = set(kwargs.keys())
            missing_inputs = required_inputs - provided_inputs
            if missing_inputs:
                raise ValueError(
                    f"Missing required inputs for {prompt_name}: {missing_inputs}"
                )

        # ── FIX : utiliser un Environment Jinja2 avec des délimiteurs custom ──
        # Le problème : les accolades {} dans le contenu mermaid (ex: Decision{...})
        # sont interprétées par Jinja2 comme des blocs de template et effacées
        # avant d'arriver au LLM → le converter reçoit un texte vide → retourne
        # lanes:[], nodes:[], edges:[].
        #
        # Solution : changer les délimiteurs Jinja2 pour utiliser [[ ]] au lieu
        # de {{ }} — les accolades mermaid passent désormais sans modification.
        # Les templates .prompty doivent utiliser {{ var }} (converti ci-dessous)
        # ou directement [[ var ]] dans les nouveaux fichiers.
        # ──────────────────────────────────────────────────────────────────────
        env = Environment(
            variable_start_string="[[",
            variable_end_string="]]",
            block_start_string="[%",
            block_end_string="%]",
            comment_start_string="[#",
            comment_end_string="#]",
        )

        # Convertir l'ancienne syntaxe {{ var }} → [[ var ]] pour compatibilité
        # avec les templates existants qui utilisent encore {{ }}
        import re
        prompt_content = re.sub(
            r"\{\{\s*(\w+)\s*\}\}",
            r"[[ \1 ]]",
            prompt_content,
        )

        template = env.from_string(prompt_content)
        return template.render(**kwargs)

    def get_system_prompt(self, prompt_type: str) -> str:
        prompt_name = f"system_prompt_{prompt_type}"
        return self._load_prompt(prompt_name)

    def get_user_generator_prompt(self, context: str, question: str) -> str:
        return self._load_prompt(
            "user_prompt_answer_generator",
            context=context,
            question=question,
        )

    def get_user_convertor_prompt(self, mermaid_text: str) -> str:
        return self._load_prompt(
            "user_prompt_convertor",
            mermaid_text=mermaid_text,
        )

    def get_agent_instructions(self) -> str:
        return self._load_prompt("agent_instructions")