"""OCR result model for parsed workflow content."""

from dataclasses import dataclass


@dataclass
class OcrResult:
    """Result of OCR processing for a page or image.

    :ivar workflow: Workflow block content.
    :ivar pre_graph_content: Text before the workflow graph.
    :ivar post_graph_content: Text after the workflow graph.
    :ivar has_table: Whether tables were detected in OCR output.
    """
    workflow: str
    pre_graph_content: str
    post_graph_content: str
    has_table: bool