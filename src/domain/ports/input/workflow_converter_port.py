from abc import ABC, abstractmethod
from src.domain.models.workflow_model import WorkflowResult

class WorkflowConverterPort(ABC):
    """Port abstrait pour convertir un flowchart en workflow JSON."""

    @abstractmethod
    def convert(self, mermaid_text: str) -> WorkflowResult:
        pass