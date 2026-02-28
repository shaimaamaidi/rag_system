from dataclasses import dataclass


@dataclass
class OcrResult:
    workflow: str
    pre_graph_content: str
    post_graph_content: str
    has_table: bool