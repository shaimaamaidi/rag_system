"""Workflow conversion result model."""

from dataclasses import dataclass


@dataclass
class WorkflowResult:
    """Container for workflow conversion output.

    :ivar raw_json: Raw JSON string produced by the converter.
    """
    raw_json: str