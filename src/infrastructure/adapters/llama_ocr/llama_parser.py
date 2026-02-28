import re

class LlamaOcrParser:
    """Extraction et parsing du markdown / tables HTML en Markdown."""

    @staticmethod
    def extract_text_from_response(data: dict):
        raw_md = LlamaOcrParser._extract_raw_markdown(data)
        return raw_md

    @staticmethod
    def _extract_raw_markdown(data: dict) -> str:
        for key in ("markdown_full", "markdown"):
            obj = data.get(key)
            if isinstance(obj, dict):
                parts = [(p.get("markdown") or p.get("md") or "").strip() for p in obj.get("pages", [])]
                parts = [p for p in parts if p]
                if parts:
                    return "\n\n".join(parts)
            elif isinstance(obj, str) and obj.strip():
                return obj.strip()

        for key in ("text_full", "text"):
            obj = data.get(key)
            if isinstance(obj, dict):
                parts = [
                    p.get("text", "").strip()
                    for p in obj.get("pages", [])
                    if isinstance(p.get("text"), str) and p.get("text").strip()
                ]
                if parts:
                    return "\n\n".join(parts)
            elif isinstance(obj, str) and obj.strip():
                return obj.strip()

        return ""

    @staticmethod
    def split_mermaid_blocks(raw_md: str):
        pattern = re.compile(r"```(?:mermaid)?\s*\n(.*?)```", re.DOTALL)
        matches = list(pattern.finditer(raw_md))

        if not matches:
            return "", raw_md.strip(), ""

        workflow = "\n\n".join([m.group(1).strip() for m in matches])
        pre_graph = raw_md[: matches[0].start()].strip()
        post_graph = raw_md[matches[-1].end() :].strip()
        return workflow, pre_graph, post_graph

    @staticmethod
    def convert_html_tables_to_markdown(text: str) -> str:
        table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE)

        def convert_single_table(table_html: str) -> str:
            rows = re.findall(r"<tr.*?>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
            md_rows = []
            for row in rows:
                cells = re.findall(r"<t[dh].*?>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                clean_cells = [re.sub(r"<.*?>", "", c).strip() for c in cells]
                if clean_cells:
                    md_rows.append(clean_cells)
            if not md_rows:
                return ""
            header = "| " + " | ".join(md_rows[0]) + " |"
            separator = "| " + " | ".join(["---"] * len(md_rows[0])) + " |"
            body = ["| " + " | ".join(r) + " |" for r in md_rows[1:]]
            return "\n".join([header, separator] + body)

        return table_pattern.sub(lambda m: convert_single_table(m.group(0)), text)