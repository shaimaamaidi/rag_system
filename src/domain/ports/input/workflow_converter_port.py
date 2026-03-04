"""Input port interface for workflow conversion."""

from abc import ABC, abstractmethod
from src.domain.models.workflow_model import WorkflowResult

class WorkflowConverterPort(ABC):
    """Interface for converting flowcharts into workflow JSON."""

    @abstractmethod
    def convert(self, mermaid_text: str) -> WorkflowResult:
        """Convert Mermaid flowchart text into a workflow result.

        :param mermaid_text: Mermaid flowchart content.
        :return: Workflow conversion result.
        """
        pass