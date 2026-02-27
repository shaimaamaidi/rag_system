import requests
import time
import os
import re
import json
from dotenv import load_dotenv



class LlamaOCRProcessor:

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self.base_url = os.getenv("LLAMA_CLOUD_ENDPOINT")

    def upload_image(self, image_path: str) -> str:
        url = f"{self.base_url}/parse/upload"
        configuration = {
            "tier": "agentic_plus",
            "version": "latest",
            "processing_options": {"ocr_parameters": {"languages": ["ar"]}},
            "output_options": {"markdown": {"annotate_links": False}},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(image_path, "rb") as f:
            response = requests.post(
                url, headers=headers, files={"file": f},
                data={"configuration": json.dumps(configuration)}
            )
        response.raise_for_status()
        job_id = response.json()["id"]
        print(f"→ job_id: {job_id}")
        return job_id

    def wait_for_completion(self, job_id: str) -> tuple[str, str, str, bool]:
        url = f"{self.base_url}/parse/{job_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        while True:
            response = requests.get(url, headers=headers, params={"expand": "markdown,text"})
            response.raise_for_status()
            data = response.json()

            status = data["job"]["status"]
            print("Status:", status)

            if status == "COMPLETED":
                return LlamaOCRProcessor._extract_text_from_response(data)
            elif status == "FAILED":
                raise RuntimeError(data["job"].get("error_message", "unknown"))

            time.sleep(3)

    @staticmethod
    def _extract_text_from_response(data: dict) -> tuple[str, str, str, bool]:

        raw_md = ""

        # ── 1. Récupérer tout le Markdown ───────────────────────────────
        for key in ("markdown_full", "markdown"):
            obj = data.get(key)
            if isinstance(obj, dict):
                pages = obj.get("pages", [])
                parts = []
                for p in pages:
                    md = p.get("markdown") or p.get("md") or ""
                    if isinstance(md, str) and md.strip():
                        parts.append(md.strip())
                if parts:
                    raw_md = "\n\n".join(parts)
                    break
            elif isinstance(obj, str) and obj.strip():
                raw_md = obj.strip()
                break

        # ── 2. Fallback sur le texte brut ───────────────────────────────
        if not raw_md:
            for key in ("text_full", "text"):
                obj = data.get(key)
                if isinstance(obj, dict):
                    pages = obj.get("pages", [])
                    parts = [
                        p.get("text", "").strip()
                        for p in pages
                        if isinstance(p.get("text"), str) and p.get("text").strip()
                    ]
                    if parts:
                        raw_md = "\n\n".join(parts)
                        break
                elif isinstance(obj, str) and obj.strip():
                    raw_md = obj.strip()
                    break

        if not raw_md:
            return "", "", "", False

        # ── 3. Extraire blocs mermaid ────────────────────────────────────
        mermaid_pattern = re.compile(r"```(?:mermaid)?\s*\n(.*?)```", re.DOTALL)
        matches = list(mermaid_pattern.finditer(raw_md))
        mermaid_blocks = [m.group(1).strip() for m in matches]

        workflow = "\n\n".join(mermaid_blocks) if mermaid_blocks else ""

        # ── 4. Extraire pre_graph et post_graph ─────────────────────────
        if matches:
            first_match = matches[0]
            last_match = matches[-1]

            pre_graph_content = raw_md[:first_match.start()].strip()
            post_graph_content = raw_md[last_match.end():].strip()
        else:
            pre_graph_content = raw_md.strip()
            post_graph_content = ""

        # ── 5. Vérifier table après graph ───────────────────────────────
        has_table_after_graph = bool(
            re.search(r"<table.*?>", post_graph_content, re.IGNORECASE | re.DOTALL)
        )
        if has_table_after_graph:
            post_graph_content = LlamaOCRProcessor._convert_html_tables_to_markdown(post_graph_content)

        has_table_before_graph = bool(
            re.search(r"<table.*?>", pre_graph_content, re.IGNORECASE | re.DOTALL)
        )
        if has_table_before_graph:
            pre_graph_content = LlamaOCRProcessor._convert_html_tables_to_markdown(pre_graph_content)

        has_table = has_table_before_graph or has_table_after_graph
        return workflow, pre_graph_content, post_graph_content, has_table

    @staticmethod
    def _convert_html_tables_to_markdown(text: str) -> str:
        table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE)

        def convert_single_table(table_html: str) -> str:
            # Extract rows
            rows = re.findall(r"<tr.*?>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
            md_rows = []

            for row in rows:
                cells = re.findall(r"<t[dh].*?>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                clean_cells = [
                    re.sub(r"<.*?>", "", cell).strip()
                    for cell in cells
                ]
                if clean_cells:
                    md_rows.append(clean_cells)

            if not md_rows:
                return ""

            header = "| " + " | ".join(md_rows[0]) + " |"
            separator = "| " + " | ".join(["---"] * len(md_rows[0])) + " |"

            body = [
                "| " + " | ".join(row) + " |"
                for row in md_rows[1:]
            ]

            return "\n".join([header, separator] + body)

        return table_pattern.sub(lambda m: convert_single_table(m.group(0)), text)