from src.domain.models.ocr_result_model import OcrResult
from src.domain.ports.output.LlamaOcrPort import LlamaOcrPort
from .llama_api_client import LlamaApiClient
from .llama_parser import LlamaOcrParser

class LlamaOcrAdapter(LlamaOcrPort):
    """Adaptateur OCR orchestration."""

    def __init__(self):
        self.client = LlamaApiClient()
        self.parser = LlamaOcrParser()

    def process(self, image_path: str) -> OcrResult:
        job_id = self.client.upload_image(image_path)
        data = self.client.wait_for_completion(job_id)
        raw_md = self.parser.extract_text_from_response(data)

        if not raw_md:
            return OcrResult("", "", "", False)

        workflow, pre_graph, post_graph = self.parser.split_mermaid_blocks(raw_md)

        has_table_pre = "<table" in pre_graph.lower()
        has_table_post = "<table" in post_graph.lower()

        if has_table_pre:
            pre_graph = self.parser.convert_html_tables_to_markdown(pre_graph)
        if has_table_post:
            post_graph = self.parser.convert_html_tables_to_markdown(post_graph)

        return OcrResult(
            workflow=workflow,
            pre_graph_content=pre_graph,
            post_graph_content=post_graph,
            has_table=has_table_pre or has_table_post,
        )